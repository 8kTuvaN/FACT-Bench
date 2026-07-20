"""FACT-Bench batch template generator.

Generates templates in batches per (domain, complexity) using a pluggable LLM
client (default: MockClient for offline runs).

Batch plan (per plan.md Day 8-9):
  - finance simple: 75
  - telecom simple: 75
  - finance medium: 47
  - telecom medium: 47
  - finance complex: 18
  - telecom complex: 18
  Total: 280 new + 20 seed = 300 templates.

Each generated template is validated against src/templates/validator.py.
Failed validations are retried up to 3 times before being logged + skipped.

Usage:
    python -m src.templates.batch_generator --provider mock
    python -m src.templates.batch_generator --provider openai --model gpt-4o
    python -m src.templates.batch_generator --provider mock --dry-run     # print plan only
"""
from __future__ import annotations

import argparse
import io
import json
import random
import sys
from pathlib import Path
from typing import Any

from src.templates.llm_client import get_client
from src.templates.validator import ValidationError, validate

REPO_ROOT = Path(__file__).resolve().parents[2]
SLOTS_FILES = {
    "finance": REPO_ROOT / "data" / "slots" / "finance_slots.json",
    "telecom": REPO_ROOT / "data" / "slots" / "telecom_slots.json",
}
GROUPS_FILES = {
    "finance": REPO_ROOT / "data" / "slots" / "semantic_groups_finance.json",
    "telecom": REPO_ROOT / "data" / "slots" / "semantic_groups_telecom.json",
}
ACTIONS_FILES = {
    "finance": REPO_ROOT / "data" / "actions" / "finance_actions.json",
    "telecom": REPO_ROOT / "data" / "actions" / "telecom_actions.json",
}

# Plan: simple 75+75, medium 47+47, complex 18+18 = 280
BATCH_PLAN: dict[tuple[str, str], int] = {
    ("finance", "simple"): 75,
    ("telecom", "simple"): 75,
    ("finance", "medium"): 47,
    ("telecom", "medium"): 47,
    ("finance", "complex"): 18,
    ("telecom", "complex"): 18,
}

# Scenario pools per (domain, complexity) — drives template diversity
SCENARIO_POOLS: dict[tuple[str, str], list[str]] = {
    ("finance", "simple"): [
        "pure_query", "single_add", "single_modify", "single_delete",
        "loan_application", "fraud_report",
    ],
    ("telecom", "simple"): [
        "pure_query", "single_add", "single_modify",
        "outage_report", "dispute_bill",
    ],
    ("finance", "medium"): [
        "cascade_autopay_enable", "multi_slot_mixed", "target_shift",
        "loan_application", "fraud_report",
    ],
    ("telecom", "medium"): [
        "cascade_plan_change", "cascade_addon_subscribe",
        "device_activation", "multi_slot_mixed", "outage_report",
    ],
    ("finance", "complex"): [
        "sop_violation", "no_action_abstention", "target_shift",
    ],
    ("telecom", "complex"): [
        "sop_violation", "no_action_abstention", "device_activation",
    ],
}


# -------- ontology loader (module-level for cross-import) --------


_ONT: dict[str, Any] | None = None


def _ontology() -> dict[str, Any]:
    global _ONT
    if _ONT is not None:
        return _ONT
    slots = {dom: json.load(io.open(p, "r", encoding="utf-8"))["slots"] for dom, p in SLOTS_FILES.items()}
    groups = {dom: json.load(io.open(p, "r", encoding="utf-8"))["groups"] for dom, p in GROUPS_FILES.items()}
    actions = {dom: json.load(io.open(p, "r", encoding="utf-8"))["actions"] for dom, p in ACTIONS_FILES.items()}
    _ONT = {"slots": slots, "groups": groups, "actions": actions}
    return _ONT


# -------- helpers --------


