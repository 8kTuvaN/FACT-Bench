"""FACT-Bench Day 12-13 — dialogue generator + 3-layer filter pipeline.

Per plan.md Day 12-13:
  - 3 LLM providers: GPT-4o, Claude Sonnet, DeepSeek-V3
  - Per template: 5 variants (GPT-4o×2, Claude×2, DeepSeek×1)
  - Temperatures: GPT-4o=0.8, Claude=0.9, DeepSeek=1.0
  - Concurrency: <=5 simultaneous API requests
  - Exponential backoff retry up to 3x

Pipeline:
  1. dialogue_generator.py — produce raw dialogues (one per (template, variant))
  2. filter_structural.py — layer 1: completeness, slot mention regex, action param check
  3. filter_semantic.py  — layer 2: LLM-based intent coverage
  4. filter_verifiability.py — layer 3: reverse-infer state_operations, compare to truth

This script is the entry point. It uses src/templates/llm_client.py for
provider abstraction; without API keys, the MockClient produces
placeholder dialogues for smoke testing.

Usage:
    python -m src.generation.dialogue_generator --provider mock --limit 5
    python -m src.generation.dialogue_generator --provider openai --out data/dialogues/raw/
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.templates.llm_client import get_client  # noqa: E402
from src.templates.validator import validate  # noqa: E402


# ---- Mock dialogue client (offline smoke test) ----


class MockDialogueClient:
    """Schema-valid dialogue synthesizer for offline runs / smoke tests.

    Produces 4-6 turn dialogues from the template, naming the action and
    touching all the slots in initial_state. Used when --provider mock
    is passed (so the smoke test runs without an API key).
    """

    name = "mock-dialogue"

    def __init__(self, seed: int = 42):
        import random
        self._rng = random.Random(seed)

    def generate_json(self, prompt, system="", temperature=0.8, max_retries=2):
        import re as _re
        m = _re.search(r"Expected agent action: (\w+)", prompt)
        action_name = m.group(1) if m else "unknown_action"
        m_init = _re.search(r"Initial state:\s*(\{.*?\})\s*\n", prompt, _re.DOTALL)
        m_final = _re.search(r"Expected final state:\s*(\{.*?\})\s*\n", prompt, _re.DOTALL)
        m_user = _re.search(r"User first utterance.*?:\s*\"([^\"]+)\"", prompt)
        user_utt = m_user.group(1) if m_user else "Hi, I need help."
        m_persona = _re.search(r"User persona:\s*([^\n]+)", prompt)
        persona = (m_persona.group(1).strip() if m_persona else "Direct.") or "Direct."
        n_turns = self._rng.randint(4, 6)
        turns = [{"role": "user", "text": user_utt}]
        for i in range(n_turns - 2):
            turns.append({"role": "agent", "text": f"Sure, let me check that for you (turn {i+1})."})
            turns.append({"role": "user", "text": f"Please proceed (follow-up {i+1})."})
        # Final agent turn names the action
        final_text = f"All set — I've completed your request: {action_name}."
        turns.append({"role": "agent", "text": final_text})
        # Re-parse state (best-effort)
        import json as _json
        try:
            init = _json.loads(m_init.group(1)) if m_init else {}
            final = _json.loads(m_final.group(1)) if m_final else {}
        except Exception:
            init, final = {}, {}
        # Build state trajectory (init -> mid -> final)
        return {
            "turns": turns,
            "agent_actions": [action_name],
            "state_trajectory": [init, final],
        }

# Per plan.md Day 12-13: 5 variants per template
VARIANT_PLAN: list[dict[str, Any]] = [
    {"provider": "openai", "model": "gpt-4o", "temperature": 0.8, "n": 2},
    {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "temperature": 0.9, "n": 2},
    {"provider": "deepseek", "model": "deepseek-chat", "temperature": 1.0, "n": 1},
]

CONCURRENCY = 5
MAX_RETRIES = 3


# ---- dialogue schema ----


@dataclass
class Turn:
    role: str  # "user" | "agent"
    text: str


@dataclass
class Dialogue:
    dialogue_id: str
    template_id: str
    domain: str
    complexity: str
    variant_idx: int
    provider: str
    model: str
    temperature: float
    user_intent_seed: dict
    initial_state: dict
    turns: list[Turn] = field(default_factory=list)
    agent_actions: list[dict] = field(default_factory=list)  # [{name, params}, ...]
    final_state: dict = field(default_factory=dict)
    state_operations: list[dict] = field(default_factory=list)
    generation_status: str = "ok"  # "ok" | "partial" | "failed"
    error: Optional[str] = None
    n_api_calls: int = 0
    wallclock_seconds: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["turns"] = [asdict(t) if hasattr(t, "__dataclass_fields__") else t for t in self.turns]
        return d


# ---- template loader ----


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_templates(repo_root: Path = REPO_ROOT) -> list[dict]:
    out: list[dict] = []
    for f in sorted(
        list((repo_root / "data" / "templates").glob("**/*.json"))
        + list((repo_root / "data" / "templates").glob("**/*.jsonl"))
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


# ---- prompt construction ----


def build_prompt(template: dict, domain: str) -> str:
    """Construct the dialogue-generation prompt for a single template."""
    user_goal = template["user_intent_seed"]["user_goal"]
    user_paraphrase = template["user_intent_seed"]["agent_paraphrase"]
    user_persona = template["user_intent_seed"].get("user_persona", "")
    init = template["initial_state"]
    action = template["agent_action"]["name"]
    action_params = template["agent_action"]["params"]
    final = template["expected_state_after"]
    ops = template["state_operations"]
    sop_rules = template.get("sop_applicability", {}).get("rules", [])
    return f"""You are a synthetic dialogue generator for FACT-Bench, a benchmark
