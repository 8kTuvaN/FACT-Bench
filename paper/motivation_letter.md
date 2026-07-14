# FACT-Bench: Motivation Letter & Claim-Evidence Map

> **Purpose.** This document pins down the five claims of the FACT-Bench paper and the evidence each claim requires. Every ontology choice, baseline decision, and analysis pass must answer: *which claim does this serve?* If the answer is "none," it is out of scope.
>
> **Single-author discipline.** As a solo first-author debut targeting ACL/EMNLP, every claim must be defensible in a 4-paragraph rebuttal. We cannot afford claims we cannot back. This letter is the constitution.

---

## The Five Claims

### Claim 1 — Method (non-negotiable)
**Operation-level diagnosis surfaces failure modes that surface metrics conflate.**

- *Evidence needed*:
  - At least **3 concrete cases** where two agents have identical JGA / F1 but materially different operation-level error profiles (e.g., one omits a DELETE, the other over-ADDs a hallucinated slot).
- *Where delivered*: §5.3 (case-study section) + T1 SOC + T2 SOE evaluation tables.
- *Risk if missing*: Paper becomes "yet another benchmark" — desk-reject territory.

### Claim 2 — Method (non-negotiable)
**CASCADE is a necessary operation class for semantically-coupled multi-slot updates.**

- *Evidence needed*:
  - (a) **Frequency analysis**: ≥ 8% of state updates are CASCADE in our data.
  - (b) **Failure impact**: at least one SOP scenario where treating CASCADE as independent ADD/MODIFY causes a downstream SOP violation.
  - (c) **Annotation agreement**: κ > 0.7 between two annotators on CASCADE labels.
- *Where delivered*: §3.2 (CASCADE formalization) + §5.2 (frequency) + Appendix C (annotation study).
- *Risk if missing*: CASCADE becomes a footnote instead of a contribution.

### Claim 3 — Method (important, supporting)
**The 5×7 unified error taxonomy enables actionable capability diagnosis.**

- *Evidence needed*:
  - (a) Error-matrix heatmap showing **non-uniform distribution** (some cells empty, some dense).
  - (b) ≥ 3 distinct **capability-gap attributions** explaining observed failure patterns.
- *Where delivered*: §5.4 (error matrix) + §5.5 (capability attribution).
- *Risk if missing*: Taxonomy becomes "yet another classification" — defensible but unremarkable.

### Claim 4 — Empirical (non-negotiable)
**Current SOTA LLMs systematically fail on operation discrimination and SOP compliance.**

- *Evidence needed*:
  - (a) FACT-Score ranking across **5+ models**.
  - (b) Per-task ranking showing **consistent weakness in T1 (SOC) and T5 (SCD)** vs. relatively higher performance on T3 (SAG).
  - (c) **Statistical significance**: ≥ 2 tasks where SOTA model underperforms a simple heuristic baseline (p < 0.05).
- *Where delivered*: §6.1 (main results) + §6.2 (per-task analysis) + Appendix D (significance tests).
- *Risk if missing*: No "story" — just a benchmark with no surprising findings.

### Claim 5 — Methodological (important, supporting)
**Template-driven generation produces dialogues statistically indistinguishable from human-written ones.**

- *Evidence needed*:
  - (a) **Adversarial validation**: human annotators achieve AUC ≤ 0.65 distinguishing our dialogues from a held-out set of real customer-service dialogues.
  - (b) **Linguistic diversity**: type-token ratio, dialogue length distribution, vocabulary overlap vs. human-written dialogues.
  - (c) **Failure-mode coverage**: our dialogues contain ≥ 80% of the failure modes observed in a small (≥ 100) real-dialogue manual review.
- *Where delivered*: §4 (data construction) + Appendix E (validation study).
- *Risk if missing*: Synthetic-data validity becomes the easy reviewer attack vector.

---

## T6 (IDE) — Special Status

**T6 is a proof-of-concept, NOT a main claim.** Acknowledge this explicitly in §7 (Limitations):

- 50 dialogues × 2 user simulators is insufficient for a strong claim.
- T6 demonstrates **end-to-end pipeline feasibility** — it is feasibility evidence, not a finding.
- If T6 results are weak, the paper still ships on Claims 1–5.
- If T6 results are unexpectedly strong, treat as a bonus finding.

---

## Coverage Requirements Per Claim

