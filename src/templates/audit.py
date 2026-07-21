"""FACT-Bench Day 10 — manual-audit sampler + structured finding emitter.

Per plan.md Day 10:
  - 36 complex templates: full audit
  - 30% medium templates (random sample)
  - 15% simple templates (random sample)
  - Total ~87 templates

For each sampled template, run automated + heuristic checks aligned with
audit_checklist.md. The output is a per-template PASS/FAIL/FLAG record plus
a final markdown report at paper/audit_report.md. The report is meant for
human review; this script does NOT modify any data files.

Automated checks (already enforced by validator where applicable):
  A1. Every state_operations slot is present in initial_state OR is
      introduced by a CASCADE/ADD op.
  A2. Every state_operations entry has a slot (or CASCADE.slots) that
      exists in the domain slots.json.
  A3. CASCADE: 3 formal criteria (cause non-empty, slots in declared
      group, group has >=3 slots).
  A4. No "phantom ops" — a CASCADE.slots entry without a corresponding
      per-slot ADD/MODIFY/DELETE/KEEP (cascade_op_coverage).
  A5. agent_action.params all resolve to slot or documented meta-field.
  A6. user_intent_seed.agent_paraphrase != user_goal (no copy-paste).

Heuristic checks (plan.md Day 10 spec — "dialogue logic natural"):
  H1. user_goal and agent_action name are roughly aligned (e.g., goal
      mentions "verify" -> action should be verify_identity; goal
      mentions "payment" -> action should be make_payment/pay_bill).
  H2. user_intent_seed.user_persona is non-empty.
  H3. scenario_type is consistent with agent_action.name (e.g.,
      scenario=fraud_report -> action=report_fraud).
  H4. CASCADE.cause is plausible (mentions action name or scenario).

Usage:
    python -m src.templates.audit              # default: paper/audit_report.md
    python -m src.templates.audit --out PATH  # custom output
    python -m src.templates.audit --seed N    # reproducible sample (default 20260717)
"""
from __future__ import annotations

import argparse
import io
import json
import random
import re
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
GROUPS_FILES = {
    "finance": REPO_ROOT / "data" / "slots" / "semantic_groups_finance.json",
    "telecom": REPO_ROOT / "data" / "slots" / "semantic_groups_telecom.json",
}
ACTIONS_FILES = {
    "finance": REPO_ROOT / "data" / "actions" / "finance_actions.json",
    "telecom": REPO_ROOT / "data" / "actions" / "telecom_actions.json",
}


# ---- corpus ----


def load_corpus() -> dict[str, list[dict[str, Any]]]:
    """Returns {complexity: [{'path': ..., 'template': ...}, ...]}."""
    out: dict[str, list] = {"seed": [], "simple": [], "medium": [], "complex": []}
    for f in sorted(
        list(REPO_ROOT.glob("data/templates/**/*.json")) + list(REPO_ROOT.glob("data/templates/**/*.jsonl"))
    ):
        if f.name == "STATS.json":
            continue
        if f.suffix == ".jsonl":
            for line_no, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                tpl = json.loads(line)
                out[tpl["complexity"]].append({"path": str(f) + f":L{line_no}", "template": tpl})
        else:
            tpl = json.loads(f.read_text(encoding="utf-8"))
            out["seed"].append({"path": str(f), "template": tpl})
    return out


