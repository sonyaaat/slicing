"""LLM client for UC1: disk cache, multi-key pool, 429 handling, per-call token log.

Self-contained on purpose (the main pipeline's src/llm.py is not imported, so nothing
done here can change an earlier experiment's behaviour). The failure rules are the
same as there:

  * content None or empty is a FAILURE, never an empty answer, and is not cached;
  * a 429 is not a failure, it is waited out on the same key slot;
  * nothing is dropped silently: every attempt, cached or not, is one line in
    runs/<ts>/calls.jsonl with its token counts.

Cache key = sha256(model, endpoint, prompt version, sha256(rendered prompt), every
sampling parameter, seed, retry salt). The rendered prompt contains the input, so this
is the (model, prompt version, input hash) key the run brief asks for, plus the
parameters whose change would make a cached answer silently wrong. Cache files live in
sliceability_uc1/cache/ and are shared by all runs, so a rerun never pays twice.
"""

from __future__ import annotations

import hashlib
import json
import os
import queue
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Sequence

from dotenv import load_dotenv
from openai import (APIConnectionError, APITimeoutError, InternalServerError, OpenAI,
                    RateLimitError)

from common import CACHE_DIR, REPO_ROOT, Run, log

load_dotenv(REPO_ROOT / ".env")


class LLMError(RuntimeError):
    pass


_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I | re.M)


def parse_json(text: str) -> Any:
    if text is None:
        raise ValueError("content is None")
    t = _FENCE.sub("", text).strip()
    cands = [(t.find("{"), t.rfind("}")), (t.find("["), t.rfind("]"))]
    cands = [(i, j) for i, j in cands if i != -1 and j > i]
    if not cands:
        raise ValueError(f"no JSON found in {t[:120]!r}")
    i, j = min(cands)
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError as e:
        # A complete JSON value followed by more text ("Extra data") is read as its first
        # complete value. Added 2026-10-15 after replies with a second object appended.
        try:
            obj, _ = json.JSONDecoder().raw_decode(t[i:])
            return obj
        except json.JSONDecodeError:
            raise ValueError(f"JSON decode error at pos {e.pos}: {e.msg}") from None


