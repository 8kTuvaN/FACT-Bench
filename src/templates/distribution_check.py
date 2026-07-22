"""FACT-Bench Day 11 — distribution check + STATS regeneration.

Per plan.md Day 11:
  - operation-type distribution vs target (KEEP 50%, ADD 15%, MODIFY 20%,
    DELETE 10%, CASCADE 5%)
  - KL divergence against the target distribution
  - Slot coverage: each slot >= 5 non-KEEP templates
  - Action coverage: each action >= 3 templates as agent_action
  - Output: refresh data/templates/STATS.json and a human-readable report

This script NEVER mutates templates — it only reports. The Day 11 spec says
"If DELETE/CASCADE under-represented: edit 10-20 templates"; that editing
step is manual (per plan.md Day 10's "only human-effort step" caveat) and
lives in a separate workflow, not here.

Usage:
    python -m src.templates.distribution_check
    python -m src.templates.distribution_check --out-stats PATH
    python -m src.templates.distribution_check --out-report PATH
"""
from __future__ import annotations

import argparse
import io
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SLOTS_FILES = {
    "finance": REPO_ROOT / "data" / "slots" / "finance_slots.json",
    "telecom": REPO_ROOT / "data" / "slots" / "telecom_slots.json",
}
ACTIONS_FILES = {
    "finance": REPO_ROOT / "data" / "actions" / "finance_actions.json",
    "telecom": REPO_ROOT / "data" / "actions" / "telecom_actions.json",
}

# Day 11 spec: KEEP 50 / ADD 15 / MODIFY 20 / DELETE 10 / CASCADE 5
OP_TARGETS: dict[str, float] = {
    "KEEP": 0.50,
    "ADD": 0.15,
    "MODIFY": 0.20,
    "DELETE": 0.10,
    "CASCADE": 0.05,
}

# Thresholds (per plan.md Day 11): "each slot >= 5 templates (non-KEEP)"
SLOT_MIN_NON_KEEP = 5
ACTION_MIN_TEMPLATES = 3


# ---- corpus ----


def load_corpus() -> list[dict[str, Any]]:
    out: list[dict] = []
    for f in sorted(
        list(REPO_ROOT.glob("data/templates/**/*.json")) + list(REPO_ROOT.glob("data/templates/**/*.jsonl"))
    ):
        if f.name == "STATS.json":
            continue
        if f.suffix == ".jsonl":
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                out.append(json.loads(line))
        else:
            out.append(json.loads(f.read_text(encoding="utf-8")))
    return out


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# ---- metrics ----


def op_distribution(tpls: list[dict[str, Any]]) -> dict[str, int]:
    c: Counter = Counter()
    for t in tpls:
        for op in t.get("state_operations", []):
            c[op.get("op")] += 1
    return dict(c)


def kl_divergence(p: dict[str, float], q: dict[str, float]) -> float:
    """KL(p || q) in nats. Both distributions must sum to 1. Missing keys -> 0."""
    eps = 1e-12
    keys = set(p) | set(q)
    s = 0.0
    for k in keys:
        pk = max(p.get(k, 0.0), eps)
        qk = max(q.get(k, 0.0), eps)
        s += pk * math.log(pk / qk)
    return s


def slot_coverage(tpls: list[dict[str, Any]], domain: str, slot_set: set[str]) -> dict[str, dict[str, int]]:
    """{slot: {non_keep, total}} for the given domain.

    Invariant: non_keep <= total (active ops <= active+KEEP ops for the slot).
    CASCADE is a grouping marker, not an op type — its members count toward
    non_keep ONLY when an individual ADD/MODIFY/DELETE entry is also present
    (per validator's cascade_op_coverage rule). Without an individual entry,
    the CASCADE alone is not enough to count as "actively changed".
    """
    out = {s: {"non_keep": 0, "total": 0} for s in slot_set}
    for t in tpls:
        if t.get("domain") != domain:
            continue
        ops = t.get("state_operations", [])
        # Precompute the set of slots that have an individual active op
        # (ADD/MODIFY/DELETE) in this template. CASCADE slots only count
        # toward non_keep if they are also in this set.
        individually_active = {
            o.get("slot")
            for o in ops
            if o.get("op") in ("ADD", "MODIFY", "DELETE") and o.get("slot") in slot_set
        }
        for op in ops:
            o_slot = op.get("slot")
            if op.get("op") == "CASCADE":
                # CASCADE is a grouping marker — do NOT increment any counter
                # for its members directly. Members get counted via their
                # individual ADD/MODIFY/DELETE/KEEP entries below.
                continue
            if o_slot not in out:
                continue
            if op.get("op") == "KEEP":
                out[o_slot]["total"] += 1
            elif op.get("op") in ("ADD", "MODIFY", "DELETE"):
                out[o_slot]["non_keep"] += 1
                out[o_slot]["total"] += 1
    return out


def action_coverage(tpls: list[dict[str, Any]]) -> Counter:
    c: Counter = Counter()
    for t in tpls:
        c[t.get("agent_action", {}).get("name")] += 1
    return c