# ---- automated checks ----


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def automated_checks(tpl: dict[str, Any], ont: dict[str, Any]) -> list[str]:
    """Return list of finding strings (empty = clean)."""
    findings: list[str] = []
    domain = tpl.get("domain")
    slots = ont["slots"].get(domain, {})
    groups = ont["groups"].get(domain, {})
    actions = ont["actions"].get(domain, {})
    init = tpl.get("initial_state", {})
    final = tpl.get("expected_state_after", {})

    # A1/A2 — every op refers to a slot in domain slots; final slots are
    # introduced via ops (or already in init)
    init_keys = set(init.keys())
    op_slot_introduced: set[str] = set()
    for op in tpl.get("state_operations", []):
        if op.get("op") == "CASCADE":
            for s in op.get("slots") or []:
                op_slot_introduced.add(s)
        else:
            s = op.get("slot")
            if s:
                if op.get("op") == "ADD":
                    op_slot_introduced.add(s)
    final_keys = set(final.keys())
    orphan_finals = final_keys - init_keys - op_slot_introduced
    for s in sorted(orphan_finals):
        findings.append(f"A1 final_state has slot '{s}' but no ADD/CASCADE op introduced it")

    for op in tpl.get("state_operations", []):
        if op.get("op") == "CASCADE":
            for s in op.get("slots") or []:
                if s not in slots:
                    findings.append(f"A2 CASCADE references unknown slot '{s}'")
        elif op.get("op") in ("ADD", "MODIFY", "DELETE", "KEEP"):
            s = op.get("slot")
            if s and s not in slots:
                findings.append(f"A2 op {op['op']} references unknown slot '{s}'")

    # A3 — CASCADE formal criteria
    for op in tpl.get("state_operations", []):
        if op.get("op") == "CASCADE":
            if not (op.get("cause") or "").strip():
                findings.append("A3 CASCADE.cause is empty (violates common-cause criterion)")
            grp = op.get("group")
            if grp and grp not in groups:
                findings.append(f"A3 CASCADE.group '{grp}' not in semantic_groups_{domain}.json")
            elif grp:
                if len(groups[grp]) < 3:
                    findings.append(
                        f"A3 CASCADE.group '{grp}' has only {len(groups[grp])} slots — non-decomposability fails"
                    )
                for s in op.get("slots") or []:
                    if s not in groups.get(grp, []):
                        findings.append(
                            f"A3 CASCADE slot '{s}' not in group '{grp}' (semantic-integrality fails)"
                        )

    # A4 — cascade_op_coverage (validator also checks this; double-check here)
    cascade_slots: set[str] = set()
    for op in tpl.get("state_operations", []):
        if op.get("op") == "CASCADE":
            cascade_slots.update(op.get("slots") or [])
    non_cascade_slots = {
        o.get("slot") for o in tpl.get("state_operations", []) if o.get("op") != "CASCADE"
    }
    for s in sorted(cascade_slots - non_cascade_slots):
        findings.append(f"A4 CASCADE slot '{s}' has no per-slot op (cascade_op_coverage)")

    # A5 — agent_action params resolve
    aa = tpl.get("agent_action", {})
    action_name = aa.get("name")
    if action_name in actions:
        allowed = set(actions[action_name]["required_params"]) | set(actions[action_name]["optional_params"])
        for k in (aa.get("params") or {}).keys():
            if k not in allowed:
                findings.append(f"A5 action '{action_name}' has undeclared param '{k}'")
    elif action_name is not None:
        findings.append(f"A5 unknown agent_action.name '{action_name}'")

    # A6 — paraphrase != user_goal
    uis = tpl.get("user_intent_seed", {})
    if uis.get("agent_paraphrase") and uis.get("user_goal") and uis["agent_paraphrase"].strip() == uis["user_goal"].strip():
        findings.append("A6 user_intent_seed.agent_paraphrase == user_goal (copy-paste)")
    return findings


# ---- heuristic checks (dialogue logic natural) ----


_ACTION_KEYWORDS = {
    "verify_identity": ["verify", "identity", "authenticate", "confirm who"],
    "verify_identity_tfa": ["verify", "two-factor", "2fa", "tfa", "code"],
    "check_balance": ["check", "balance", "owe", "statement"],
    "make_payment": ["pay", "payment", "balance", "settle"],
    "update_contact_info": ["update", "change", "contact", "address", "phone", "email"],
    "enable_autopay": ["enable", "autopay", "automatic payment"],
    "disable_autopay": ["disable", "autopay", "cancel", "turn off"],
    "request_credit_limit_increase": ["credit limit", "increase limit", "raise limit", "limit increase"],
    "set_temporary_limit": ["temporary", "temp limit", "short-term"],
    "report_fraud": ["fraud", "unrecognized", "didn't make", "didnt make", "stolen"],
    "dispute_transaction": ["dispute", "transaction"],
    "check_dispute_status": ["dispute", "status", "update", "follow"],
    "issue_replacement_card": ["replacement", "new card", "reissue"],
    "apply_for_loan": ["loan", "apply", "borrow"],
    "check_loan_status": ["loan", "status", "update", "follow"],
    "escalate_to_human": ["escalate", "human", "agent", "supervisor"],
    "inform_customer": ["inform", "let you know", "fyi", "notification"],
    "confirm_intent": ["confirm", "which", "clarify", "did you mean"],
    "request_supervisor_approval": ["supervisor", "approval", "manager"],
    "check_data_usage": ["data", "usage", "how much data"],
    "change_plan": ["plan", "switch", "change plan", "upgrade plan", "downgrade"],
    "add_addon": ["add", "subscribe", "roaming", "addon", "add-on"],
    "remove_addon": ["remove", "cancel", "addon", "add-on"],
    "suspend_service": ["suspend", "pause", "stop service"],
    "resume_service": ["resume", "reactivate", "unsuspend", "unpause"],
    "activate_device": ["activate", "device", "new phone", "imei"],
    "report_lost_device": ["lost", "stolen", "device"],
    "upgrade_device": ["upgrade", "new device", "device installment"],
    "pay_bill": ["pay", "bill"],
    "change_billing_cycle": ["billing cycle", "monthly", "quarterly", "annual"],
    "check_contract_status": ["contract", "term", "commitment"],
    "report_outage": ["outage", "no service", "down", "not working"],
    "dispute_bill": ["dispute", "bill", "charge"],
}


