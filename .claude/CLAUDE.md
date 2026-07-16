# FACT-Bench — AI Assistant Instructions

> **Loaded automatically by Claude Code at session start.**
> This file contains the immutable facts about this project. Do not edit casually.
> Detailed plan lives in `plan.md`; current sprint in `sprint.md`.

---

## Project Identity

| Field | Value |
|-------|-------|
| Name | FACT-Bench |
| Type | First-author debut research artifact (SOLO, no co-authors) |
| Target Venue | ACL 2027 / EMNLP 2027 |
| Start Date | 2026-07-13 (Monday) |
| End Date | 2026-10-04 (Sunday) — 12 weeks |
| Today | See `.claude/sprint.md` "Last Updated" |

---

## Core Concept

**Operation-level diagnostic paradigm** for task-oriented dialogue (TOD) agents.

- Decompose state updates into 5 operation types
- Evaluate actions at three layers (single-step → multi-step → SOP)
- Unified 5×7 error attribution matrix
- T6 (Interactive Dialogue Evaluation) is **proof-of-concept**, NOT a main claim

---

## Immutable Numbers

### Ontology

| Item | Count |
|------|-------|
| Finance slots | 22 (8 semantic groups) |
| Telecom slots | 18 (6 semantic groups) |
| Finance actions | 19 (+4 dialogue-flow actions added 2026-07-16) |
| Telecom actions | 19 (+4 dialogue-flow actions added 2026-07-16) |

> 注:2026-07-16 审计后,action 数量从 15+15 扩展到 19+19,补回了 SOP 引用所需的关键动作(`dispute_bill`、`report_outage`、`inform_customer`、`confirm_intent`、`verify_identity_tfa`、`request_supervisor_approval`)。
| Finance simple SOP rules | 7 |
| Finance medium SOP rules | 13 (7 + 6 additional) |
| Telecom simple SOP rules | 6 |
| Telecom medium SOP rules | 12 (6 + 6 additional) |

### Data

| Item | Count |
|------|-------|
| Seed templates (manually written) | 20 (10 finance + 10 telecom) |
| Total templates (after batch generation) | 300 |
| Dialogue variants per template | 5 |
| Total dialogues | 1500 |
| Pilot test dialogues | 100 (20 templates × 5 variants) |

### Error Taxonomy

| Item | Count |
|------|-------|
| State error categories | 5 (SE1–SE5) |
| State error leaf types | 17 |
| Action error categories | 7 (AE1–AE7) |
| Action error leaf types | 21 |
| Capability gaps (in taxonomy) | 12 |

### Evaluation

| Item | Count |
|------|-------|
| Tasks | 6 (T1–T6) |
| Baseline models | 5 |
| Dialogue splits | Train (optional), Dev, Test, T6 |

---

## The 5 Operation Types

| Code | Name | Definition |
|------|------|------------|
| ADD | Add | Slot was null, now has a value |
| MODIFY | Modify | Slot had a value, value changed |
| DELETE | Delete | Slot had a value, now null |
| KEEP | Keep | Slot value unchanged |
| CASCADE | Cascade | Multiple slots coupled by common cause (≥3 slots, same semantic group, satisfies 3 formal criteria) |

### CASCADE Formal Criteria

A set of slot operations is CASCADE iff ALL THREE hold:

1. **Common cause** — multiple slots change due to one root event
2. **Semantic integrality** — slots form a coherent semantic group
3. **Non-decomposability** — treating as independent operations loses meaning

---

## The Six Tasks (T1–T6)

| ID | Code | Full Name | Primary Claim Load |
|----|------|-----------|---------------------|
| T1 | SOC | State Operation Classification | ★★★ (C1, C2, C4) |
| T2 | SOE | State Operation Execution | ★★★ (C1, C2, C4) |
| T3 | SAG | Single-Step Action Grounding | ★★ (C3, C4) |
| T4 | MAP | Multi-Step Action Planning | ★★ (C3, C4) |
| T5 | SCD | SOP Compliance Discrimination | ★★★ (C4) |
| T6 | IDE | Interactive Dialogue Evaluation | ★ (proof-of-concept) |

**If forced to cut**: cut T6 first, then T3, then T4. **T1, T2, T5 are last to compromise.**

---

## The 5 Claims

See `paper/motivation_letter.md` for full evidence map.

| ID | Type | Priority | Summary |
|----|------|----------|---------|
| C1 | Method | non-negotiable | Operation-level diagnosis surfaces failure modes that surface metrics conflate |
| C2 | Method | non-negotiable | CASCADE is a necessary operation class |
| C3 | Method | important | Unified 5×7 error taxonomy enables actionable capability diagnosis |
| C4 | Empirical | non-negotiable | SOTA LLMs systematically fail on operation discrimination and SOP compliance |
| C5 | Methodological | important | Template-driven synthesis produces dialogues statistically indistinguishable from human-written |

---

## Out-of-Scope (NEVER promise)

The rebuttal strategy for any reviewer asking is: *"valuable future work; out of scope for first release."*

- ❌ Multi-domain (≥4) generalization claim
- ❌ 10+ baseline comparison
- ❌ Human-in-the-loop agent evaluation at scale
- ❌ Real production dialogue data
- ❌ Cross-lingual evaluation
- ❌ Long-horizon (>20 turns) dialogue evaluation
- ❌ Multi-modal (voice, image) input handling

---

## Network & Auth Constraints

| Constraint | Status |
|------------|--------|
| HTTPS to github.com | ❌ BLOCKED by firewall |
| SSH (port 22) to github.com | ✅ Works |
| SSH key | `~/.ssh/id_ed25519` (already added to GitHub) |
| PAT token | ⚠️ User previously leaked in chat — **must revoke** |

---

## Workflow Reminders

1. **At session start**: This file is auto-loaded. Then read `paper/motivation_letter.md` and `.claude/sprint.md`.
2. **Before any decision**: Check which claim it serves. If none, defer.
3. **At commit time**: Use meaningful messages referencing the day's task. Never commit files under `.claude/` or `.env`.
4. **The repo on GitHub is PUBLIC-ONLY content.** Anything AI workflow-related goes in `.claude/` and stays local.

---

## Non-Negotiable Quality Bar

As a solo first-author debut, every claim must be defensible in a 4-paragraph rebuttal. Specifically:

- Every "X happens" claim needs ≥1 statistical test or ≥3 concrete cases
- Every number in the paper must trace to a file in `data/results/`
- Every claim-evidence gap is a desk-reject risk at top venues
- Paper must be reproducible end-to-end from public repo