def _gen_value(slot_name: str, slot: dict, rng: random.Random) -> Any:
    """Generate a concrete value for a slot that satisfies its validation."""
    if "enum" in slot and slot["enum"]:
        return rng.choice(slot["enum"])
    vmin = slot.get("validation", {}).get("min")
    vmax = slot.get("validation", {}).get("max")
    stype = slot["type"]
    if stype == "string":
        rx = slot.get("validation", {}).get("regex", "")
        if "1[3-9]\\d{9}" in rx:
            return "138" + "".join(rng.choices("0123456789", k=9))
        if "@" in rx:
            users = ["alex.chen", "priya.shankar", "jordan.rivera", "wei.li", "kai.tanaka"]
            return rng.choice(users) + "@example.com"
        if "FR-\\d{8}" in rx:
            return "FR-" + "".join(rng.choices("0123456789", k=8))
        if "^\\d{4}$" in rx:
            return "".join(rng.choices("0123456789", k=4))
        if "^\\d{15}$" in rx:
            return "".join(rng.choices("0123456789", k=15))
        if rx.startswith("^([1-9]|1[0-9]|2[0-8])"):
            return str(rng.randint(1, 28))
        if "YYYY-MM-DD" in rx:
            return f"2026-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}"
        # generic non-empty string
        pool = ["First National Bank", "Wells Fargo", "HSBC UK", "Chase", "Citi"]
        return rng.choice(pool)
    if stype == "integer":
        lo = int(vmin) if vmin is not None else 0
        hi = int(vmax) if vmax is not None else 1000
        return rng.randint(lo, hi)
    if stype == "float":
        lo = float(vmin) if vmin is not None else 0.0
        hi = float(vmax) if vmax is not None else 1000.0
        return round(rng.uniform(lo, max(lo + 0.01, hi)), 2)
    return None


def _make_initial_state(domain: str, slot_pool: dict, rng: random.Random) -> dict:
    """Generate a plausible initial state for the dialogue. Most slots null; ~5-8 set."""
    init: dict = {}
    # Always set: phone/email/address for contact identity, plus domain-anchor
    anchors = {
        "finance": ["card_last_four", "card_holder_name", "phone", "email"],
        "telecom": ["phone", "email", "address", "plan_name", "payment_method"],
    }
    for s in anchors[domain]:
        init[s] = _gen_value(s, slot_pool[s], rng)
    # Add a few more random slots (so there's room for ADD/MODIFY/CASCADE)
    extras = rng.sample(list(slot_pool.keys()), k=min(6, len(slot_pool)))
    for s in extras:
        if s in init:
            continue
        init[s] = _gen_value(s, slot_pool[s], rng)
    return init


