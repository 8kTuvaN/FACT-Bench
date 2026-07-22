"""Layer-3 truth-verifiability filter.

Per plan.md Day 12-13:
  - Claude Sonnet reverse-infers state_operations from the dialogue
  - Compares the inferred operations to the template's ground truth
  - Computes per-template consistency rate
  - < 85% consistency -> flag for manual review (but does not reject)

Per plan.md, this filter runs on a 20% sample (1 variant × 300 templates).

Usage:
    python -m src.generation.filter_verifiability --in data/dialogues/filtered_semantic/dialogues.jsonl --out paper/verifiability.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.templates.llm_client import get_client  # noqa: E402

REVERSE_INFER_PROMPT = """You are reverse-engineering a dialogue. Given the
transcript, infer the state operations that the agent should have performed
on the initial state.

# Initial state
{initial_state}

# Dialogue transcript
{transcript}

# Output (JSON only)
Return a JSON object: {{
  "inferred_operations": [
    {{"op": "ADD" | "MODIFY" | "DELETE" | "KEEP" | "CASCADE",
     "slot": "<name>", "old_value": <...>, "new_value": <...>}},
    ...
  ]
}}"""


def reverse_infer(client, d: dict) -> list[dict]:
    init = d.get("initial_state", {})
    transcript = "\n".join(f"{t.get('role', '?').upper()}: {t.get('text', '')}" for t in d.get("turns", []))
    prompt = REVERSE_INFER_PROMPT.format(
        initial_state=json.dumps(init, ensure_ascii=False, indent=2),
        transcript=transcript,
    )
    try:
        out = client.generate_json(prompt, temperature=0.2, max_retries=1)
        return out.get("inferred_operations", [])
    except Exception:
        return []


def _op_signature(op: dict) -> tuple:
    """Coarse signature for op matching (op + slot only)."""
    return (op.get("op"), op.get("slot"))


def compare(ground_truth: list[dict], inferred: list[dict]) -> dict:
    """Compare ops by (op, slot) signature; ignore KEEP for the match
    (KEEP is implicit in any dialogue, doesn't reflect action quality)."""
    gt = {_op_signature(o) for o in ground_truth if o.get("op") != "KEEP"}
    inf = {_op_signature(o) for o in inferred if o.get("op") != "KEEP"}
    matched = gt & inf
    missed = gt - inf  # ground truth says so, but inference didn't find
    extra = inf - gt  # inference hallucinated an op
    precision = len(matched) / len(inf) if inf else 1.0
    recall = len(matched) / len(gt) if gt else 1.0
    return {
        "matched": len(matched),
        "missed": list(missed),
        "extra": list(extra),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FACT-Bench layer-3 verifiability check")
    parser.add_argument("--in", dest="inp", required=True)
    parser.add_argument("--out", default="paper/verifiability.json")
    parser.add_argument("--provider", default="mock")
    args = parser.parse_args()

    inp = Path(args.inp)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    client = get_client(args.provider)

    # Group dialogues by template, sample 1 variant per template
    by_template: dict[str, list[dict]] = defaultdict(list)
    for line in inp.open("r", encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        by_template[d["template_id"]].append(d)
    # Sample 1 per template (first by variant_idx)
    sample = []
    for tid, dlist in by_template.items():
        dlist.sort(key=lambda d: d.get("variant_idx", 0))
        sample.append(dlist[0])

    print(f"[filter_verifiability] sampling 1 variant per template, n={len(sample)}", flush=True)

    per_template: dict[str, dict] = {}
    for d in sample:
        tid = d["template_id"]
        truth = d.get("state_operations", [])
        inferred = reverse_infer(client, d)
        cmp = compare(truth, inferred)
        per_template[tid] = {"dialogue_id": d["dialogue_id"], **cmp}

    # Aggregate
    n_tpl = len(per_template)
    avg_p = sum(t["precision"] for t in per_template.values()) / n_tpl if n_tpl else 0
    avg_r = sum(t["recall"] for t in per_template.values()) / n_tpl if n_tpl else 0
    flagged = [tid for tid, t in per_template.items() if t["recall"] < 0.85]
    report = {
        "n_templates": n_tpl,
        "avg_precision": round(avg_p, 3),
        "avg_recall": round(avg_r, 3),
        "flagged_count": len(flagged),
        "flagged_for_manual_review": flagged,
        "per_template": per_template,
    }
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"[filter_verifiability] avg_precision={avg_p:.3f} avg_recall={avg_r:.3f} "
        f"flagged={len(flagged)}/{n_tpl}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())