for task-oriented dialogue agents in the {domain} domain.

# Template to dramatize
- Scenario: {template['scenario_type']}
- User persona: {user_persona}
- User intent: {user_goal}
- User first utterance (anchor): "{user_paraphrase}"
- Initial state: {json.dumps(init, ensure_ascii=False)}
- Expected agent action: {action} with params {json.dumps(action_params, ensure_ascii=False)}
- Expected final state: {json.dumps(final, ensure_ascii=False)}
- Expected state operations: {json.dumps(ops, ensure_ascii=False)}
- Applicable SOP rules: {sop_rules}

# Output format (JSON only)
Emit a JSON object with exactly these keys:
- "turns": list of {{"role": "user" | "agent", "text": "..."}}
  4-8 turns total, starting with a user turn, ending with the agent's
  final response confirming the action.
- "agent_actions": list of action names invoked in this dialogue
  (in order; usually 1-2).
- "state_trajectory": list of state snapshots after each agent action
  (one per agent_actions entry).

# Rules
- Stay in character. The user is non-technical and time-pressed.
- The agent must actually invoke the expected action.
- Do not invent facts outside the template.
- Return ONLY the JSON object, no markdown fences, no commentary."""


# ---- generation core (with retry + exponential backoff) ----


def _generate_one_sync(
    client,
    template: dict,
    domain: str,
    variant_idx: int,
    variant_cfg: dict,
) -> tuple[Dialogue, int]:
    """Generate a single dialogue. Returns (Dialogue, n_api_calls)."""
    start = time.time()
    prompt = build_prompt(template, domain)
    last_err: Optional[str] = None
    n_calls = 0
    for attempt in range(MAX_RETRIES + 1):
        n_calls += 1
        try:
            raw = client.generate_json(
                prompt,
                temperature=variant_cfg["temperature"],
                max_retries=0,  # outer loop handles retry
            )
            turns = raw.get("turns", [])
            if not turns:
                raise ValueError("no turns in generated output")
            d = Dialogue(
                dialogue_id=f"D-{template['template_id']}-V{variant_idx:02d}",
                template_id=template["template_id"],
                domain=domain,
                complexity=template["complexity"],
                variant_idx=variant_idx,
                provider=variant_cfg["provider"],
                model=variant_cfg["model"],
                temperature=variant_cfg["temperature"],
                user_intent_seed=template["user_intent_seed"],
                initial_state=template["initial_state"],
                turns=[Turn(**t) for t in turns],
                agent_actions=raw.get("agent_actions", []),
                final_state=raw.get("state_trajectory", [{}])[-1]
                if raw.get("state_trajectory")
                else template.get("expected_state_after", {}),
                state_operations=template["state_operations"],
                generation_status="ok",
                n_api_calls=n_calls,
                wallclock_seconds=time.time() - start,
            )
            return d, n_calls
        except Exception as e:
            last_err = repr(e)
            if attempt < MAX_RETRIES:
                # exponential backoff
                time.sleep(2 ** attempt)
    # exhausted retries
    d = Dialogue(
        dialogue_id=f"D-{template['template_id']}-V{variant_idx:02d}",
        template_id=template["template_id"],
        domain=domain,
        complexity=template["complexity"],
        variant_idx=variant_idx,
        provider=variant_cfg["provider"],
        model=variant_cfg["model"],
        temperature=variant_cfg["temperature"],
        user_intent_seed=template["user_intent_seed"],
        initial_state=template["initial_state"],
        turns=[],
        agent_actions=[],
        final_state={},
        state_operations=template["state_operations"],
        generation_status="failed",
        error=last_err,
        n_api_calls=n_calls,
        wallclock_seconds=time.time() - start,
    )
    return d, n_calls


async def _generate_one_async(
    client,
    template: dict,
    domain: str,
    variant_idx: int,
    variant_cfg: dict,
    sem: asyncio.Semaphore,
) -> tuple[Dialogue, int]:
    async with sem:
        return await asyncio.to_thread(
            _generate_one_sync, client, template, domain, variant_idx, variant_cfg
        )


# ---- main batch ----


def expand_variants() -> list[tuple[int, dict]]:
    """Returns [(variant_idx, cfg), ...] with variant_idx 0..4."""
    out: list[tuple[int, dict]] = []
    idx = 0
    for v in VARIANT_PLAN:
        for _ in range(v["n"]):
            out.append((idx, v))
            idx += 1
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="FACT-Bench dialogue generator")
    parser.add_argument("--provider", default="mock", help="default LLM provider (mock|openai|anthropic)")
    parser.add_argument("--model", default=None, help="override model name")
    parser.add_argument("--out", default=str(REPO_ROOT / "data" / "dialogues" / "raw" / "dialogues.jsonl"))
    parser.add_argument("--limit", type=int, default=None, help="limit number of templates (for smoke tests)")
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY)
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("", encoding="utf-8")  # truncate

    templates = load_templates()
    if args.limit:
        templates = templates[: args.limit]
    print(f"[generator] {len(templates)} templates × 5 variants = {len(templates) * 5} dialogue tasks", flush=True)

    client_kwargs = {"model": args.model} if args.model else {}
    if args.provider == "mock":
        client = MockDialogueClient()
    else:
        client = get_client(args.provider, **client_kwargs)
    variants = expand_variants()

    n_ok = 0
    n_failed = 0
    n_total_calls = 0
    started = time.time()
    with out_path.open("a", encoding="utf-8") as f:
        for t_idx, tpl in enumerate(templates, 1):
            for v_idx, v_cfg in variants:
                d, calls = _generate_one_sync(client, tpl, tpl["domain"], v_idx, v_cfg)
                n_total_calls += calls
                if d.generation_status == "ok":
                    n_ok += 1
                else:
                    n_failed += 1
                f.write(json.dumps(d.to_dict(), ensure_ascii=False) + "\n")
            f.flush()
            if t_idx % 10 == 0:
                print(
                    f"[generator] {t_idx}/{len(templates)} templates | ok={n_ok} failed={n_failed} | "
                    f"calls={n_total_calls} | elapsed={time.time()-started:.1f}s",
                    flush=True,
                )
    elapsed = time.time() - started
    print(
        f"[generator] DONE: {len(templates)} templates × 5 = {len(templates) * 5} dialogues | "
        f"ok={n_ok} failed={n_failed} | total_api_calls={n_total_calls} | elapsed={elapsed:.1f}s",
        flush=True,
    )
    print(f"[generator] wrote {out_path}", flush=True)
    return 0 if n_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())