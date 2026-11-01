"""Sliceability v5 run infrastructure: decisions log, checkpoint, progress file, and an LLM
client that survives an unattended overnight run.

What this adds to llm_client.LLM (which is left unchanged, so runs 1-4 are unaffected):

  * Gateway outage budget. Connection errors, timeouts, 5xx and 429 are retried with
    backoff for as long as the step's outage budget lasts (llm.outage_budget_s, 2 h). An
    outage window is a period in which calls fail and none succeeds; only windows longer
    than llm.outage_min_window_s count, so routine 429s between successes never add up.
    Once the budget is spent, GatewayGiveUp is raised and the run exits non-zero.
  * 401 / 403 / 404 are fatal immediately (FatalAPIError): a wrong key or model name would
    otherwise turn every annotation into a parse error.
  * Cache files are written atomically (tmp + rename), so a kill mid-write cannot leave a
    truncated cache entry; an unreadable cache entry is treated as a miss and logged.
  * Progress counters (calls done / total, cache hits) for progress.json.
  * run_jobs(): parallel map with a per-step partial file. Every finished job is appended
    to <step>_partial.jsonl (fsync every run.checkpoint_every_calls jobs); a restart loads
    it and runs only the missing jobs. Fatal errors stop the pool and are re-raised.

Cache key: unchanged from llm_client.LLM._key (model, endpoint, prompt version, sha256 of
the rendered prompt, sampling parameters, seed, retry salt).
"""

from __future__ import annotations

import json
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from openai import (APIConnectionError, APITimeoutError, AuthenticationError,
                    InternalServerError, NotFoundError, PermissionDeniedError, RateLimitError)

from common import Run, log
from llm_client import LLM, LLMError


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class GatewayGiveUp(RuntimeError):
    pass


class FatalAPIError(RuntimeError):
    pass


FATAL = (GatewayGiveUp, FatalAPIError)


# ---------------------------------------------------------------------------
# decisions.log
# ---------------------------------------------------------------------------

_DEC_LOCK = threading.Lock()


def decide(run: Run, step: str, decision: str, reason: str) -> None:
    """One line per decision the run makes on its own, with its reason."""
    line = f"{utcnow()}\tstep {step}\t{decision}\treason: {reason}"
    with _DEC_LOCK, open(run.path("decisions.log"), "a") as f:
        f.write(line + "\n")
    log(f"DECISION [{step}] {decision} -- {reason}")


# ---------------------------------------------------------------------------
# checkpoint.json
# ---------------------------------------------------------------------------

class Checkpoint:
    def __init__(self, run: Run):
        self.path = run.path("checkpoint.json")
        self.state = json.loads(self.path.read_text()) if self.path.exists() else \
            {"done_steps": [], "step_seconds": {}, "history": []}

    def is_done(self, step: str) -> bool:
        return step in self.state["done_steps"]

    def mark_done(self, step: str, seconds: float) -> None:
        if step not in self.state["done_steps"]:
            self.state["done_steps"].append(step)
        self.state["step_seconds"][step] = round(seconds, 1)
        self.state["history"].append({"step": step, "done_at": utcnow(), "seconds": round(seconds, 1)})
        self._save()

    def unmark(self, step: str) -> None:
        if step in self.state["done_steps"]:
            self.state["done_steps"].remove(step)
            self._save()

    def note(self, **kw) -> None:
        self.state.setdefault("notes", []).append({"at": utcnow(), **kw})
        self._save()

    def _save(self) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.state, indent=2) + "\n")
        os.replace(tmp, self.path)


# ---------------------------------------------------------------------------
# progress.json
# ---------------------------------------------------------------------------