def _action_keywords(action_name: str) -> list[str]:
    return _ACTION_KEYWORDS.get(action_name, [])


def heuristic_checks(tpl: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    aa = tpl.get("agent_action", {}).get("name", "")
    uis = tpl.get("user_intent_seed", {})
    goal = (uis.get("user_goal") or "").lower()
    paraphrase = (uis.get("agent_paraphrase") or "").lower()
    persona = uis.get("user_persona", "")
    scenario = tpl.get("scenario_type", "")

    # H1 — goal/paraphrase should mention at least one action keyword
    keywords = _action_keywords(aa)
    if keywords:
        text = goal + " " + paraphrase
        if not any(kw in text for kw in keywords):
            findings.append(
                f"H1 user_goal / agent_paraphrase mention none of {aa}'s expected keywords {keywords}"
            )

    # H2 — user_persona non-empty
    if not persona.strip():
        findings.append("H2 user_intent_seed.user_persona is empty")

    # H3 — scenario_type should align with action
    SCENARIO_ACTION_HINTS = {
        "fraud_report": ["report_fraud", "dispute_transaction", "check_dispute_status"],
        "loan_application": ["apply_for_loan", "check_loan_status"],
        "outage_report": ["report_outage"],
        "dispute_bill": ["dispute_bill"],
        "device_activation": ["activate_device"],
        "cascade_plan_change": ["change_plan"],
        "cascade_autopay_enable": ["enable_autopay"],
        "cascade_addon_subscribe": ["add_addon"],
        "identity_verification": ["verify_identity", "verify_identity_tfa"],
        "replacement": ["issue_replacement_card"],
        "supervisor_approval": ["request_supervisor_approval"],
        "dialogue_inform": ["inform_customer"],
        "dialogue_confirm": ["confirm_intent"],
        "service_resume": ["resume_service"],
        "service_suspend": ["suspend_service"],
        "contract_check": ["check_contract_status"],
        "device_upgrade": ["upgrade_device"],
        "dispute_followup": ["dispute_transaction", "check_dispute_status"],
        "loan_followup": ["check_loan_status"],
    }
    if scenario in SCENARIO_ACTION_HINTS and aa not in SCENARIO_ACTION_HINTS[scenario]:
        findings.append(
            f"H3 scenario_type '{scenario}' usually pairs with {SCENARIO_ACTION_HINTS[scenario]}; got '{aa}'"
        )

    # H4 — CASCADE.cause plausibility
    for op in tpl.get("state_operations", []):
        if op.get("op") == "CASCADE":
            cause = (op.get("cause") or "").lower()
            if aa and aa.replace("_", " ") not in cause and aa not in cause:
                # weak signal: cause should mention action or a related verb
                if not any(tok in cause for tok in aa.split("_")):
                    findings.append(
                        f"H4 CASCADE.cause '{op['cause']}' does not mention action '{aa}'"
                    )

    return findings


# ---- sampling + report ----


def sample_for_audit(
    corpus: dict[str, list[dict[str, Any]]],
    seed: int = 20260717,
) -> dict[str, list[dict[str, Any]]]:
    """Returns {complexity: [sampled items]}. Complex = all, others = 30%/15%."""
    rng = random.Random(seed)
    out: dict[str, list] = {}
    out["complex"] = list(corpus["complex"])  # all 36
    # medium: 30%
    medium_pool = list(corpus["medium"])
    rng.shuffle(medium_pool)
    out["medium"] = sorted(medium_pool[:28], key=lambda x: x["template"]["template_id"])
    # simple: 15% of 150 = 23
    simple_pool = list(corpus["simple"])
    rng.shuffle(simple_pool)
    out["simple"] = sorted(simple_pool[:23], key=lambda x: x["template"]["template_id"])
    return out


def build_ontology() -> dict[str, Any]:
    return {
        "slots": {dom: _load(p)["slots"] for dom, p in SLOTS_FILES.items()},
        "groups": {dom: _load(p)["groups"] for dom, p in GROUPS_FILES.items()},
        "actions": {dom: _load(p)["actions"] for dom, p in ACTIONS_FILES.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FACT-Bench Day 10 manual-audit script")
    parser.add_argument("--out", default=str(REPO_ROOT / "paper" / "audit_report.md"))
    parser.add_argument("--seed", type=int, default=20260717)
    args = parser.parse_args()

    ont = build_ontology()
    corpus = load_corpus()
    sample = sample_for_audit(corpus, seed=args.seed)

    counts = {k: len(v) for k, v in sample.items()}
    total = sum(counts.values())

    by_complexity: dict[str, dict[str, int]] = {
        "complex": {"pass": 0, "flag": 0, "fail": 0, "finding": 0},
        "medium": {"pass": 0, "flag": 0, "fail": 0, "finding": 0},
        "simple": {"pass": 0, "flag": 0, "fail": 0, "finding": 0},
    }
    severity_total: Counter = Counter()
    all_records: list[dict[str, Any]] = []

    for complexity, items in sample.items():
        for item in items:
            tpl = item["template"]
            auto = automated_checks(tpl, ont)
            heur = heuristic_checks(tpl)
            all_findings = auto + heur
            n_auto = len(auto)
            n_heur = len(heur)
            if not all_findings:
                status = "PASS"
            elif n_auto > 0:
                status = "FAIL"  # validator-class violation (shouldn't pass validator but flag)
            else:
                status = "FLAG"  # heuristic only
            by_complexity[complexity][status.lower()] += 1
            by_complexity[complexity]["finding"] += len(all_findings)
            for f in auto:
                severity_total["automated"] += 1
            for f in heur:
                severity_total["heuristic"] += 1
            all_records.append(
                {
                    "template_id": tpl.get("template_id", "<missing>"),
                    "complexity": complexity,
                    "path": item["path"],
                    "domain": tpl.get("domain"),
                    "scenario": tpl.get("scenario_type"),
                    "action": tpl.get("agent_action", {}).get("name"),
                    "status": status,
                    "auto_count": n_auto,
                    "heur_count": n_heur,
                    "findings": all_findings,
                }
            )

    # ---- write report ----
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# FACT-Bench — Day 10 Manual Audit Report")
    lines.append("")
    lines.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_")
    lines.append(f"_Sample seed: `{args.seed}` (reproducible)_")
    lines.append(f"_Validator: `src/templates/validator.py` v1.1.0 (auto-checks 8 rules)_")
    lines.append(f"_Auditor: researcher session (heuristic + automated checks)_")
    lines.append("")
    lines.append("## 1. Scope")
    lines.append("")
    lines.append("| Complexity | Population | Sampled | % |")
    lines.append("|---|---|---|---|")
    pop = {k: len(corpus[k]) for k in ("complex", "medium", "simple")}
    for c in ("complex", "medium", "simple"):
        n = counts[c]
        pct = (n / pop[c] * 100) if pop[c] else 0
        lines.append(f"| {c} | {pop[c]} | {n} | {pct:.0f}% |")
    lines.append(f"| **Total** | **{sum(pop.values())}** | **{total}** | — |")
    lines.append("")
    lines.append("Per plan.md Day 10 spec: 36 complex (100%) + 30% medium + 15% simple = ~87.")
    lines.append("")
    lines.append("## 2. Outcome Summary")
    lines.append("")
    lines.append("| Complexity | PASS | FLAG | FAIL | Findings |")
    lines.append("|---|---|---|---|---|")
    for c in ("complex", "medium", "simple"):
        s = by_complexity[c]
        lines.append(
            f"| {c} | {s['pass']} | {s['flag']} | {s['fail']} | {s['finding']} |"
        )
    s_total = {
        k: sum(by_complexity[c][k] for c in ("complex", "medium", "simple"))
        for k in ("pass", "flag", "fail", "finding")
    }
    lines.append(
        f"| **Total** | **{s_total['pass']}** | **{s_total['flag']}** | **{s_total['fail']}** | **{s_total['finding']}** |"
    )
    lines.append("")
    lines.append(f"**Finding breakdown**: {severity_total['automated']} automated + {severity_total['heuristic']} heuristic.")
    lines.append("")
    lines.append("### Status legend")
    lines.append("- **PASS** — no findings (template fully clean).")
    lines.append("- **FLAG** — only heuristic findings (qualitative concern, no validator violation).")
    lines.append("- **FAIL** — automated finding present (validator-class issue; should have been caught by `src/templates/validator.py`).")
    lines.append("")
    lines.append("## 3. Findings by Template")
    lines.append("")
    for complexity in ("complex", "medium", "simple"):
        lines.append(f"### 3.{['complex','medium','simple'].index(complexity)+1} {complexity.upper()}")
        lines.append("")
        for rec in all_records:
            if rec["complexity"] != complexity:
                continue
            lines.append(
                f"- **{rec['template_id']}** ({rec['domain']}/{rec['scenario']}/{rec['action']}) — "
                f"{rec['status']} (auto={rec['auto_count']}, heur={rec['heur_count']})"
            )
            for f in rec["findings"]:
                lines.append(f"  - {f}")
            if not rec["findings"]:
                lines.append(f"  - _no findings_")
        lines.append("")
    lines.append("## 4. Patterns & Recommendations")
    lines.append("")
    # Aggregate heuristic patterns
    heur_counter: Counter = Counter()
    for rec in all_records:
        for f in rec["findings"]:
            # group by leading H1/H2/H3/H4/A1-6
            key = f.split(" ", 1)[0] if f else ""
            heur_counter[key] += 1
    lines.append("### Finding frequency")
    lines.append("")
    lines.append("| Rule | Count |")
    lines.append("|---|---|")
    for k, v in heur_counter.most_common():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    # Recommendations
    lines.append("### Top recommendations")
    lines.append("")
    if heur_counter.get("H1", 0) > total * 0.2:
        lines.append(
            "- **H1 (user_goal ↔ action keyword mismatch) is frequent** — the mock's user_intent text is too generic. Either (a) regenerate with a real LLM, or (b) tighten `_user_intent` in `MockClient` to pick paraphrases from a per-action pool."
        )
    if heur_counter.get("H3", 0) > 0:
        lines.append(
            "- **H3 (scenario ↔ action mismatch)** is a coverage-picker artifact: when no candidate is under-covered, the picker falls back to scenario-specific candidates, but a few scenario buckets are still missing the right candidates. Tighten the MockClient `candidates` map."
        )
    if heur_counter.get("H4", 0) > total * 0.1:
        lines.append(
            "- **H4 (CASCADE.cause does not mention action)** — the mock generates generic causes like 'enable_autopay rewrites autopay_config group atomically' which always pass, but lack specificity. Lower-priority."
        )
    if not heur_counter:
        lines.append("- No systematic issues detected across the 87-template sample.")
    lines.append("")
    lines.append("## 5. Conclusion")
    lines.append("")
    lines.append(
        f"Of **{total} templates** audited ({counts['complex']} complex + {counts['medium']} medium + {counts['simple']} simple):"
    )
    lines.append(
        f"- **{s_total['pass']} PASS** ({s_total['pass']/total*100:.0f}%) — fully clean."
    )
    lines.append(
        f"- **{s_total['flag']} FLAG** ({s_total['flag']/total*100:.0f}%) — heuristic-only concerns (typically H1 user_goal phrasing)."
    )
    lines.append(
        f"- **{s_total['fail']} FAIL** ({s_total['fail']/total*100:.0f}%) — would have been caught by validator; double-check these."
    )
    lines.append("")
    lines.append(
        "Mock-generated templates are schema-valid and operationally coherent but linguistically thin. "
        "Regenerate with `--provider openai` for a real benchmark-quality corpus."
    )
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[audit] wrote {out_path} — {total} templates, "
          f"PASS={s_total['pass']} FLAG={s_total['flag']} FAIL={s_total['fail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())