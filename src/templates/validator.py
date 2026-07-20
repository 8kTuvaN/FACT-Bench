"""FACT-Bench template validator.

Validates a single template against:
  1. JSON-Schema structural check (template_schema.json).
  2. Slot-name resolution: every slot referenced in initial_state, expected_state_after,
     state_operations (ADD/MODIFY/DELETE/KEEP slots + CASCADE.slots) must exist in the
     domain's slots.json.
  3. Action-name resolution + param resolution:
       - agent_action.name must exist in domain actions.json
       - every key in agent_action.params must be declared by the action
       - each declared param must resolve to EITHER a domain slot OR a documented
         meta-field in data/meta_fields/meta_fields.json
       - meta-field usage is scope-checked against used_by_actions
       - type='slot_reference' meta-fields must point to a real domain slot
  4. CASCADE formal criteria (all three):
       (a) common_cause: CASCADE.cause is a non-empty string.
       (b) semantic_integrality: len(CASCADE.slots) >= 3 AND all slots belong to the
           declared group per semantic_groups_<domain>.json.
       (c) non_decomposability: group is CASCADE-eligible (>= 3 slots in group).
  4b. CASCADE op-coverage: every slot listed in a CASCADE must also have its own
       per-slot ADD/MODIFY/DELETE/KEEP op in state_operations (added 2026-07-17 P0 fix).
  5. Operation enum: state_operations[*].op must be one of ADD/MODIFY/DELETE/KEEP/CASCADE.
  6. Semantic-group ref: state_operations CASCADE.group must exist in
     semantic_groups_<domain>.json.
  7. SOP rule ref: every rule id in sop_applicability.rules must exist in either
     simple or medium SOP files for the domain.
  8. State consistency: for each slot in expected_state_after vs initial_state, the
     operations list must be coherent (KEEP if value unchanged; ADD/MODIFY if changed; etc.).

Usage:
    python -m src.templates.validator data/templates/finance/seed/FIN-*.json
    python -m src.templates.validator --all   # validates every *.json under data/templates/

Exit code 0 if all valid; non-zero (with stderr summary) otherwise.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # we will fall back to a hand-rolled structural check

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
SOP_FILES = {
    "finance": [
        REPO_ROOT / "data" / "sop" / "finance_sop_simple.json",
        REPO_ROOT / "data" / "sop" / "finance_sop_medium.json",
    ],
    "telecom": [
        REPO_ROOT / "data" / "sop" / "telecom_sop_simple.json",
        REPO_ROOT / "data" / "sop" / "telecom_sop_medium.json",
    ],
}
SCHEMA_PATH = REPO_ROOT / "src" / "templates" / "schema" / "template_schema.json"
META_FIELDS_PATH = REPO_ROOT / "data" / "meta_fields" / "meta_fields.json"

ALLOWED_OPS = {"ADD", "MODIFY", "DELETE", "KEEP", "CASCADE"}


class ValidationError:
    def __init__(self, template_id: str, rule: str, message: str):
        self.template_id = template_id
        self.rule = rule
        self.message = message

    def __str__(self) -> str:
        return f"[{self.template_id}] {self.rule}: {self.message}"


def _load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_slot_index() -> dict[tuple[str, str], dict[str, Any]]:
    """Returns {(domain, slot_name): {'semantic_group': ...}}.

    Indexed by (domain, slot_name) because some slot names are shared across
    domains (phone, email, address, dispute_status) — checking by name alone
    would produce false cross-domain ownership violations.
    """
    idx: dict[tuple[str, str], dict[str, Any]] = {}
    for domain, path in SLOTS_FILES.items():
        d = _load_json(path)
        for name, slot in d["slots"].items():
            idx[(domain, name)] = {"semantic_group": slot["semantic_group"]}
    return idx


def _build_group_index() -> dict[tuple[str, str], dict[str, Any]]:
    """Returns {(domain, group_name): {'slots': [...]}}."""
    idx: dict[tuple[str, str], dict[str, Any]] = {}
    for domain, path in GROUPS_FILES.items():
        d = _load_json(path)
        for group, members in d["groups"].items():
            idx[(domain, group)] = {"slots": list(members)}
    return idx


def _build_action_index() -> dict[tuple[str, str], dict[str, Any]]:
    """Returns {(domain, action_name): action_dict}.

    Indexed by (domain, action_name) because some actions are shared across
    domains (verify_identity, update_contact_info, escalate_to_human).
    """
    idx: dict[tuple[str, str], dict[str, Any]] = {}
    for domain, path in ACTIONS_FILES.items():
        d = _load_json(path)
        for name, action in d["actions"].items():
            idx[(domain, name)] = action
    return idx


def _build_sop_index() -> dict[str, str]:
    """Returns {rule_id: domain}."""
    idx: dict[str, str] = {}
    for domain, paths in SOP_FILES.items():
        for path in paths:
            d = _load_json(path)
            for rule in d.get("rules") or d.get("additional_rules") or []:
                idx[rule["id"]] = domain
    return idx


def _build_meta_field_index() -> dict[str, dict[str, Any]]:
    """Returns {meta_field_name: {category, type, used_by_actions, ...}}.

    Meta-fields (per data/meta_fields/meta_fields.json) are NOT dialogue state
    slots — they are transient action parameters or control signals. An action
    param that is neither a slot nor a documented meta-field is an audit risk
    (silently untracked). Consulted by the action_param check to replace the
    brittle action-name allowlist (2026-07-17 P0 audit follow-up).
    """
    if not META_FIELDS_PATH.exists():
        return {}
    d = _load_json(META_FIELDS_PATH)
    return dict(d.get("meta_fields", {}))


def validate(template: dict[str, Any], errors: list[ValidationError]) -> None:
    """In-place mutator: appends ValidationError entries for any rule violation."""
    tid = template.get("template_id", "<missing>")
    domain = template.get("domain")

    # -- 1. JSON-Schema structural check --
    if jsonschema is not None and SCHEMA_PATH.exists():
        try:
            schema = _load_json(SCHEMA_PATH)
            jsonschema.validate(instance=template, schema=schema)
        except jsonschema.ValidationError as e:
            errors.append(ValidationError(tid, "schema", str(e.message)))
            return  # no point checking further if the structure is broken
    else:
        errors.append(
            ValidationError(
                tid,
                "schema",
                "jsonschema package unavailable or schema missing — skipping structural check",
            )
        )

    if domain not in {"finance", "telecom"}:
        errors.append(ValidationError(tid, "domain", f"invalid domain: {domain}"))
        return

    slot_idx = _build_slot_index()
    group_idx = _build_group_index()
    action_idx = _build_action_index()
    sop_idx = _build_sop_index()
    meta_idx = _build_meta_field_index()

    # -- 2. Slot-name resolution --
    init = template.get("initial_state", {})
    final = template.get("expected_state_after", {})
    for slot in list(init.keys()) + list(final.keys()):
        if (domain, slot) not in slot_idx:
            errors.append(ValidationError(tid, "slot_ref", f"unknown slot '{slot}' for domain {domain}"))

    # -- 3. Action-name resolution + param check --
    agent_action = template.get("agent_action", {})
    action_name = agent_action.get("name")
    if (domain, action_name) not in action_idx:
        errors.append(ValidationError(tid, "action_ref", f"unknown action '{action_name}' for domain {domain}"))
    else:
        action = action_idx[(domain, action_name)]
        allowed_params = set(action["required_params"]) | set(action["optional_params"])
        for k in (agent_action.get("params") or {}).keys():
            if k not in allowed_params:
                errors.append(
                    ValidationError(
                        tid,
                        "action_param",
                        f"param '{k}' not in {action_name}.required_params ∪ .optional_params",
                    )
                )
            else:
                # The param is declared by the action. It must resolve to either:
                #   (a) a domain slot (in slot_idx), OR
                #   (b) a documented meta-field (in meta_idx).
                # If neither, it's an undocumented param — audit risk.
                if (domain, k) in slot_idx:
                    pass  # slot-bound param, fine
                elif k in meta_idx:
                    mf = meta_idx[k]
                    # cross-check: declared used_by_actions must include this action
                    if action_name not in mf.get("used_by_actions", []):
                        errors.append(
                            ValidationError(
                                tid,
                                "meta_field_scope",
                                f"meta-field '{k}' is declared for actions {mf.get('used_by_actions')}, "
                                f"but used here by '{action_name}'",
                            )
                        )
                    # slot_reference type meta-fields must point to a valid slot
                    if mf.get("type") == "slot_reference":
                        ref = (agent_action.get("params") or {}).get(k)
                        if ref is not None and (domain, ref) not in slot_idx:
                            errors.append(
                                ValidationError(
                                    tid,
                                    "meta_field_slot_ref",
                                    f"meta-field '{k}' has slot_reference type, but '{ref}' is not a slot in {domain}",
                                )
                            )
                else:
                    errors.append(
                        ValidationError(
                            tid,
                            "action_param_unbound",
                            f"param '{k}' on action '{action_name}' is neither a domain slot nor a documented meta-field. "
                            f"Add '{k}' to {domain}_slots.json (state) or to data/meta_fields/meta_fields.json (transient).",
                        )
                    )

    # -- 4+6. Operation enum + CASCADE criteria + semantic-group ref --
    cascade_slots: set[str] = set()
    for op_entry in template.get("state_operations", []):
        op = op_entry.get("op")
        if op not in ALLOWED_OPS:
            errors.append(ValidationError(tid, "op_enum", f"invalid op '{op}'"))
            continue
        if op == "CASCADE":
            group = op_entry.get("group")
            slots = op_entry.get("slots") or []
            cause = op_entry.get("cause", "")
            if not cause:
                errors.append(
                    ValidationError(tid, "cascade_cause", "CASCADE.cause must be non-empty (criterion: common cause)")
                )
            if (domain, group) not in group_idx:
                errors.append(ValidationError(tid, "cascade_group", f"unknown group '{group}' for domain {domain}"))
            else:
                # criterion (b): semantic_integrality — all slots in same group
                group_members = set(group_idx[(domain, group)]["slots"])
                for s in slots:
                    if s not in group_members:
                        errors.append(
                            ValidationError(
                                tid,
                                "cascade_integrality",
                                f"CASCADE slot '{s}' not in group '{group}'",
                            )
                        )
                # criterion (c): non_decomposability — group must be CASCADE-eligible
                if len(group_members) < 3:
                    errors.append(
                        ValidationError(
                            tid,
                            "cascade_eligible",
                            f"group '{group}' has only {len(group_members)} slots — cannot form CASCADE",
                        )
                    )
            # criterion (b) continued: at least 3 slots in the cascade
            if len(slots) < 3:
                errors.append(
                    ValidationError(
                        tid, "cascade_size", f"CASCADE requires >=3 slots, got {len(slots)}"
                    )
                )
            cascade_slots.update(slots)
        else:
            slot = op_entry.get("slot")
            if (domain, slot) not in slot_idx:
                errors.append(ValidationError(tid, "slot_ref", f"op {op} on unknown slot '{slot}' for domain {domain}"))

    # -- 4b. CASCADE op-coverage: every slot listed in a CASCADE entry must have
    #         its own ADD/MODIFY/DELETE/KEEP op in state_operations. Otherwise
    #         dialogue generators (GPT-4o in W2) might leave the slot untouched,
    #         producing logically inconsistent state trajectories.
    ops_on_slots = {
        o.get("slot")
        for o in template.get("state_operations", [])
        if o.get("op") != "CASCADE" and o.get("slot") is not None
    }
    for s in cascade_slots:
        if s not in ops_on_slots:
            errors.append(
                ValidationError(
                    tid,
                    "cascade_op_coverage",
                    f"CASCADE slot '{s}' has no individual op entry (CASCADE alone is not enough — declare the per-slot ADD/MODIFY/DELETE/KEEP)",
                )
            )

    # -- 7. SOP rule ref --
    for rid in (template.get("sop_applicability") or {}).get("rules", []):
        if rid not in sop_idx:
            errors.append(ValidationError(tid, "sop_ref", f"unknown SOP rule '{rid}'"))
        elif sop_idx[rid] != domain:
            errors.append(
                ValidationError(
                    tid, "sop_ref", f"SOP rule '{rid}' belongs to {sop_idx[rid]}, not {domain}"
                )
            )

    # -- 8. State consistency (lightweight) --
    for slot, final_val in final.items():
        if (domain, slot) not in slot_idx:
            continue  # already flagged
        init_val = init.get(slot, None)
        op_for_slot = None
        for o in template.get("state_operations", []):
            if o.get("slot") == slot:
                op_for_slot = o
                break
            if o.get("op") == "CASCADE" and slot in (o.get("slots") or []):
                op_for_slot = o
                break
        if init_val == final_val:
            # no change: should be KEEP (or no entry). We don't enforce, just note.
            continue
        if init_val is None and final_val is not None:
            if op_for_slot is None or op_for_slot.get("op") not in {"ADD", "CASCADE"}:
                errors.append(
                    ValidationError(
                        tid,
                        "state_consistency",
                        f"slot '{slot}' went null→value but has no ADD/CASCADE op",
                    )
                )
        elif init_val is not None and final_val is None:
            if op_for_slot is None or op_for_slot.get("op") not in {"DELETE", "CASCADE"}:
                errors.append(
                    ValidationError(
                        tid,
                        "state_consistency",
                        f"slot '{slot}' went value→null but has no DELETE/CASCADE op",
                    )
                )


def main() -> int:
    parser = argparse.ArgumentParser(description="FACT-Bench template validator")
    parser.add_argument("paths", nargs="*", help="Template JSON files (or globs)")
    parser.add_argument("--all", action="store_true", help="Validate every template under data/templates/ (incl. .jsonl batches)")
    args = parser.parse_args()

    if args.all:
        files = sorted(
            f
            for f in (
                set(
                    glob.glob(str(REPO_ROOT / "data" / "templates" / "**" / "*.json"), recursive=True)
                    + glob.glob(str(REPO_ROOT / "data" / "templates" / "**" / "*.jsonl"), recursive=True)
                )
            )
            if Path(f).name != "STATS.json"
        )
    else:
        files = []
        for p in args.paths:
            files.extend(glob.glob(p))
        files = sorted(set(files))

    if not files:
        print("[validator] no template files to validate", file=sys.stderr)
        return 1

    all_errors: list[ValidationError] = []
    total = 0
    for f in files:
        path = Path(f)
        if path.suffix == ".jsonl":
            with open(path, "r", encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line:
                        continue
                    total += 1
                    try:
                        tpl = json.loads(line)
                    except Exception as e:
                        all_errors.append(ValidationError(f"{path.name}:L{line_no}", "load", f"could not parse: {e}"))
                        continue
                    validate(tpl, all_errors)
        else:
            total += 1
            try:
                tpl = _load_json(path)
            except Exception as e:
                all_errors.append(ValidationError(f, "load", f"could not parse JSON: {e}"))
                continue
            validate(tpl, all_errors)

    if all_errors:
        print(f"[validator] FAILED — {len(all_errors)} error(s) across {total} template(s) in {len(files)} file(s):", file=sys.stderr)
        for e in all_errors[:50]:
            print(f"  {e}", file=sys.stderr)
        if len(all_errors) > 50:
            print(f"  ... ({len(all_errors) - 50} more)", file=sys.stderr)
        return 1

    print(f"[validator] OK — {total} template(s) passed all checks ({len(files)} file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())