class Progress:
    """Process-wide progress state, written to progress.json every run.progress_every_s."""

    def __init__(self):
        self.lock = threading.Lock()
        self.path: Path | None = None
        self.t_run = time.time()
        self.step = None
        self.t_step = time.time()
        self.total = 0
        self.done = 0
        self.cache_hits = 0
        self.api_calls = 0
        self.failed = 0
        self.steps_plan: list[str] = []
        self.steps_done: list[str] = []
        self.status = "starting"
        self._thread = None
        self._stop = threading.Event()

    def start(self, path: Path, every_s: int, plan: list[str]) -> None:
        self.path, self.steps_plan = path, plan
        self._thread = threading.Thread(target=self._loop, args=(every_s,), daemon=True)
        self._thread.start()

    def _loop(self, every_s: int) -> None:
        while not self._stop.wait(every_s):
            self.write()

    def stop(self, status: str) -> None:
        self.status = status
        self._stop.set()
        self.write()

    def start_step(self, step: str) -> None:
        with self.lock:
            self.step, self.t_step = step, time.time()
            self.total = self.done = self.cache_hits = self.api_calls = self.failed = 0
            self.status = "running"
        self.write()

    def end_step(self, step: str) -> None:
        with self.lock:
            self.steps_done.append(step)
        self.write()

    def add_total(self, n: int) -> None:
        with self.lock:
            self.total += n

    def job_done(self, ok: bool = True) -> None:
        with self.lock:
            self.done += 1
            self.failed += 0 if ok else 1

    def call(self, cached: bool) -> None:
        with self.lock:
            if cached:
                self.cache_hits += 1
            else:
                self.api_calls += 1

    def write(self) -> None:
        if self.path is None:
            return
        with self.lock:
            now = time.time()
            el = now - self.t_step
            rate = self.done / el if el > 0 else 0.0
            eta = (self.total - self.done) / rate if rate > 0 and self.total else None
            st = {"updated_utc": utcnow(), "status": self.status, "current_step": self.step,
                  "calls_done": self.done, "calls_total": self.total,
                  "cache_hits": self.cache_hits, "api_calls": self.api_calls,
                  "failed_jobs": self.failed,
                  "step_elapsed_s": round(el), "step_eta_s": None if eta is None else round(eta),
                  "step_eta_utc": None if eta is None else
                  datetime.fromtimestamp(now + eta, timezone.utc).isoformat(timespec="seconds"),
                  "run_elapsed_s": round(now - self.t_run),
                  "steps_done": self.steps_done, "steps_plan": self.steps_plan,
                  "outage_s_this_step": round(OUTAGE.spent()), "pid": os.getpid()}
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(st, indent=2) + "\n")
        os.replace(tmp, self.path)


PROGRESS = Progress()


# ---------------------------------------------------------------------------
# outage budget
# ---------------------------------------------------------------------------

class Outage:
    def __init__(self):
        self.lock = threading.Lock()
        self.total = 0.0
        self.window_start: float | None = None
        self.budget = 7200.0
        self.min_window = 60.0

    def configure(self, budget: float, min_window: float) -> None:
        self.budget, self.min_window = budget, min_window

    def reset(self) -> None:
        with self.lock:
            self.total, self.window_start = 0.0, None

    def failure(self) -> float:
        with self.lock:
            now = time.time()
            if self.window_start is None:
                self.window_start = now
            return self.total + (now - self.window_start)

    def success(self) -> None:
        with self.lock:
            if self.window_start is not None:
                w = time.time() - self.window_start
                if w >= self.min_window:
                    self.total += w
                self.window_start = None

    def spent(self) -> float:
        with self.lock:
            cur = (time.time() - self.window_start) if self.window_start else 0.0
            return self.total + cur


OUTAGE = Outage()


