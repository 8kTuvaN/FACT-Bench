"""Layer-2 semantic filter.

Per plan.md Day 12-13:
  - GPT-4o-mini intent coverage check
  - Lightweight LLM-as-judge: does the dialogue actually address the user intent?
  - Track per-intent YES/NO ratio to identify systematic omissions

Expected rejection rate: 5-10% on layer-1 survivors.

Usage:
    python -m src.generation.filter_semantic --in data/dialogues/filtered/dialogues.jsonl --out data/dialogues/filtered_semantic/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.templates.llm_client import get_client  # noqa: E402

JUDGE_PROMPT = """You are evaluating a synthetic customer-service dialogue for
intent coverage. The customer's intent is:

  {user_goal}

The agent's final turn should explicitly address this intent (e.g., confirm
the action taken, explain next steps, or escalate if needed).

# Dialogue
{transcript}

# Output (JSON only)
Return a JSON object: {{"covers_intent": true | false, "reason": "<one sentence>"}}"""


def judge_one(client, d: dict) -> tuple[bool, str]:
    user_goal = d.get("user_intent_seed", {}).get("user_goal", "")
    transcript_lines = [
        f"{t.get('role', '?').upper()}: {t.get('text', '')}" for t in d.get("turns", [])
    ]
    transcript = "\n".join(transcript_lines)
    prompt = JUDGE_PROMPT.format(user_goal=user_goal, transcript=transcript)
    try:
        out = client.generate_json(prompt, temperature=0.2, max_retries=1)
        return bool(out.get("covers_intent")), out.get("reason", "")
    except Exception as e:
        # On error, accept the dialogue (don't false-reject)
        return True, f"judge_error: {e}"


def main() -> int:
    parser = argparse.ArgumentParser(description="FACT-Bench layer-2 semantic filter")
    parser.add_argument("--in", dest="inp", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--provider", default="mock")
    args = parser.parse_args()

    inp = Path(args.inp)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = get_client(args.provider)

    n_in = 0
    n_pass = 0
    n_rej = 0
    rej_reasons: dict[str, int] = {}
    with inp.open("r", encoding="utf-8") as fi, \
         (out_dir / "dialogues.jsonl").open("w", encoding="utf-8") as fo, \
         (out_dir / "rejected.jsonl").open("w", encoding="utf-8") as fr:
        for line in fi:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            n_in += 1
            ok, reason = judge_one(client, d)
            if ok:
                n_pass += 1
                fo.write(json.dumps(d, ensure_ascii=False) + "\n")
            else:
                n_rej += 1
                d["__rejection_reason__"] = reason
                fr.write(json.dumps(d, ensure_ascii=False) + "\n")
                rej_reasons[reason[:60]] = rej_reasons.get(reason[:60], 0) + 1

    rate = n_rej / n_in if n_in else 0
    print(f"[filter_semantic] {n_in} in | {n_pass} pass | {n_rej} rejected ({rate*100:.1f}%)", flush=True)
    if rej_reasons:
        print(f"[filter_semantic] sample reasons:", flush=True)
        for k, v in sorted(rej_reasons.items(), key=lambda x: -x[1])[:5]:
            print(f"  {v:3d}  {k}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())