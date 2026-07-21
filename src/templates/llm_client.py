"""Pluggable LLM client interface for FACT-Bench template generation.

Defines a small LLMClient protocol and three implementations:
  - MockClient: deterministic, schema-valid synthetic templates. No API needed.
    Used for Day 8-9 batch generation when no API key is configured, and as
    a reproducible offline test fixture.
  - OpenAIClient: thin wrapper around the openai SDK (>=1.55.0). Activated
    by setting FACT_BENCH_LLM_PROVIDER=openai and providing OPENAI_API_KEY.
  - AnthropicClient: thin wrapper around the anthropic SDK. Activated by
    FACT_BENCH_LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY.

The MockClient is the default for offline runs. The real clients are wired
but inactive by default — they will raise a clear error if invoked without
the relevant API key in env.

Usage:
    from src.templates.llm_client import get_client
    client = get_client(provider="mock")  # or "openai" / "anthropic"
    raw = client.generate_json(prompt=prompt, system=system, temperature=0.8)
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Protocol

# -------- protocol --------


class LLMClient(Protocol):
    name: str

    def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.8,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        """Call the model and return a parsed JSON object. Implementations
        should retry on transient errors and raise on persistent failure."""


# -------- mock (default, deterministic) --------


class MockClient:
    """Deterministic schema-valid template generator.

    The mock does NOT call any external LLM. It composes templates from the
    ontology (slots, semantic groups, actions) using simple but principled
    rules: pick a scenario type, pick concrete slot values that satisfy the
    slot validation, derive the state_operations from initial→final, ensure
    CASCADE criteria when applicable. Output is reproducible given a seed.

    The mock is intended for two purposes:
      1. Unit-testing batch_generator without API keys.
      2. Generating a baseline corpus (280 templates) when no real LLM is
         available — these templates pass the validator but are not
         linguistically rich; a follow-up run with a real LLM should
         regenerate them for the final benchmark.
    """

    name = "mock"

    def __init__(self, seed: int = 42):
        import random

        self._rng = random.Random(seed)
        # Action usage tracking (per domain) — feeds coverage-aware _pick_action.
        self._action_usage: dict[str, dict[str, int]] = {"finance": {}, "telecom": {}}
        self._scenario_pool: dict[tuple[str, str], list[str]] = {
            ("finance", "simple"): [
                "pure_query", "single_add", "single_modify", "single_delete",
                "loan_application", "fraud_report",
                "identity_verification", "dispute_followup", "loan_followup",
                "replacement", "supervisor_approval",
                "dialogue_inform", "dialogue_confirm",
            ],
            ("telecom", "simple"): [
                "pure_query", "single_add", "single_modify",
                "outage_report", "dispute_bill",
                "identity_verification", "service_suspend", "service_resume",
                "contract_check", "dialogue_inform", "dialogue_confirm",
            ],
            ("finance", "medium"): [
                "cascade_autopay_enable", "multi_slot_mixed", "target_shift",
                "loan_application", "fraud_report",
                "replacement", "dispute_followup", "loan_followup",
                "supervisor_approval", "dialogue_inform", "dialogue_confirm",
            ],
            ("telecom", "medium"): [
                "cascade_plan_change", "cascade_addon_subscribe",
                "device_activation", "multi_slot_mixed",
                "device_upgrade", "service_resume", "service_suspend",
                "contract_check", "dialogue_inform", "dialogue_confirm",
            ],
            ("finance", "complex"): [
                "sop_violation", "no_action_abstention", "target_shift",
                "supervisor_approval", "dialogue_inform", "dialogue_confirm",
            ],
            ("telecom", "complex"): [
                "sop_violation", "no_action_abstention", "device_activation",
                "device_upgrade", "dialogue_inform", "dialogue_confirm",
            ],
        }

    def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.8,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        # Parse the prompt to extract: domain, complexity, scenario_type, batch_idx.
        m = re.search(r"DOMAIN:\s*(\w+)\s+COMPLEXITY:\s*(\w+)\s+SCENARIO:\s*([\w_]+)\s+IDX:\s*(\d+)", prompt)
        if not m:
            raise ValueError("MockClient prompt must contain DOMAIN/COMPLEXITY/SCENARIO/IDX header")
        domain, complexity, scenario, idx = m.group(1), m.group(2), m.group(3), int(m.group(4))
        return self._compose(domain, complexity, scenario, idx)

    def _compose(self, domain: str, complexity: str, scenario: str, idx: int) -> dict[str, Any]:
        from src.templates.batch_generator import _ontology  # local import to avoid cycle
        ont = _ontology()
        slot_pool = ont["slots"][domain]
        group_pool = ont["groups"][domain]
        action_pool = ont["actions"][domain]
        rng = self._rng

        # Pick an action appropriate for the scenario
        action_name = self._pick_action(scenario, domain, action_pool)
        action = action_pool[action_name]

        # Generate initial state with concrete values
        init = self._init_state(domain, slot_pool, rng)

        # Apply the action: mutate state and produce state_operations
        final, ops = self._apply_action(action_name, action, init, slot_pool, group_pool, rng, scenario)

        # Build agent_action.params from action.allowed_params
        params = self._action_params(action_name, action, final, rng)

        # Choose 1-2 SOP rules from applicable list
        sop_rules = self._pick_sop_rules(domain, scenario, action_name)
        sop = {"rules": sop_rules}
        if scenario in {"sop_violation", "no_action_abstention"}:
            sop["violation_intent"] = True

        tid = self._make_tid(domain, scenario, idx)
        user_seed = self._user_intent(scenario, rng)
        # Track action usage for coverage-aware next picks
        self._action_usage[domain][action_name] = self._action_usage[domain].get(action_name, 0) + 1
        return {
            "template_id": tid,
            "domain": domain,
            "complexity": complexity,
            "scenario_type": scenario,
            "initial_state": init,
            "user_intent_seed": user_seed,
            "agent_action": {"name": action_name, "params": params},
            "state_operations": ops,
            "expected_state_after": final,
            "sop_applicability": sop,
        }

    # --- composition helpers ---
    def _pick_action(self, scenario: str, domain: str, action_pool):
        """Coverage-aware action picker.

        Two-stage: (1) check if any action is below COVERAGE_TARGET; if so,
        force-pick the most under-covered valid action for this scenario.
        (2) Otherwise pick from scenario-specific candidates, weighted toward
        less-covered actions to avoid clumping.
        """
        COVERAGE_TARGET = 3
        candidates = {
            "pure_query": ["check_balance" if domain == "finance" else "check_data_usage", "check_data_usage" if domain == "finance" else "check_data_usage"],
            "single_add": ["update_contact_info", "apply_for_loan"],
            "single_modify": ["make_payment" if domain == "finance" else "pay_bill", "change_billing_cycle"],
            "single_delete": ["disable_autopay", "remove_addon"],
            "loan_application": ["apply_for_loan"],
            "fraud_report": ["report_fraud"],
            "dispute_followup": ["dispute_transaction", "check_dispute_status"],
            "loan_followup": ["check_loan_status"],
            "replacement": ["issue_replacement_card"],
            "identity_verification": ["verify_identity", "verify_identity_tfa"],
            "supervisor_approval": ["request_supervisor_approval"],
            "dialogue_inform": ["inform_customer"],
            "dialogue_confirm": ["confirm_intent"],
            "service_resume": ["resume_service"],
            "service_suspend": ["suspend_service"],
            "device_upgrade": ["upgrade_device"],
            "contract_check": ["check_contract_status"],
            "cascade_autopay_enable": ["enable_autopay"],
            "multi_slot_mixed": ["set_temporary_limit", "update_contact_info"],
            "target_shift": ["update_contact_info"],
            "cascade_plan_change": ["change_plan"],
            "cascade_addon_subscribe": ["add_addon"],
            "device_activation": ["activate_device"],
            "outage_report": ["report_outage"],
            "dispute_bill": ["dispute_bill"],
            "sop_violation": ["request_credit_limit_increase", "report_lost_device"],
            "no_action_abstention": ["escalate_to_human"],
        }
        opts = candidates.get(scenario, list(action_pool.keys()))
        valid = [a for a in opts if a in action_pool]
        if not valid:
            valid = list(action_pool.keys())

        # Coverage pressure: if any action in valid has < COVERAGE_TARGET uses,
        # force-pick the most under-covered one.
        usage = self._action_usage[domain]
        under = [a for a in valid if usage.get(a, 0) < COVERAGE_TARGET]
        if under:
            return min(under, key=lambda a: usage.get(a, 0))
        # Otherwise random from valid
        return self._rng.choice(valid)

    def _init_state(self, domain: str, slot_pool: dict, rng) -> dict:
        from src.templates.batch_generator import _make_initial_state
        return _make_initial_state(domain, slot_pool, rng)

    def _apply_action(self, action_name: str, action: dict, init: dict, slot_pool: dict, group_pool: dict, rng, scenario):
        from src.templates.batch_generator import _apply_action_to_state
        return _apply_action_to_state(action_name, action, init, slot_pool, group_pool, rng, scenario)

    def _action_params(self, action_name: str, action: dict, final: dict, rng) -> dict:
        params = {}
        for k in action.get("required_params", []) + action.get("optional_params", []):
            v = final.get(k)
            if v is not None:
                params[k] = v
        return params

    def _pick_sop_rules(self, domain: str, scenario: str, action_name: str) -> list[str]:
        # Minimal sensible SOP coverage; expanded by Day 10 audit if needed.
        rules = ["FS-01" if domain == "finance" else "TS-01"]
        if action_name in {"make_payment", "pay_bill"}:
            rules.append("FS-03" if domain == "finance" else "TS-05")
        if action_name in {"enable_autopay", "add_addon", "change_plan"}:
            rules.append("FM-01" if domain == "finance" else "TM-02" if action_name == "add_addon" else "TM-01")
        if action_name == "activate_device":
            rules.append("TM-03")
        if action_name == "report_lost_device":
            rules.append("TM-04")
        if action_name == "report_fraud":
            rules.append("FM-02")
        if action_name == "apply_for_loan":
            rules.append("FM-04")
        if action_name == "request_credit_limit_increase":
            rules.append("FM-06")
        if action_name == "report_outage":
            rules.append("TM-04")
        return rules

    def _user_intent(self, scenario: str, rng) -> dict:
        # Two distinct text fields: user_goal (intent) and agent_paraphrase
        # (natural-language surface form for dialogue generation).
        goals = {
            "pure_query": "Customer wants to check their current account status.",
            "single_add": "Customer wants to update a personal detail on file.",
            "single_modify": "Customer wants to change a specific account setting.",
            "single_delete": "Customer wants to remove an existing account feature.",
            "loan_application": "Customer wants to apply for a personal loan.",
            "fraud_report": "Customer wants to report an unrecognized charge as fraud.",
            "cascade_autopay_enable": "Customer wants to enable autopay with specific bank and date.",
            "multi_slot_mixed": "Customer wants to update multiple account fields at once.",
            "target_shift": "Customer shifts topic mid-conversation, wants two updates.",
            "cascade_plan_change": "Customer wants to switch to a different plan tier.",
            "cascade_addon_subscribe": "Customer wants to subscribe to a value-added add-on.",
            "device_activation": "Customer wants to activate a new device on their line.",
            "outage_report": "Customer wants to report a service outage in their area.",
            "dispute_bill": "Customer wants to dispute a charge on their bill.",
            "sop_violation": "Customer request triggers an SOP-compliance decision point.",
            "no_action_abstention": "Customer request cannot be safely auto-executed; escalate.",
            "dispute_followup": "Customer follows up on an existing dispute.",
            "loan_followup": "Customer follows up on a pending loan application.",
            "replacement": "Customer wants a replacement card shipped.",
            "identity_verification": "Customer begins the call by verifying identity.",
            "supervisor_approval": "Customer request needs supervisor authority.",
            "dialogue_inform": "Agent delivers information back to the customer.",
            "dialogue_confirm": "Agent asks the customer to clarify an ambiguous intent.",
            "service_resume": "Customer wants to resume a previously suspended line.",
            "service_suspend": "Customer wants to suspend their service.",
            "device_upgrade": "Customer wants to upgrade to a new device.",
            "contract_check": "Customer wants to check their remaining contract term.",
        }
        # Paraphrases are scenario-specific natural-language variants
        paraphrases = {
            "pure_query": "What's my current balance?",
            "single_add": "Can you add this to my account?",
            "single_modify": "I'd like to change a setting.",
            "single_delete": "Please remove that for me.",
            "loan_application": "I want to take out a loan.",
            "fraud_report": "There's a charge I didn't make.",
            "cascade_autopay_enable": "Set up autopay starting next month.",
            "multi_slot_mixed": "I need to update a few things at once.",
            "target_shift": "Oh, and one more thing...",
            "cascade_plan_change": "I'd like to switch plans.",
            "cascade_addon_subscribe": "Add this feature to my line.",
            "device_activation": "Help me activate my new device.",
            "outage_report": "There's an outage in my area.",
            "dispute_bill": "I want to dispute a charge.",
            "sop_violation": "This is a sensitive request.",
            "no_action_abstention": "Can you check on something?",
            "dispute_followup": "Any update on my dispute?",
            "loan_followup": "How's my loan application coming?",
            "replacement": "I need a new card.",
            "identity_verification": "Let me verify who I am first.",
            "supervisor_approval": "This needs to go up the chain.",
            "dialogue_inform": "Just FYI on your account.",
            "dialogue_confirm": "Quick — which option did you mean?",
            "service_resume": "Reactivate my line, please.",
            "service_suspend": "Pause my service temporarily.",
            "device_upgrade": "I'm ready for an upgrade.",
            "contract_check": "How long is left on my contract?",
        }
        g = goals.get(scenario, "Generic customer request.")
        p = paraphrases.get(scenario, "Could you help me with something?")
        return {
            "user_goal": g,
            "agent_paraphrase": p,
            "user_persona": rng.choice(["Direct.", "Polite.", "Impatient.", "Anxious.", "Curious."])
        }

    def _make_tid(self, domain: str, scenario: str, idx: int) -> str:
        # Map scenario to a 3-5 letter code
        code = scenario.upper().replace("_", "")[:5]
        return f"{'FIN' if domain == 'finance' else 'TEL'}-{code}-{idx:03d}"


# -------- openai (real; requires OPENAI_API_KEY) --------


class OpenAIClient:
    name = "openai"

    def __init__(self, model: str = "gpt-4o"):
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "OpenAIClient requires OPENAI_API_KEY in env. "
                "Set it or use --provider mock for offline runs."
            )
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as e:
            raise RuntimeError("openai package not installed; pip install openai>=1.55.0") from e
        self._client = OpenAI()
        self._model = model

    def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.8,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        import json as _json

        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system or "You generate FACT-Bench dialogue templates as JSON."},
                        {"role": "user", "content": prompt},
                    ],
                )
                return _json.loads(resp.choices[0].message.content)
            except Exception as e:  # pragma: no cover - network path
                last_exc = e
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"OpenAIClient failed after {max_retries + 1} attempts: {last_exc}")


# -------- anthropic (real; requires ANTHROPIC_API_KEY) --------


class AnthropicClient:
    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "AnthropicClient requires ANTHROPIC_API_KEY in env. "
                "Set it or use --provider mock for offline runs."
            )
        try:
            from anthropic import Anthropic  # type: ignore
        except ImportError as e:
            raise RuntimeError("anthropic package not installed; pip install anthropic>=0.40.0") from e
        self._client = Anthropic()
        self._model = model

    def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.8,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        import json as _json

        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                msg = self._client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    temperature=temperature,
                    system=system or "You generate FACT-Bench dialogue templates as JSON.",
                    messages=[{"role": "user", "content": prompt}],
                )
                # Extract JSON from first text block
                text = next((b.text for b in msg.content if getattr(b, "type", "") == "text"), "{}")
                # Strip code fences if present
                text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
                return _json.loads(text)
            except Exception as e:  # pragma: no cover - network path
                last_exc = e
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"AnthropicClient failed after {max_retries + 1} attempts: {last_exc}")


# -------- factory --------


def get_client(provider: str | None = None, **kwargs) -> LLMClient:
    """Resolve the LLM client. provider order: explicit arg > FACT_BENCH_LLM_PROVIDER env > 'mock'."""
    p = (provider or os.environ.get("FACT_BENCH_LLM_PROVIDER") or "mock").lower()
    if p == "mock":
        return MockClient(**kwargs)
    if p == "openai":
        return OpenAIClient(**kwargs)
    if p in {"anthropic", "claude"}:
        return AnthropicClient(**kwargs)
    raise ValueError(f"unknown provider: {p}")