class CallLog:
    """Append-only call log for one run. Thread-safe."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def write(self, rec: dict) -> None:
        line = json.dumps(rec, ensure_ascii=False)
        with self._lock, open(self.path, "a") as f:
            f.write(line + "\n")


class LLM:
    """One model role ('strong' or 'annotation') from run_config.json."""

    def __init__(self, run: Run, role: str, *, model_override: str | None = None):
        spec = dict(run.cfg["models"][role])
        if model_override:
            spec["model"] = model_override
        ep = run.cfg["endpoints"][spec["endpoint"]]
        self.role = role
        self.model = spec["model"]
        self.endpoint = spec["endpoint"]
        self.temperature = spec["temperature"]
        self.token_param = spec["token_param"]
        self.max_tokens = spec["max_tokens"]
        self.price_in = spec["price_in_per_1m"] / 1e6
        self.price_out = spec["price_out_per_1m"] / 1e6
        self.extra_body = ep.get("extra_body") or {}
        # Optional per-endpoint cache namespace. Two gateways serving the same model name
        # are not assumed to be the same deployment, so their replies must not share a
        # cache entry. Absent (run 1) -> the key is exactly as before.
        self.cache_tag = ep.get("cache_tag")
        lc = run.cfg["llm"]
        self.max_parse_retries = lc["max_parse_retries"]
        self.rl_retries = lc["rate_limit_retries"]
        self.rl_backoff = lc["rate_limit_backoff_s"]
        self.conn_retries = lc.get("connection_retries", 12)
        self.calllog = CallLog(run.path("calls.jsonl"))

        clients = []
        for env in ep["api_key_envs"]:
            key = os.environ.get(env)
            if not key:
                raise LLMError(f"${env} is not set (endpoint {self.endpoint})")
            kw: dict[str, Any] = dict(api_key=key, timeout=spec["timeout_s"], max_retries=0)
            if ep.get("base_url"):
                kw["base_url"] = ep["base_url"]
            clients.append(OpenAI(**kw))
        # One queue entry per concurrent slot; a worker holds a slot for the whole call.
        self._slots: queue.Queue = queue.Queue()
        for _ in range(ep["per_key_concurrency"]):
            for c in clients:
                self._slots.put(c)
        self.n_slots = self._slots.qsize()
        self.n_keys = len(clients)

    # -- cache --------------------------------------------------------------

    def _key(self, prompt: str, prompt_version: str, seed: int | None, salt: str) -> str:
        payload = json.dumps({
            "model": self.model, "endpoint": self.endpoint, "prompt_version": prompt_version,
            "input_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "temperature": self.temperature, "token_param": self.token_param,
            "max_tokens": self.max_tokens, "extra_body": self.extra_body,
            "seed": seed, "salt": salt,
            **({"cache_tag": self.cache_tag} if self.cache_tag else {}),
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def _cache_path(key: str) -> Path:
        d = CACHE_DIR / key[:2]
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{key}.json"

    # -- one raw call -------------------------------------------------------

    def _api(self, prompt: str, seed: int | None) -> tuple[str | None, int, int, str]:
        kw: dict[str, Any] = {self.token_param: self.max_tokens}
        if self.temperature is not None:
            kw["temperature"] = self.temperature
        if seed is not None:
            kw["seed"] = seed
        if self.extra_body:
            kw["extra_body"] = self.extra_body
        client = self._slots.get()
        try:
            rl, conn = 0, 0
            while True:
                try:
                    r = client.chat.completions.create(
                        model=self.model, messages=[{"role": "user", "content": prompt}], **kw)
                    break
                except RateLimitError as e:
                    rl += 1
                    if rl > self.rl_retries:
                        raise LLMError(f"429 after {self.rl_retries} waits: {e}") from None
                    time.sleep(min(2.0, self.rl_backoff * (2 ** min(rl, 3))
                                   * (0.5 + random.random())))
                except (APIConnectionError, APITimeoutError, InternalServerError) as e:
                    # Gateway outage, not a model answer. Waited out on the same slot so it
                    # does not consume a parse retry (a 15-minute Janus outage on
                    # 2026-10-15 otherwise turned good cells into parse errors).
                    conn += 1
                    self.calllog.write({"ts": time.time(), "role": self.role,
                                        "model": self.model, "event": "connection_retry",
                                        "error": f"{type(e).__name__}: {str(e)[:200]}"})
                    if conn > self.conn_retries:
                        raise LLMError(f"connection failed {conn} times: {e}") from None
                    time.sleep(min(30.0, 5.0 * 2 ** min(conn, 3)) * (0.5 + random.random()))
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
            rec = json.loads(path.read_text())
            self.calllog.write({**base, "cached": True, "tokens_in": rec["tokens_in"],
                                "tokens_out": rec["tokens_out"], "cost_usd": 0.0,
                                "latency_s": 0.0, "ok": True})
            return rec["text"]
        t0 = time.time()
        try:
            text, tin, tout, fin = self._api(prompt, seed)
        except Exception as e:
            self.calllog.write({**base, "cached": False, "tokens_in": 0, "tokens_out": 0,
                                "cost_usd": 0.0, "latency_s": time.time() - t0, "ok": False,
                                "error": f"api: {type(e).__name__}: {str(e)[:300]}"})
            raise LLMError(f"API failure for {item}: {type(e).__name__}: {e}") from None
        lat = time.time() - t0
        cost = tin * self.price_in + tout * self.price_out
        if text is None or not str(text).strip():
            self.calllog.write({**base, "cached": False, "tokens_in": tin, "tokens_out": tout,
                                "cost_usd": cost, "latency_s": lat, "ok": False,
                                "error": f"null_content finish_reason={fin}"})
            raise LLMError(f"null content for {item} (finish_reason={fin}, out={tout})")
        path.write_text(json.dumps({"text": text, "tokens_in": tin, "tokens_out": tout,
                                    "finish_reason": fin, "model": self.model,
                                    "prompt_version": prompt_version, "seed": seed},
                                   ensure_ascii=False))
        self.calllog.write({**base, "cached": False, "tokens_in": tin, "tokens_out": tout,
                            "cost_usd": cost, "latency_s": lat, "ok": True,
                            "finish_reason": fin})
        return text

    def complete_json(self, prompt: str, *, step: str, prompt_version: str, item: str,
                      seed: int | None = None,
                      validator: Callable[[Any], Any] | None = None,
                      salt_prefix: str = "") -> Any:
        """Completion + JSON parse + optional validator, retried with a new cache salt.

        A validator raises ValueError to reject a reply. Every rejected attempt is
        logged; after the last one LLMError is raised. Nothing returns None.
        """
        last = None
        for attempt in range(self.max_parse_retries):
            salt = salt_prefix if attempt == 0 else f"{salt_prefix}retry{attempt}"
            try:
                text = self.complete(prompt, step=step, prompt_version=prompt_version,
                                     item=item, seed=seed, salt=salt)
                obj = parse_json(text)
                return validator(obj) if validator else obj
            except (ValueError, LLMError) as e:
                last = e
                self.calllog.write({"ts": time.time(), "step": step, "role": self.role,
                                    "model": self.model, "prompt_version": prompt_version,
                                    "item": item, "seed": seed, "salt": salt,
                                    "event": "rejected", "error": str(e)[:400]})
        raise LLMError(f"{self.max_parse_retries} attempts failed for {item}: {last}")


def run_parallel(fn: Callable[[Any], Any], items: Sequence[Any], n_workers: int,
                 label: str, every: int = 200) -> list[Any]:
    """Apply fn to items concurrently; results in input order.

    An exception is RETURNED in place of the result (never swallowed), so the caller
    decides how to record it.
    """
    out: list[Any] = [None] * len(items)
    done = [0]
    lock = threading.Lock()
    t0 = time.time()

    def work(i):
        try:
            out[i] = fn(items[i])
        except Exception as e:                       # recorded, not dropped
            out[i] = e
        with lock:
            done[0] += 1
            if done[0] % every == 0 or done[0] == len(items):
                el = time.time() - t0
                log(f"  {label}: {done[0]}/{len(items)} ({el:.0f}s, "
                    f"{done[0] / max(el, 1e-9):.1f}/s)")

    with ThreadPoolExecutor(max_workers=max(1, n_workers)) as ex:
        list(ex.map(work, range(len(items))))
    return out