def _apply_action_to_state(
    action_name: str,
    action: dict,
    init: dict,
    slot_pool: dict,
    group_pool: dict,
    rng: random.Random,
    scenario: str,
) -> tuple[dict, list]:
    """Apply the action to a copy of init, producing (final, ops).

    - CASCADE scenarios rewrite the whole semantic group (when 3+ slots
      in the group exist) plus add a CASCADE entry.
    - MODIFY scenarios change 1-2 slots.
    - ADD scenarios introduce 1-3 new slot values.
    - DELETE scenarios null out 1 slot.
    - QUERY scenarios: KEEP all.
    """
    import copy

    final = copy.deepcopy(init)
    ops: list = []

    # Find which groups the action touches (via side_effects ∩ groups)
    side_effects = set(action.get("side_effects", []))
    cascade_groups = [g for g, members in group_pool.items() if set(members) & side_effects and len(members) >= 3]

    if scenario.startswith("cascade_") and cascade_groups:
        g = cascade_groups[0]
        members = group_pool[g]
        # Rewrite all group members
        for s in members:
            if s in slot_pool:
                final[s] = _gen_value(s, slot_pool[s], rng)
        ops.append({
            "op": "CASCADE", "group": g, "slots": members,
            "cause": f"{action_name} rewrites {g} group atomically",
        })
        # Per-slot MODIFY/ADD entries
        for s in members:
            old = init.get(s)
            new = final.get(s)
            if old is None:
                ops.append({"op": "ADD", "slot": s, "value": new})
            elif old != new:
                ops.append({"op": "MODIFY", "slot": s, "old_value": old, "new_value": new})
            else:
                ops.append({"op": "KEEP", "slot": s})

    elif scenario == "multi_slot_mixed":
        # Touch 2-4 slots: mix of ADD/MODIFY/DELETE
        candidates = list(set(side_effects) | set(action.get("required_params", [])))
        candidates = [s for s in candidates if s in slot_pool]
        k = min(rng.randint(2, 4), len(candidates))
        for s in rng.sample(candidates, k=k):
            choice = rng.choice(["add", "modify", "delete"])
            if choice == "add" and init.get(s) is None:
                final[s] = _gen_value(s, slot_pool[s], rng)
                ops.append({"op": "ADD", "slot": s, "value": final[s]})
            elif choice == "modify" and init.get(s) is not None:
                old = init[s]
                final[s] = _gen_value(s, slot_pool[s], rng)
                ops.append({"op": "MODIFY", "slot": s, "old_value": old, "new_value": final[s]})
            elif choice == "delete" and init.get(s) is not None:
                final[s] = None
                ops.append({"op": "DELETE", "slot": s})
            else:
                ops.append({"op": "KEEP", "slot": s})
        # Add KEEP for everything else
        for s in init:
            if s not in {o.get("slot") for o in ops}:
                ops.append({"op": "KEEP", "slot": s})

    elif scenario == "single_add":
        null_slots = [x for x in action.get("required_params", []) + action.get("optional_params", []) if x in slot_pool and init.get(x) is None]
        if null_slots:
            s = rng.choice(null_slots)
        else:
            # Pick a random slot not currently in init
            extras = [x for x in slot_pool if x not in init]
            s = rng.choice(extras) if extras else rng.choice(list(slot_pool.keys()))
        final[s] = _gen_value(s, slot_pool[s], rng)
        ops.append({"op": "ADD", "slot": s, "value": final[s]})
        for x in init:
            if x != s:
                ops.append({"op": "KEEP", "slot": x})

    elif scenario == "single_modify":
        candidates = [x for x in action.get("required_params", []) + action.get("side_effects", []) if x in slot_pool and init.get(x) is not None]
        if not candidates:
            candidates = [x for x in init if x in slot_pool]
        s = rng.choice(candidates)
        old = init[s]
        final[s] = _gen_value(s, slot_pool[s], rng)
        ops.append({"op": "MODIFY", "slot": s, "old_value": old, "new_value": final[s]})
        for x in init:
            if x != s:
                ops.append({"op": "KEEP", "slot": x})

    elif scenario == "single_delete":
        candidates = [x for x in action.get("optional_params", []) + action.get("side_effects", []) if x in init]
        if not candidates:
            candidates = list(init.keys())
        s = rng.choice(candidates)
        final[s] = None
        ops.append({"op": "DELETE", "slot": s})
        for x in init:
            if x != s:
                ops.append({"op": "KEEP", "slot": x})

    elif scenario == "no_action_abstention":
        # No state change; everything KEEP
        for x in init:
            ops.append({"op": "KEEP", "slot": x})

    elif scenario == "fraud_report":
        # Cascade the fraud_info group (3 slots)
        members = group_pool.get("fraud_info", [])
        if all(m in slot_pool for m in members):
            for s in members:
                final[s] = _gen_value(s, slot_pool[s], rng)
            ops.append({"op": "CASCADE", "group": "fraud_info", "slots": members, "cause": "report_fraud initializes fraud_info group"})
            for s in members:
                old = init.get(s)
                new = final[s]
                if old is None:
                    ops.append({"op": "ADD", "slot": s, "value": new})
                elif old != new:
                    ops.append({"op": "MODIFY", "slot": s, "old_value": old, "new_value": new})
        for x in init:
            if x not in members:
                ops.append({"op": "KEEP", "slot": x})

    elif scenario == "device_activation":
        members = group_pool.get("device_info", []) + group_pool.get("service_info", [])
        members = [m for m in members if m in slot_pool]
        for s in members:
            final[s] = _gen_value(s, slot_pool[s], rng)
        if members:
            ops.append({"op": "CASCADE", "group": "device_info", "slots": group_pool["device_info"], "cause": "activate_device populates device_info group"})
            if "service_info" in group_pool:
                ops.append({"op": "CASCADE", "group": "service_info", "slots": group_pool["service_info"], "cause": "activate_device transitions service_info"})
        for s in members:
            old = init.get(s)
            new = final[s]
            if old is None:
                ops.append({"op": "ADD", "slot": s, "value": new})
            elif old != new:
                ops.append({"op": "MODIFY", "slot": s, "old_value": old, "new_value": new})
            else:
                ops.append({"op": "KEEP", "slot": s})
        for x in init:
            if x not in members:
                ops.append({"op": "KEEP", "slot": x})

    else:  # pure_query, target_shift, sop_violation, outage_report, dispute_bill, loan_application
        # Default: NO explicit ops for unchanged slots (consumer derives KEEP).
        # Add 1-3 auxiliary ADD/MODIFY/DELETE ops to keep distribution near targets.
        n_aux = rng.randint(1, 3)
        for _ in range(n_aux):
            choice = rng.choice(["add", "modify", "delete"])
            if choice == "add":
                extras = [x for x in slot_pool if x not in final]
                if not extras:
                    continue
                s = rng.choice(extras)
                final[s] = _gen_value(s, slot_pool[s], rng)
                ops.append({"op": "ADD", "slot": s, "value": final[s]})
            elif choice == "modify":
                candidates = [x for x in init if x in slot_pool and x not in {o.get("slot") for o in ops}]
                if not candidates:
                    continue
                s = rng.choice(candidates)
                old = init[s]
                if rng.random() < 0.7:
                    final[s] = _gen_value(s, slot_pool[s], rng)
                ops.append({"op": "MODIFY", "slot": s, "old_value": old, "new_value": final[s]})
            else:  # delete
                candidates = [x for x in init if x not in {o.get("slot") for o in ops}]
                if not candidates:
                    continue
                s = rng.choice(candidates)
                final[s] = None
                ops.append({"op": "DELETE", "slot": s})

    return final, ops