class V5LLM(LLM):
    """llm_client.LLM with the outage budget, fatal-error rules, atomic cache writes and
    progress counting. Same cache key, same call log format."""

    def __init__(self, run: Run, role: str, *, model_override: str | None = None):
        super().__init__(run, role, model_override=model_override)
        lc = run.cfg["llm"]
        self.backoff_max = lc.get("backoff_max_s", 120)

    def _api(self, prompt: str, seed: int | None):
        kw: dict[str, Any] = {self.token_param: self.max_tokens}
        if self.temperature is not None:
            kw["temperature"] = self.temperature
        if seed is not None:
            kw["seed"] = seed
        if self.extra_body:
            kw["extra_body"] = self.extra_body
        client = self._slots.get()
        try:
            n_err = 0
            while True:
                try:
                    r = client.chat.completions.create(
                        model=self.model, messages=[{"role": "user", "content": prompt}], **kw)
                    OUTAGE.success()
                    break
                except (AuthenticationError, PermissionDeniedError, NotFoundError) as e:
                    raise FatalAPIError(f"{type(e).__name__} from {self.endpoint}/{self.model}: "
                                        f"{str(e)[:300]}") from None
                except (RateLimitError, APIConnectionError, APITimeoutError,
                        InternalServerError) as e:
                    n_err += 1
                    spent = OUTAGE.failure()
                    is429 = isinstance(e, RateLimitError)
                    if not is429 or n_err % 50 == 0:
                        self.calllog.write({"ts": time.time(), "role": self.role,
                                            "model": self.model, "event": "gateway_retry",
                                            "n_err": n_err, "outage_spent_s": round(spent),
                                            "error": f"{type(e).__name__}: {str(e)[:200]}"})
                    if spent > OUTAGE.budget:
                        raise GatewayGiveUp(
                            f"gateway errors on {self.endpoint}/{self.model} for "
                            f"{spent / 60:.0f} min of outage in this step (budget "
                            f"{OUTAGE.budget / 60:.0f} min); last error "
                            f"{type(e).__name__}: {str(e)[:200]}") from None
                    if is429:
                        time.sleep(min(2.0, self.rl_backoff * (2 ** min(n_err, 3)))
                                   * (0.5 + random.random()))
                    else:
                        time.sleep(min(self.backoff_max, 5.0 * 2 ** min(n_err, 5))
                                   * (0.5 + random.random()))
        finally:
            self._slots.put(client)
        ch = r.choices[0]
        tin = r.usage.prompt_tokens if r.usage else 0
        tout = r.usage.completion_tokens if r.usage else 0
        return ch.message.content, tin, tout, str(ch.finish_reason)

    def complete(self, prompt: str, *, step: str, prompt_version: str, item: str,
                 seed: int | None = None, salt: str = "") -> str:
        key = self._key(prompt, prompt_version, seed, salt)
        path = self._cache_path(key)
        base = {"ts": time.time(), "step": step, "role": self.role, "model": self.model,
                "prompt_version": prompt_version, "item": item, "seed": seed, "salt": salt,
                "cache_key": key}
        if path.exists():
            try:
                rec = json.loads(path.read_text())
                PROGRESS.call(cached=True)
                self.calllog.write({**base, "cached": True, "tokens_in": rec["tokens_in"],
                                    "tokens_out": rec["tokens_out"], "cost_usd": 0.0,
                                    "latency_s": 0.0, "ok": True})
                return rec["text"]
            except (json.JSONDecodeError, KeyError) as e:
                self.calllog.write({**base, "event": "corrupt_cache_entry_ignored",
                                    "error": str(e)[:200]})
        t0 = time.time()
        try:
            text, tin, tout, fin = self._api(prompt, seed)
        except FATAL:
            raise
        except Exception as e:
            self.calllog.write({**base, "cached": False, "tokens_in": 0, "tokens_out": 0,
                                "cost_usd": 0.0, "latency_s": time.time() - t0, "ok": False,
                                "error": f"api: {type(e).__name__}: {str(e)[:300]}"})
            raise LLMError(f"API failure for {item}: {type(e).__name__}: {e}") from None
        PROGRESS.call(cached=False)
        lat = time.time() - t0
        cost = tin * self.price_in + tout * self.price_out
        if text is None or not str(text).strip():
            self.calllog.write({**base, "cached": False, "tokens_in": tin, "tokens_out": tout,
                                "cost_usd": cost, "latency_s": lat, "ok": False,
                                "error": f"null_content finish_reason={fin}"})
            raise LLMError(f"null content for {item} (finish_reason={fin}, out={tout})")
        tmp = path.with_suffix(f".tmp{os.getpid()}.{threading.get_ident()}")
        tmp.write_text(json.dumps({"text": text, "tokens_in": tin, "tokens_out": tout,
                                   "finish_reason": fin, "model": self.model,
                                   "prompt_version": prompt_version, "seed": seed},
                                  ensure_ascii=False))
        os.replace(tmp, path)
        self.calllog.write({**base, "cached": False, "tokens_in": tin, "tokens_out": tout,
                            "cost_usd": cost, "latency_s": lat, "ok": True,
                            "finish_reason": fin})
        return text