| Claim | Minimum Evidence (must have) | Stretch Evidence (if time allows) |
|-------|------------------------------|------------------------------------|
| 1 | 3 JGA-tied but operation-distinct cases | 10+ cases with quantified error-type counts |
| 2 | 8% CASCADE frequency + 1 SOP-impact case | Annotation agreement study + cross-domain frequency comparison |
| 3 | Heatmap + 3 distinct capability gaps | 12 capability gaps with quantified per-baseline scores |
| 4 | 5-model ranking + 2 significance tests | 8-model ranking + per-domain + per-SOP-complexity analysis |
| 5 | AUC ≤ 0.65 + 100-dialogue manual comparison | Linguistic diversity metrics + failure-mode coverage analysis |

---

## Out-of-Scope (do NOT promise in the paper)

The following would be valuable but cannot be supported by 12-week single-author execution. The rebuttal strategy for any reviewer who asks is: *"valuable future work; out of scope for first release."*

- ❌ Multi-domain (≥ 4 domains) generalization claim
- ❌ 10+ baseline comparison
- ❌ Human-in-the-loop agent evaluation at scale
- ❌ Real production dialogue data (privacy constraints)
- ❌ Cross-lingual evaluation
- ❌ Long-horizon (> 20 turns) dialogue evaluation
- ❌ Multi-modal (voice, image) input handling

---

## Rebuttal Pre-empting

| Likely Reviewer Attack | Pre-empting Strategy |
|------------------------|----------------------|
| "Only 2 domains" | First release; cross-domain extension roadmap in §7 + CASCADE frequency reported per domain |
| "Only 5 baselines" | FACT-Score separates baselines more sharply than aggregate metrics (§6.1) — fewer baselines needed for sharper signal |
| "Synthetic data is suspect" | AUC ≤ 0.65 + 100-dialogue manual comparison (§4.3 + Appendix E) |
| "Why not just use JGA?" | Three concrete failure-mode cases (§5.3) where JGA cannot distinguish operation-level differences |
| "T6 is weak" | T6 is proof-of-concept by design; main claims rest on T1–T5 (§7 Limitations) |
| "Solo author — how rigorous?" | Three-layer filtering, adversarial validation, statistical tests all documented in Appendices A–E |
| "What's the comparison to τ-Bench / AgentBoard?" | §2.3 (Related Work) explicitly positions FACT-Bench as **diagnostic** (operation-level), not end-to-end success-rate |
| "CASCADE seems ad-hoc" | Three formal criteria (§3.2) + inter-annotator κ study (Appendix C) |

---

## Decision Filter for Future Work

Before adding any feature, ask:

1. **Which claim does this serve?**
2. If "none," **defer or remove**.
3. If "Claim X," what is the **minimum evidence required**?
4. Does the time budget allow delivering that minimum evidence by W10?

**Examples**:

| Feature | Claim served | Verdict |
|---------|--------------|---------|
| New domain (retail) | Weakly serves 1–5 | Defer to post-submission extension |
| Add ReAct / multi-agent baselines | Directly serves 4 | **MUST add** (if budget allows) |
| Fine-tuned Llama baseline | Weakly serves 4 | Nice-to-have |
| RQ4.3 human study (≥ 10 annotators) | Strongly serves 5 | **High priority** if time allows |
| Add per-capability per-model bar chart | Strongly serves 3 | **MUST add** (low cost, high payoff) |
| Implement T6 with 200 dialogues | Weakly serves (no claim) | **Do not increase beyond 50** — spend the time elsewhere |

---

## Summary

**The paper's main contributions live in Claims 1, 2, and 4.** Claim 3 (taxonomy) and Claim 5 (synthesis validation) are supporting evidence. T6 is demo material.

Every experimental decision in the next 12 weeks must be filterable through this claim map. **If a feature does not serve a claim, it is not built.**

---

## Appendix: Claim-to-Task Mapping

| Claim | T1 SOC | T2 SOE | T3 SAG | T4 MAP | T5 SCD | T6 IDE |
|-------|--------|--------|--------|--------|--------|--------|
| 1 (diagnostic) | ★★★ | ★★★ | — | — | — | — |
| 2 (CASCADE) | ★★★ | ★★★ | — | — | ★ | — |
| 3 (taxonomy) | ★★ | ★★ | ★★ | ★★ | ★★ | — |
| 4 (SOTA fails) | ★★★ | ★★★ | ★★ | ★★ | ★★★ | ★ |
| 5 (synthesis) | ★ | ★ | ★ | ★ | ★ | ★ |

★ = supporting role, ★★ = significant, ★★★ = central

**Implication**: T1 and T2 carry the heaviest claim load. If at any point we need to cut work, **T1 and T2 evaluators are the last to compromise.**