# -------- main batch loop --------


def _build_prompt(domain: str, complexity: str, scenario: str, idx: int, seed_count: int) -> str:
    """Prompt for real LLMs. MockClient parses the DOMAIN/COMPLEXITY/SCENARIO/IDX header."""
    return (
        f"Generate a FACT-Bench dialogue template as a JSON object. "
        f"Follow src/templates/schema/template_schema.json exactly. "
        f"DOMAIN: {domain} COMPLEXITY: {complexity} SCENARIO: {scenario} IDX: {idx}\n\n"
        f"Constraints:\n"
        f"- scenario_type MUST be one of: pure_query, single_add, single_modify, single_delete, "
        f"multi_slot_mixed, cascade_plan_change, cascade_autopay_enable, target_shift, "
        f"sop_violation, no_action_abstention, device_activation, outage_report, "
        f"dispute_bill, loan_application, fraud_report.\n"
        f"- agent_action.name MUST exist in {domain}_actions.json.\n"
        f"- All slots referenced MUST exist in {domain}_slots.json.\n"
        f"- CASCADE ops MUST satisfy the three formal criteria (cause non-empty, "
        f"all slots in declared group, group has >=3 slots).\n"
        f"- sop_applicability.rules MUST use rule ids FS-/FM-/TS-/TM-.\n"
        f"- You are generating seed #{idx} of {seed_count} for this batch."
    )


def _generate_one(client, domain: str, complexity: str, scenario: str, idx: int, max_retries: int = 3) -> dict | None:
    """Generate one template; return None if all retries fail."""
    prompt = _build_prompt(domain, complexity, scenario, idx, max_retries)
    last_errors: list[str] = []
    for attempt in range(max_retries):
        try:
            tpl = client.generate_json(prompt, temperature=0.8 + 0.05 * attempt)
        except Exception as e:
            last_errors.append(f"client error: {e}")
            continue
        # Validate
        errs: list[ValidationError] = []
        validate(tpl, errs)
        if not errs:
            return tpl
        last_errors.append("; ".join(str(e) for e in errs))
    return None


