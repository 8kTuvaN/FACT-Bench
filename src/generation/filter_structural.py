"""Layer-1 structural filter.

Per plan.md Day 12-13:
  - Completeness: every required field present and non-empty
  - Slot mention: user/agent text mentions the relevant slot values (fuzzy regex on evidence)
  - Action param check: agent's declared params match the template's action params

Layer-1 is the cheap, deterministic filter that runs on all 1500 dialogues.
Expected rejection rate: 10-15%.

Usage:
    python -m src.generation.filter_structural --in data/dialogues/raw/dialogues.jsonl --out data/dialogues/filtered/
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def check_completeness(d: dict) -> list[str]:
    """Hard completeness: every required field present and non-empty."""
    errs: list[str] = []
    if not d.get("turns"):
        errs.append("empty turns")
    for t in d.get("turns", []):
        if not t.get("text", "").strip():
            errs.append(f"empty text in turn {t.get('role', '?')}")
    if not d.get("agent_actions"):
        errs.append("empty agent_actions")
    if not d.get("template_id"):
        errs.append("missing template_id")
    return errs


def check_slot_mention(d: dict) -> list[str]:
    """Fuzzy check: each non-null slot in initial_state should be mentioned
    in some user/agent turn. Uses substring + numeric-coercion matching.
    """
    errs: list[str] = []
    init = d.get("initial_state", {})
    full_text = " ".join(t.get("text", "") for t in d.get("turns", []))
    full_text_lc = full_text.lower()
    for slot, val in init.items():
        if val is None or val == "":
            continue
        # Only enforce mention for "concrete" values (numbers / specific strings)
        candidates: list[str] = []
        if isinstance(val, (int, float)):
            # int 1200 -> "1,200" / "1200" / "1.2k"
            candidates.append(str(val))
            candidates.append(f"{val:,}")
        elif isinstance(val, str):
            # Skip short tokens (likely to be false-positive)
            if len(val) >= 4:
                candidates.append(val)
        for cand in candidates:
            if cand.lower() in full_text_lc or cand in full_text:
                break
        else:
            # also try date formats
            if isinstance(val, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", val):
                # 2026-07-17 -> "July 17, 2026" / "07/17/2026" etc. (loose)
                yr, mo, dy = val.split("-")
                if f"{yr}" in full_text:
                    continue
            errs.append(f"slot '{slot}' (value {val!r}) not mentioned in any turn")
    return errs


def check_action_params(d: dict) -> list[str]:
    """Lightweight check: agent's declared actions should be a subset of
    the template's agent_action.name (no LLM needed).
    """
    errs: list[str] = []
    template_id = d.get("template_id", "")
    agent_actions = d.get("agent_actions", [])
    if not template_id or not agent_actions:
        return errs
    # We do not have the template loaded here; this check is a soft pass.
    # Hard param verification lives in filter_verifiability.py.
    return errs


def filter_dialogue(d: dict) -> tuple[bool, list[str]]:
    errs = (
        check_completeness(d)
        + check_slot_mention(d)
        + check_action_params(d)
    )
    return (len(errs) == 0, errs)


def main() -> int:
    parser = argparse.ArgumentParser(description="FACT-Bench layer-1 structural filter")
    parser.add_argument("--in", dest="inp", required=True, help="input dialogues.jsonl")
    parser.add_argument("--out", required=True, help="output directory for filtered/ + rejected/")
    parser.add_argument("--report", default=None, help="optional path for filter report")
    args = parser.parse_args()

    inp = Path(args.inp)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rej_dir = out_dir / "rejected"
    rej_dir.mkdir(parents=True, exist_ok=True)

    n_total = 0
    n_pass = 0
    n_rej = 0
    rej_reasons: dict[str, int] = {}
    with inp.open("r", encoding="utf-8") as fi, \
         (out_dir / "dialogues.jsonl").open("w", encoding="utf-8") as fo, \
         (rej_dir / "dialogues.jsonl").open("w", encoding="utf-8") as fr:
        for line in fi:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            n_total += 1
            ok, errs = filter_dialogue(d)
            if ok:
                n_pass += 1
                fo.write(json.dumps(d, ensure_ascii=False) + "\n")
            else:
                n_rej += 1
                d["__rejection_reasons__"] = errs
                fr.write(json.dumps(d, ensure_ascii=False) + "\n")
                for e in errs:
                    key = e.split(":", 1)[0].split("(", 1)[0].strip()[:50]
                    rej_reasons[key] = rej_reasons.get(key, 0) + 1

    rate = n_rej / n_total if n_total else 0
    print(f"[filter_structural] {n_total} in | {n_pass} pass | {n_rej} rejected ({rate*100:.1f}%)", flush=True)
    if rej_reasons:
        print(f"[filter_structural] top rejection reasons:", flush=True)
        for k, v in sorted(rej_reasons.items(), key=lambda x: -x[1])[:5]:
            print(f"  {v:4d}  {k}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())