# ---------------------------------------------------------------------------
# parallel jobs with a partial-results checkpoint
# ---------------------------------------------------------------------------

def run_jobs(run: Run, step: str, jobs: Sequence[Any], key_fn: Callable[[Any], str],
             fn: Callable[[Any], dict], n_workers: int, label: str,
             every_log: int = 500, add_total: bool = True) -> list[dict]:
    """fn(job) -> JSON-serialisable dict. Results in job order.

    Finished jobs are appended to <step>_partial.jsonl as {"key": ..., "result": ...}; on a
    restart, jobs whose key is already there are not run again. An ordinary exception from
    fn is a bug in the caller (fn must record model faults itself) and is re-raised after
    the pool stops, as are GatewayGiveUp / FatalAPIError.
    """
    every_ckpt = run.cfg["run"]["checkpoint_every_calls"]
    ppath = run.path(f"{step}_partial.jsonl")
    done: dict[str, dict] = {}
    if ppath.exists():
        for line in ppath.read_text().splitlines():
            try:
                rec = json.loads(line)
                done[rec["key"]] = rec["result"]
            except (json.JSONDecodeError, KeyError):
                continue                      # a line cut by a kill: that job is rerun
    keys = [key_fn(j) for j in jobs]
    todo = [i for i, k in enumerate(keys) if k not in done]
    if add_total:
        PROGRESS.add_total(len(jobs))
    for _ in range(len(jobs) - len(todo)):
        PROGRESS.job_done()
    if done:
        log(f"  {label}: {len(jobs) - len(todo)}/{len(jobs)} jobs restored from {ppath.name}")
    lock = threading.Lock()
    stop = threading.Event()
    errors: list[BaseException] = []
    fh = open(ppath, "a")
    n_new = [0]
    t0 = time.time()

    def work(i):
        if stop.is_set():
            return
        try:
            res = fn(jobs[i])
        except BaseException as e:            # noqa: BLE001 - re-raised below
            with lock:
                errors.append(e)
            stop.set()
            return
        with lock:
            done[keys[i]] = res
            fh.write(json.dumps({"key": keys[i], "result": res}, ensure_ascii=False) + "\n")
            n_new[0] += 1
            if n_new[0] % every_ckpt == 0:
                fh.flush(); os.fsync(fh.fileno())
            if n_new[0] % every_log == 0 or n_new[0] == len(todo):
                el = time.time() - t0
                log(f"  {label}: {n_new[0]}/{len(todo)} new ({el:.0f}s, "
                    f"{n_new[0] / max(el, 1e-9):.2f}/s)")
        PROGRESS.job_done(ok=not res.get("_failed", False) if isinstance(res, dict) else True)

    try:
        with ThreadPoolExecutor(max_workers=max(1, n_workers)) as ex:
            list(ex.map(work, todo))
    finally:
        fh.flush(); os.fsync(fh.fileno()); fh.close()
    if errors:
        fatal = [e for e in errors if isinstance(e, FATAL)]
        raise (fatal[0] if fatal else errors[0])
    return [done[k] for k in keys]