def _output_path(domain: str, complexity: str) -> Path:
    return REPO_ROOT / "data" / "templates" / domain / complexity / "batch.jsonl"


def _append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _seed_template_ids(domain: str, complexity: str) -> set[str]:
    """Avoid colliding with seed template IDs."""
    seed_dir = REPO_ROOT / "data" / "templates" / domain / "seed"
    used = set()
    if seed_dir.exists():
        for p in seed_dir.glob("*.json"):
            try:
                used.add(json.load(io.open(p, "r", encoding="utf-8"))["template_id"])
            except Exception:
                pass
    return used


def run_batch(client, dry_run: bool = False, seed_offset: int = 0) -> dict:
    """Generate all templates per BATCH_PLAN. Returns summary stats."""
    used_ids: dict[str, set[str]] = {dom: _seed_template_ids(dom, "seed") for dom in ("finance", "telecom")}
    rng = random.Random(20260717)

    stats: dict = {"generated": 0, "validated": 0, "failed": [], "by_bucket": {}}

    for (domain, complexity), count in BATCH_PLAN.items():
        bucket_key = f"{domain}/{complexity}"
        stats["by_bucket"][bucket_key] = {"requested": count, "ok": 0, "failed": 0}
        scenarios = SCENARIO_POOLS[(domain, complexity)]
        out_path = _output_path(domain, complexity)
        if not dry_run:
            out_path.write_text("", encoding="utf-8")  # truncate

        for i in range(count):
            idx = seed_offset + i + 1
            # Cycle through scenario pool for diversity
            scenario = scenarios[i % len(scenarios)]
            tpl = _generate_one(client, domain, complexity, scenario, idx, max_retries=3)
            if tpl is None:
                stats["failed"].append({"domain": domain, "complexity": complexity, "idx": idx, "scenario": scenario})
                stats["by_bucket"][bucket_key]["failed"] += 1
                continue
            # Ensure unique ID
            tid = tpl["template_id"]
            while tid in used_ids[domain]:
                # append a random suffix if collision
                tid = tid.rsplit("-", 1)[0] + f"-{rng.randint(100, 999)}"
            tpl["template_id"] = tid
            used_ids[domain].add(tid)
            stats["generated"] += 1
            stats["validated"] += 1
            stats["by_bucket"][bucket_key]["ok"] += 1
            if not dry_run:
                _append_jsonl(out_path, tpl)
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="FACT-Bench batch template generator")
    parser.add_argument("--provider", default=None, help="openai|anthropic|mock (default: env FACT_BENCH_LLM_PROVIDER or mock)")
    parser.add_argument("--model", default=None, help="model name for the chosen provider")
    parser.add_argument("--dry-run", action="store_true", help="plan only, no generation")
    parser.add_argument("--seed-offset", type=int, default=100, help="starting template idx (avoid seed collision)")
    args = parser.parse_args()

    client_kwargs = {}
    if args.model:
        client_kwargs["model"] = args.model
    client = get_client(args.provider, **client_kwargs)
    print(f"[batch_generator] provider={client.name} kwargs={client_kwargs}", file=sys.stderr)

    if args.dry_run:
        for (domain, complexity), count in BATCH_PLAN.items():
            print(f"  {domain:8s} {complexity:8s} -> {count:3d} templates", file=sys.stderr)
        print(f"  total: {sum(BATCH_PLAN.values())}", file=sys.stderr)
        return 0

    stats = run_batch(client, dry_run=False, seed_offset=args.seed_offset)
    print(f"[batch_generator] generated={stats['generated']} validated={stats['validated']} failed={len(stats['failed'])}", file=sys.stderr)
    for k, v in stats["by_bucket"].items():
        print(f"  {k}: requested={v['requested']} ok={v['ok']} failed={v['failed']}", file=sys.stderr)
    if stats["failed"]:
        print("[batch_generator] FAILURES (first 5):", file=sys.stderr)
        for f in stats["failed"][:5]:
            print(f"  {f}", file=sys.stderr)
    return 0 if not stats["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())