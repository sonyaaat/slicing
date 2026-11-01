"""Shared helpers for the Sliceability UC1 pipeline: paths, config, prompts, file I/O.

Everything this pipeline writes lives under sliceability_uc1/. Nothing here reads or
writes the main pipeline's data/, artifacts/, results/ or cache/ directories; the only
files read from outside this folder are the two .eval logs and main_data/*.csv.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UC1_ROOT = Path(__file__).resolve().parent.parent          # sliceability_uc1/
REPO_ROOT = UC1_ROOT.parent                                 # the repository root
PROMPTS_DIR = UC1_ROOT / "prompts"
RUNS_DIR = UC1_ROOT / "runs"
CACHE_DIR = UC1_ROOT / "cache"
MASTER_CONFIG = UC1_ROOT / "run_config.json"

# Values the annotation schema always allows, in addition to an attribute's own values.
OTHER, UNKNOWN, NA, PARSE_ERROR = "other", "unknown", "not_applicable", "parse_error"
SPECIAL_VALUES = (OTHER, UNKNOWN, NA)


# ---------------------------------------------------------------------------
# Run directory and config
# ---------------------------------------------------------------------------

class Run:
    """One run: its directory, its frozen config, and its call log."""

    def __init__(self, run_dir: Path):
        self.dir = Path(run_dir)
        self.cfg: dict = json.loads((self.dir / "run_config.json").read_text())

    @classmethod
    def create(cls, run_dir: Path | None = None) -> "Run":
        if run_dir is None:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            run_dir = RUNS_DIR / stamp
        run_dir = Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = run_dir / "run_config.json"
        if not cfg_path.exists():
            cfg_path.write_text(MASTER_CONFIG.read_text())
            (run_dir / "CANARY.txt").write_text(
                "This directory contains derived HealthBench data.\n"
                f"Canary: {json.loads(MASTER_CONFIG.read_text())['canary']}\n"
                "Do not publish example text from these files online in plain text.\n")
        return cls(run_dir)

    def path(self, name: str) -> Path:
        return self.dir / name

    @property
    def target(self) -> str:
        return self.cfg["target_score"]

    @property
    def target_model(self) -> str:
        """'gpt' for score_gpt, 'claude' for score_claude, 'mean' for score_mean."""
        return self.target.replace("score_", "")


def config_sha(run: Run) -> str:
    return hashlib.sha256((run.dir / "run_config.json").read_bytes()).hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def write_meta(run: Run, out: Path, step: str, **extra: Any) -> None:
    """Small sidecar next to every artifact: when, from what, under which config."""
    meta = {
        "written_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "step": step,
        "git_commit": git_commit(),
        "run_config_sha256": config_sha(run),
        "target_score": run.target,
        "prompt_version": run.cfg["prompts"]["version"],
        "canary": run.cfg["canary"],
        **extra,
    }
    Path(str(out) + ".meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text())


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def prompts_dir(run: Run) -> Path:
    """prompts/<version>/ - each prompt version lives in its own folder."""
    return PROMPTS_DIR / run.cfg["prompts"].get("dir", run.cfg["prompts"]["version"])


def has_prompt(run: Run, key: str) -> bool:
    return key in run.cfg["prompts"]["files"]


def load_prompt(run: Run, key: str) -> tuple[str, str]:
    """(template text, version tag). The version tag goes into every cache key."""
    fname = run.cfg["prompts"]["files"][key]
    text = (prompts_dir(run) / fname).read_text()
    # A prompt whose text did not change keeps the cache tag of the version it was last
    # changed in (prompts.cache_versions), so identical prompts hit the cache across runs.
    # The claim is checked byte for byte against that version's file.
    tagv = run.cfg["prompts"].get("cache_versions", {}).get(key, run.cfg["prompts"]["version"])
    if tagv != run.cfg["prompts"]["version"]:
        old = (PROMPTS_DIR / tagv / fname).read_text()
        if old != text:
            die(f"prompts.cache_versions says {key} is unchanged since {tagv}, but "
                f"prompts/{tagv}/{fname} differs from the current file")
    return text, f"{key}@{tagv}"


def prompt_shas(run: Run) -> dict[str, str]:
    return {k: hashlib.sha256((prompts_dir(run) / f).read_bytes()).hexdigest()[:16]
            for k, f in run.cfg["prompts"]["files"].items()}


def render(template: str, **slots: str) -> str:
    """Fill <slot> placeholders in one pass.

    One pass matters: user text is inserted verbatim and may itself contain
    `<something>`; a sequential replace would rescan it.
    """
    # slots whose value is empty may be absent from an older template version
    slots = {k: v for k, v in slots.items() if f"<{k}>" in template or v}
    missing = [k for k in slots if f"<{k}>" not in template]
    if missing:
        raise KeyError(f"template has no placeholder(s) {missing}")
    pat = re.compile("<(" + "|".join(re.escape(k) for k in slots) + ")>")
    out = pat.sub(lambda m: slots[m.group(1)], template)
    return out


# ---------------------------------------------------------------------------
# Value normalisation
# ---------------------------------------------------------------------------

def norm_value(v: Any) -> str:
    """Comparison key for a value label: case, quotes, spacing, _ vs space."""
    if v is None:
        return ""
    s = str(v).strip().strip('"\'`').strip().lower()
    s = s.replace("_", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s)
    return s.rstrip(".")


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "attr"


def die(msg: str) -> None:
    print(f"\nABORT: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(1)