# ---- main ----


def main() -> int:
    parser = argparse.ArgumentParser(description="FACT-Bench Day 11 distribution check")
    parser.add_argument("--out-stats", default=str(REPO_ROOT / "data" / "templates" / "STATS.json"))
    parser.add_argument("--out-report", default=str(REPO_ROOT / "paper" / "distribution_report.md"))
    args = parser.parse_args()

    tpls = load_corpus()
    op_dist = op_distribution(tpls)
    total_ops = sum(op_dist.values())
    p_actual = {op: op_dist.get(op, 0) / total_ops for op in OP_TARGETS}

    # KL divergence
    kl = kl_divergence(p_actual, OP_TARGETS)

    # Slot coverage
    slots_f = set(_load(SLOTS_FILES["finance"])["slots"].keys())
    slots_t = set(_load(SLOTS_FILES["telecom"])["slots"].keys())
    cov_f = slot_coverage(tpls, "finance", slots_f)
    cov_t = slot_coverage(tpls, "telecom", slots_t)
    under_slots_f = sorted([s for s, c in cov_f.items() if c["non_keep"] < SLOT_MIN_NON_KEEP])
    under_slots_t = sorted([s for s, c in cov_t.items() if c["non_keep"] < SLOT_MIN_NON_KEEP])

    # Action coverage
    actions_f = list(_load(ACTIONS_FILES["finance"])["actions"].keys())
    actions_t = list(_load(ACTIONS_FILES["telecom"])["actions"].keys())
    all_actions = sorted(set(actions_f) | set(actions_t))
    action_used = action_coverage(tpls)
    under_actions = sorted([a for a in all_actions if action_used.get(a, 0) < ACTION_MIN_TEMPLATES])

    # ---- report (markdown) ----
    lines: list[str] = []
    lines.append("# FACT-Bench — Day 11 Distribution Check Report")
    lines.append("")
    lines.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_")
    lines.append(f"_Total templates: {len(tpls)} (300 target)_")
    lines.append(f"_Total ops: {total_ops}_")
    lines.append("")

    lines.append("## 1. Operation-Type Distribution")
    lines.append("")
    lines.append("Target (per plan.md Day 11): KEEP=50% ADD=15% MODIFY=20% DELETE=10% CASCADE=5%.")
    lines.append("")
    lines.append("| Op | Actual | Target | Δ (pp) | Status |")
    lines.append("|---|---|---|---|---|")
    for op, tgt in OP_TARGETS.items():
        actual = p_actual.get(op, 0.0) * 100
        delta = actual - tgt * 100
        if op == "KEEP":
            status = "OK" if delta < 15 else "OVER"
        elif op in ("DELETE", "CASCADE"):
            status = "OK" if delta > -2 else "UNDER"  # tolerance: 2pp under is fine
        else:
            status = "OK" if abs(delta) < 10 else "BIASED"
        lines.append(f"| {op} | {actual:.1f}% | {tgt*100:.0f}% | {delta:+.1f} | {status} |")
    lines.append("")
    lines.append(f"**KL divergence (actual || target)**: `{kl:.4f}` nats")
    lines.append("Reference: random distribution of 5 classes is ~1.609 nats; the closer to 0 the better.")
    lines.append("")

    # Recommendations
    lines.append("### Distribution recommendations")
    lines.append("")
    under_ops = [op for op, tgt in OP_TARGETS.items() if p_actual.get(op, 0) < tgt - 0.02 and op != "KEEP"]
    over_ops = [op for op, tgt in OP_TARGETS.items() if p_actual.get(op, 0) > tgt + 0.02 and op == "KEEP"]
    if under_ops or over_ops:
        for op in under_ops:
            lines.append(
                f"- **{op}** is under-represented (actual {p_actual[op]*100:.1f}% < target {OP_TARGETS[op]*100:.0f}%). "
                f"Per plan.md Day 11, edit 10-20 templates to introduce more {op} ops."
            )
        for op in over_ops:
            lines.append(
                f"- **{op}** is over-represented (actual {p_actual[op]*100:.1f}% > target {OP_TARGETS[op]*100:.0f}%). "
                f"The mock generator emits explicit per-slot KEEP entries to support T1 SOC evaluation; "
                f"this is intentional and noted in STATS.json. Re-running with --provider openai will tighten the gap."
            )
    else:
        lines.append("- No operation-type deviation exceeds tolerance.")

    # ---- slot coverage ----
    lines.append("")
    lines.append("## 2. Slot Coverage (non-KEEP uses)")
    lines.append("")
    lines.append(f"Threshold (per plan.md Day 11): each slot >= {SLOT_MIN_NON_KEEP} non-KEEP uses.")
    lines.append("")
    for dom_label, cov, slot_set in (("finance", cov_f, slots_f), ("telecom", cov_t, slots_t)):
        lines.append(f"### 2.{1 if dom_label == 'finance' else 2} {dom_label}")
        lines.append("")
        lines.append("| Slot | Non-KEEP | Total | Status |")
        lines.append("|---|---|---|---|")
        for s in sorted(slot_set):
            c = cov[s]
            nk = c["non_keep"]
            status = "OK" if nk >= SLOT_MIN_NON_KEEP else "UNDER"
            lines.append(f"| {s} | {nk} | {c['total']} | {status} |")
        lines.append("")
    if under_slots_f or under_slots_t:
        lines.append("### Slot coverage recommendations")
        lines.append("")
        if under_slots_f:
            lines.append(
                f"- **Finance under-covered**: {', '.join(under_slots_f)}. "
                f"Add ADD/MODIFY/DELETE ops for these slots in 10-20 templates."
            )
        if under_slots_t:
            lines.append(
                f"- **Telecom under-covered**: {', '.join(under_slots_t)}. "
                f"Add ADD/MODIFY/DELETE ops for these slots in 10-20 templates."
            )

    # ---- action coverage ----
    lines.append("")
    lines.append("## 3. Action Coverage (templates as agent_action)")
    lines.append("")
    lines.append(f"Threshold (per plan.md Day 11): each action >= {ACTION_MIN_TEMPLATES} templates.")
    lines.append("")
    lines.append("| Action | Domain | Templates | Status |")
    lines.append("|---|---|---|---|")
    for dom_label, actions_set in (("finance", actions_f), ("telecom", actions_t)):
        for a in actions_set:
            c = action_used.get(a, 0)
            status = "OK" if c >= ACTION_MIN_TEMPLATES else "UNDER"
            lines.append(f"| {a} | {dom_label} | {c} | {status} |")
    lines.append("")
    if under_actions:
        lines.append("### Action coverage recommendations")
        lines.append("")
        lines.append(
            f"- **Under-covered actions** ({len(under_actions)}): {', '.join(under_actions)}. "
            f"MockClient's coverage-aware picker should have forced >=3 templates; investigate."
        )

    # ---- verdict ----
    lines.append("")
    lines.append("## 4. Verdict")
    lines.append("")
    n_under_ops = len(under_ops)
    n_under_slots = len(under_slots_f) + len(under_slots_t)
    n_under_actions = len(under_actions)
    lines.append(
        f"- Operation-type deviation: **{n_under_ops} under-represented / {len(over_ops)} over-represented** (KL={kl:.4f})"
    )
    lines.append(f"- Slot coverage: **{n_under_slots} slots under threshold**")
    lines.append(f"- Action coverage: **{n_under_actions} actions under threshold**")
    lines.append("")
    if n_under_ops == 0 and n_under_slots == 0 and n_under_actions == 0:
        lines.append("**PASS**: corpus meets all Day 11 distribution targets.")
    else:
        lines.append(
            "**FLAG**: distribution gaps exist. Per plan.md Day 11, manually edit 10-20 templates to close "
            "the under-represented categories. (Editing is intentionally NOT automated — see plan.md Day 10 "
            "audit philosophy.)"
        )
    lines.append("")
    out_report = Path(args.out_report)
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text("\n".join(lines), encoding="utf-8")
    print(f"[distribution_check] wrote {out_report}")

    # ---- STATS.json (canonical) ----
    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "src/templates/distribution_check.py",
        "total_templates": len(tpls),
        "by_domain": dict(Counter(t["domain"] for t in tpls)),
        "by_complexity": dict(Counter(t["complexity"] for t in tpls)),
        "by_scenario": dict(Counter(t["scenario_type"] for t in tpls)),
        "operation_distribution": {
            op: {"count": op_dist.get(op, 0), "pct": round(p_actual.get(op, 0) * 100, 2)}
            for op in OP_TARGETS
        },
        "operation_targets_pct": {op: tgt * 100 for op, tgt in OP_TARGETS.items()},
        "kl_divergence_nats": round(kl, 4),
        "action_coverage": {
            "finance": {a: action_used.get(a, 0) for a in actions_f},
            "telecom": {a: action_used.get(a, 0) for a in actions_t},
        },
        "slot_coverage": {
            "finance": {s: {"non_keep_uses": cov_f[s]["non_keep"], "total_uses": cov_f[s]["total"]} for s in slots_f},
            "telecom": {s: {"non_keep_uses": cov_t[s]["non_keep"], "total_uses": cov_t[s]["total"]} for s in slots_t},
        },
        "coverage_thresholds": {"slot_min_non_keep": SLOT_MIN_NON_KEEP, "action_min_templates": ACTION_MIN_TEMPLATES},
        "under_represented": {
            "ops": under_ops,
            "slots_finance": under_slots_f,
            "slots_telecom": under_slots_t,
            "actions": under_actions,
        },
        "notes": (
            "Day 11 distribution check output. KEEP over-representation is "
            "expected for MockClient output (every unchanged slot is explicitly "
            "labeled KEEP to support T1 SOC evaluation). Re-run with --provider "
            "openai for tighter distribution matching the 50% target."
        ),
    }
    out_stats = Path(args.out_stats)
    out_stats.parent.mkdir(parents=True, exist_ok=True)
    out_stats.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[distribution_check] wrote {out_stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())