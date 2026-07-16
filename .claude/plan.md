# FACT-Bench — 12-Week Execution Plan

> **Single-author, no co-authors, no human annotators beyond self-review.**
> **Period**: 2026-07-13 → 2026-10-04 (12 weeks).
> Source: full Chinese plan provided by user; this is a structured summary.

---

## Phase Overview

| Phase | Weeks | Deliverable |
|-------|-------|-------------|
| 1 | W1–W2 | Infrastructure + template design |
| 2 | W3–W4 | Dialogue generation pipeline |
| 3 | W5–W6 | Evaluation framework |
| 4 | W7–W8 | Baseline experiments |
| 5 | W9–W10 | Analysis & RQ experiments |
| 6 | W11–W12 | Paper writing & submission |

---

## Six Milestones (M1–M6)

| ID | End of Week | Pass Criterion |
|----|-------------|----------------|
| M1 | W2 | 300 templates pass all auto-validation |
| M2 | W4 | ~1,200 dialogues pass 3-layer filtering; dataset split complete |
| M3 | W6 | T1–T5 evaluators runnable; error auto-attribution output correct |
| M4 | W8 | 5 baselines × full FACT-Bench evaluation results |
| M5 | W10 | All RQ analyses complete; figures finalized |
| M6 | W12 | arXiv preprint live + code open-sourced |

---

## Phase 1 — Infrastructure & Template Design (W1–W2)

### W1 — Project Scaffold + Domain Ontology (2026-07-13 → 2026-07-19)

#### Day 1 (Mon 7/13) — Project Scaffold  ✅ DONE
- Create GitHub repo
- Initialize directory structure
- Configure Python venv (3.11+) + core deps (openai, anthropic, datasets, evaluate, scipy, pandas, pydantic, rich, pytest)
- API key management (env vars + .env, not committed)
- Output: directory structure, requirements.txt, README.md v0.1

#### Day 2 (Tue 7/14) — Finance Slot Ontology
- Define 22 finance slots with full schema (type, regex, enum, default)
- 8 semantic groups: card_identity, bill_info, autopay_config, credit_config, contact_info, fraud_info, loan_info, customer_profile
- Output: `data/slots/finance_slots.json`, `data/slots/semantic_groups_finance.json`

#### Day 3 (Wed 7/15) — Telecom Slot Ontology
- Define 18 telecom slots with full schema
- 6 semantic groups: plan_spec, addon_config, device_info, contact_info, service_info, billing_info
- Output: `data/slots/telecom_slots.json`, `data/slots/semantic_groups_telecom.json`

#### Day 4 (Thu 7/16) — Action Schema Library
- 15 finance actions: verify_identity, verify_identity_tfa, check_bill, update_due_date, update_contact, adjust_credit_limit, toggle_autopay, report_fraud, dispute_transaction, apply_loan, check_loan_status, request_supervisor_approval, escalate_to_human, inform_customer, confirm_intent
- 15 telecom actions: check_plan, upgrade_plan, check_contract_status, calculate_termination_fee, add_data_addon, remove_addon, add_roaming, remove_roaming, check_upgrade_eligibility, order_device, report_outage, dispute_bill, inform_customer, confirm_intent, escalate_to_human
- Full JSON Schema per action (params, preconditions, side effects)
- Output: `data/actions/finance_actions.json`, `data/actions/telecom_actions.json`

### Implementation Notes (2026-07-16 修订)

原始 plan 列出了 15+15 个动作,实际 JSON 实现时做了以下调整:

**改名动作**(plan 名 → JSON 实现名,8 项):
- finance: `check_bill` → `check_balance`; `update_due_date` → 已合并到 `enable_autopay`/`disable_autopay` 副作用; `update_contact` → `update_contact_info`; `adjust_credit_limit` → 拆为 `request_credit_limit_increase` + `set_temporary_limit`; `toggle_autopay` → 拆为 `enable_autopay` + `disable_autopay`; `apply_loan` → `apply_for_loan`。
- telecom: `check_plan` → `check_data_usage` + `change_plan` 拆分; `upgrade_plan` → `change_plan`; `add_data_addon` → `add_addon`; `remove_addon` 保持; `add_roaming`/`remove_roaming` → 被 `add_addon`/`remove_addon` 泛化覆盖; `check_upgrade_eligibility` → 被 `check_contract_status` 覆盖; `order_device` → `upgrade_device`; `calculate_termination_fee` → 待后续审计补回。

**拆分动作**(plan 1 个,实现拆成 2 个):
- `adjust_credit_limit` (finance) → `request_credit_limit_increase` + `set_temporary_limit`
- `toggle_autopay` (finance) → `enable_autopay` + `disable_autopay`
- `check_plan` (telecom) → `check_data_usage` + `change_plan`

**新增动作**(plan 没有但实现加了,JSON-only 7 项):
- finance: `make_payment`、`check_dispute_status`、`issue_replacement_card`、`report_fraud`(在 plan 中是 `report_fraud` 但 JSON 重新设计为更细的 `report_fraud`+`dispute_transaction`)、`check_loan_status`。
- telecom: `verify_identity`、`update_contact_info`、`suspend_service`、`resume_service`、`activate_device`、`change_billing_cycle`。

**审计后补回动作**(2026-07-16,plan 与实现双向收口):
- finance (新增 4 个):`inform_customer`、`confirm_intent`、`verify_identity_tfa`、`request_supervisor_approval`。
- telecom (新增 4 个):`dispute_bill`、`report_outage`、`inform_customer`、`confirm_intent`。

**SOP 同步**(SOP 数量不变,引用扩展):
- finance simple FS-01 `applies_to_actions` 追加 `verify_identity_tfa`、`request_supervisor_approval`。
- finance medium FM-06 约束扩展:credit-limit increase 必须先经 TFA。
- telecom simple TS-01 `applies_to_actions` 追加 `dispute_bill`。
- telecom medium TM-04 扩展:同时覆盖 `report_lost_device` 与并行的 `report_outage` 场景。

**未实现的 plan 动作**(留给未来审计):
- `calculate_termination_fee`(telecom)— 低频场景,后续按需补回。

最终统计:**finance 19 个, telecom 19 个**(均超过原计划 15 个)。

#### Day 5 (Fri 7/17) — SOP Documents
- Finance simple SOP: 7 rules (FIN-01..07)
- Finance medium SOP: +6 rules (FIN-08..13)
- Telecom simple SOP: 6 rules (TEL-01..06)
- Telecom medium SOP: +6 rules (TEL-07..12)
- Structured JSON per rule: rule_type, trigger_action, condition, required_actions, severity_on_violation
- Output: `data/sop/finance_sop_simple.json`, `finance_sop_medium.json`, `telecom_sop_simple.json`, `telecom_sop_medium.json`

#### Day 6–7 (Sat–Sun 7/18–19) — Template JSON Schema + Validator + 20 Seed Templates
- Define `src/templates/schema/template_schema.json`
- Implement `src/templates/validator.py`: schema, slot ref, action ref, param type, CASCADE constraint, operation enum, semantic group ref
- Write 10 finance seed templates (5 simple + 3 medium + 2 complex)
- Write 10 telecom seed templates (5 simple + 3 medium + 2 complex)
- Cover scenario types: pure query, single-slot ADD/MODIFY/DELETE, multi-slot mixed, CASCADE (telecom plan migration), target shift, SOP violation, NO_ACTION abstention
- All 20 templates pass validation
- **W1 milestone**: scaffold + 2 domain ontologies + 20 seed templates

### W2 — Batch Template Generation (2026-07-20 → 2026-07-26)

#### Day 8–9 — LLM-Assisted Batch Template Generation
- `src/templates/batch_generator.py` using GPT-4o
- Prompt includes: full slot ontology, action schemas, semantic groups, 10 seed templates as few-shot
- Batch: finance simple 75 + telecom simple 75 → medium 47+47 → complex 18+18 = 280 new templates
- Auto-retry up to 3x per failed generation
- Output: 280 LLM-generated templates + generator script

#### Day 10 — Manual Audit (only human-effort step)
- All 36 complex templates: full audit
- 30% medium (~28): random sample audit
- 15% simple (~23): random sample audit
- Total ~87 templates audited
- Verify: state_operations complete, user_intent_seed aligned, agent_action + params correct, CASCADE satisfies 3 criteria, dialogue logic natural
- Adjust LLM prompt if systematic issues found
- Output: 300 validated templates

#### Day 11 — Distribution Check
- `src/templates/distribution_check.py`: operation-type distribution vs target (KEEP 50%, ADD 15%, MODIFY 20%, DELETE 10%, CASCADE 5%)
- Compute KL divergence
- If DELETE/CASCADE under-represented: edit 10–20 templates
- Slot coverage check: each slot ≥5 templates (non-KEEP)
- Action coverage check: each action ≥3 templates as agent_action
- Output: 300 final templates + `templates/STATS.json`

#### Day 12–13 — Dialogue Generation Script
- `src/generation/dialogue_generator.py`: GPT-4o / Claude Sonnet / DeepSeek-V3
- Per template: 5 variants (GPT-4o×2, Claude×2, DeepSeek×1)
- Temperatures: GPT-4o=0.8, Claude=0.9, DeepSeek=1.0
- Concurrency: ≤5 simultaneous API requests
- Exponential backoff retry up to 3x
- `src/generation/filter_structural.py`: completeness, slot mention check (fuzzy regex on evidence), action param check (lightweight LLM verification)
- `src/generation/filter_semantic.py`: GPT-4o-mini intent coverage check
- `src/generation/filter_verifiability.py`: Claude Sonnet reverse-infer state_operations, compare to template truth, run on 20% sample (1 per template × 5 variants)
- Output: dialogue generator + 3 filter scripts + prompt templates

#### Day 14 — Small-Scale Pilot + Adjustment
- Run full pipeline on 20 seed templates (100 dialogues)
- Manual quality check on 100 dialogues
- Adjust: dialogue generation prompt, filter thresholds, generation params
- Estimate API cost for full run
- Output: 100 pilot dialogues + quality report + adjusted prompts + API cost estimate

**W2 milestone**: 300 templates validated + dialogue generation + 3-layer filtering end-to-end runnable + 100 pilot dialogues quality-checked + full-run cost estimate

---

## Phase 2 — Dialogue Generation Pipeline (W3–W4)

### W3 (7/27 → 8/2) — Full Dialogue Generation + Filtering

#### Day 15–17 — Full Generation
- 300 templates × 5 variants = 1500 generation tasks
- Expected: ~85,500 total API calls across Phase 4 if all models evaluated on all tasks; Phase 2 generation only: ~1500 calls
- Estimated time: 48–72 hours (rate-limit aware)
- Monitor success rate; auto-retry failures
- After generation: run layer-1 structural filter (expected ~10–15% rejection)
- Output: 1500 raw dialogues (`data/dialogues/raw/`) + generation log

#### Day 18 — Layer-2 Semantic Filter
- Run GPT-4o-mini semantic filter on layer-1 survivors
- Track per-intent YES/NO ratio; identify systematic omissions
- Output: `data/dialogues/filtered_semantic/` + filter statistics report

#### Day 19–20 — Layer-3 Truth Verifiability + Regeneration
- For each template, sample 1 variant (~300 dialogues) → Claude Sonnet reverse-inference
- Compute consistency rate per template
- <85% consistency → manual review of template + regenerate all 5 variants
- For prior-layer rejects: if same template has ≥2 rejects, check template for systematic issues, regenerate (max 3 attempts)
- Output: verifiability report + revised templates (if any) + final dataset (target ≥1200)

#### Day 21 — Dataset Assembly + Splits + Stats Report
- Convert to HuggingFace `datasets` format
- Per dialogue: dialogue_id, template_id, variant, domain, complexity, turns (user_utterance, agent_response, agent_action), state_trajectory (state_before, state_after, operations), sop_violations
- Split by template (no template leakage across splits):
  - Train: ~170 templates → ~850 variants (optional for v1.0)
  - Dev: ~40 templates → ~200 variants
  - Test: ~90 templates → ~450 variants (≥400)
  - T6 set: 10 templates (5 finance + 5 telecom) → best 1 of 5 variants = 50
- Generate `data/STATS.md`: total dialogues, turns, op annotations; per-domain/complexity distribution; op distribution vs target; turn-length histogram; type-token ratio; slot coverage heatmap; baseline quality metrics (GCS, SDI, OTB, DC)
- Export as JSONL
- Output: 4 JSONL files + STATS.md

**W3–W4 milestone**: ≥1200 dialogues pass all 3-layer filters + truth consistency >85% per template + dataset split complete + baseline quality metrics all met

---

## Phase 3 — Evaluation Framework (W5–W6)

### W5 (8/3 → 8/9) — T1–T3 Evaluators

#### Day 22–23 — Base Evaluator + T1 (SOC)
- `src/evaluation/base_evaluator.py`: unified model interface (OpenAI/Anthropic/DeepSeek), prompt template management, metric computation + serialization
- T1 SOC prompt: classify operation type per slot
- `src/evaluation/t1_soc.py`: batch processing, metrics: per-operation F1, macro F1, TEM, confusion matrix
- Dev-set test + verify metric correctness
- Output: base + T1 evaluator + T1 prompt

#### Day 24 — T2 (SOE) Evaluator
- T2 SOE prompt: predict full updated state S_t given context + S_{t-1}
- `src/evaluation/t2_soe.py`: state generation + comparison, metrics: JGA, SO-F1, Acc_ADD/MODIFY/DELETE/KEEP, CCR
- Operational conditional accuracy: derive ops from generated S_t vs S_{t-1}, compare with truth ops
- Output: T2 evaluator + T2 prompt

#### Day 25 — T3 (SAG) Evaluator
- T3 SAG prompt: select single best action given state + schemas + latest utterance, or "NO_ACTION"
- `src/evaluation/t3_sag.py`: action name exact match, per-parameter precision/recall, AGS composite, abstention rate AR
- Output: T3 evaluator + T3 prompt

#### Day 26–27 — T4–T5 Evaluators
- T4 MAP prompt: generate full action sequence considering preconditions + SOP
- `src/evaluation/t4_map.py`: sequence edit distance SED (Levenshtein on action names), action set F1 (order-agnostic), precondition satisfaction rate PSR, planned length ratio PLR
- T5 SCD prompt: compliance audit + violation identification
- `src/evaluation/t5_scd.py`: compliance classification F1, violation detection recall/precision (VDR/VDP), rule attribution accuracy (RAA), SCS composite
- Output: T4 + T5 evaluators + prompts

#### Day 28 — Error Auto-Attribution + Diagnostic Report
- `src/analysis/state_error_classifier.py`: per-turn truth vs predicted ops → SE1–SE5 labels (per decision tree) + confusion matrix
- `src/analysis/action_error_classifier.py`: per-turn truth vs predicted actions → AE1–AE7 labels + attribution table
- `src/analysis/diagnostic_report.py`: per-model full FACT report: operation confusion heatmap, action error attribution table, per-task radar, top-5 error types, cross-turn error propagation curve
- `src/evaluation/fact_score.py`: composite metric (0.25×SO-F1 + 0.20×AGS + 0.15×(1-SED) + 0.15×SCS + 0.15×TSR + 0.10×TE)
- Output: 4 analysis/evaluation scripts

**W5–W6 milestone**: T1–T5 evaluators runnable + Dev-set test pass + error auto-attribution verified vs hand-labeled (20-sample spot check) + diagnostic report generator works

---

## Phase 4 — Baseline Experiments (W7–W8)

### W7 (8/10 → 8/16) — Pilot + Model Integration

#### Day 29–30 — Unified Model Interface + Prompt Engineering
- `src/evaluation/model_interface.py`: OpenAI (GPT-4o, GPT-4o-mini), Anthropic (Claude Sonnet 4), DeepSeek (DeepSeek-V3), TogetherAI (Qwen-3-70B, Llama-4); unified retry / rate limit / error handling / token usage stats
- Unified system prompt template (domain + slots + actions + SOP)
- Per-model adapter for different API formats and token limits
- `src/evaluation/run_evaluation.py`: single model × single task, checkpoint resume, real-time progress + ETA
- Output: model interface + run_evaluation + 5 adapter configs

#### Day 31–32 — Pilot Experiment
- On Dev set (200 dialogues): run T1–T5 pilot with only GPT-4o + Claude Sonnet (cost-saving)
- Check for ceiling (FACT-Score >0.95) or floor (<0.05) effects
- Check output format compliance (JSON parse success rate)
- Check for systematic operation-type bias
- Adjust: prompt wording, few-shot examples (add 2–3 if unstable), output parser (robust handling)
- Output: pilot results (2 models × 5 tasks × 200 dialogues) + revised prompts + full-run feasibility confirmation

#### Day 33–35 — Full T1–T5 Evaluation
- On Test set (~450 dialogues): 5 baselines × full T1–T5 evaluation
  - GPT-4o, Claude Sonnet 4, DeepSeek-V3, Qwen-3-70B (Together/Aliyun), Llama-4 (Together/Replicate)
- Per-model API call estimates:
  - T1: ~450 dialogues × ~12 avg turns = ~5,400 calls
  - T2: ~5,400 calls; T3: ~5,400 calls; T4: ~450 calls; T5: ~450 calls
  - ~17,100 calls per model; total ~85,500 for 5 models
  - Estimated cost: $1,500–$2,500
- Checkpoint resume, per-model call stats
- Run error auto-attribution + diagnostic report immediately on completion
- Output: 5 models × T1–T5 results (`data/results/`) + 5 error classifications + 5 diagnostic reports + API usage stats

**W7–W8 milestone**: 5 baselines × full T1–T5 results + per-model diagnostic report auto-generated + no systematic ceiling/floor effects

---

## Phase 5 — Analysis & RQ Experiments (W9–W10)

### W9 (8/24 → 8/30) — Error Analysis + RQ Experiments

#### Day 36–37 — Cross-Model Error Profile Analysis
- RQ1.1 (operation discrimination): 5 models macro-F1, per-op F1 bar chart, identify weakest op per model
- RQ1.2 (operation confusion patterns): 5×5 confusion matrix heatmaps per model, Jensen-Shannon divergence between confusion matrices, hierarchical clustering by confusion pattern
- RQ1.3 (cascade awareness): per-model CCR, cascade slot count (3 vs 4 vs 5+) vs CCR
- RQ2.1 (state-action independence): state error rate vs action error rate Pearson correlation, regression: state error → action error causal path
- RQ2.2 (value vs operation decomposition): combine T1 + T2: correct op but wrong value proportion; T1 macro-F1 vs T2 SO-F1 gap distribution (diagnostic gap)
- RQ3.1 (architecture profile): API-LLM vs Open-LLM groups, compare SE/AE profiles
- RQ3.2 (scale effect): Qwen-3-70B vs GPT-4o, which error types scale-reduces, which are "stubborn"

#### Day 38–39 — RQ4.1 Targeted Improvement Experiment
- Pick 1–2 worst-performing models
- Extract top-3 error types + training samples from Train set (50–80 per type, 150–240 total)
- Three conditions:
  - A: General fine-tune / few-shot with random 150–240 dialogues
  - B: Few-shot prompt + explicit error-profile feedback ("you tend to confuse MODIFY with ADD...")
  - C: No feedback (original prompt)
- Evaluate on Dev set, record per-condition cost + improvement magnitude per error type
- Output: RQ4.1 results + efficiency analysis

#### Day 40 — RQ4.2 SOP Complexity Scaling
- For each model: evaluate T5 under simple vs medium SOP
- Plot SCS vs rule count
- Analyze which SOP rule types (MANDATORY_PRECHECK vs CONDITIONAL_ESCALATION vs BRANCHING) degrade fastest
- If data allows: rule nesting depth vs compliance

#### Day 41–42 — T6 Lightweight Validation + Statistical Tests
- `src/evaluation/t6_user_simulator.py`: GPT-4o as simulator, parameterized by goal/behavior/surface layers
- Small T6: 50 dialogues (25 finance + 25 telecom) × 2 models (GPT-4o, Claude Sonnet) × TSR/TE/GSRT + T1–T5 online metrics
- Simulator adversarial validation: train simple classifier (n-gram + TF-IDF + logistic regression), distinguish T6-generated vs Test-set dialogues, report AUC
- Statistical tests: bootstrap (n=10,000, 95% CI) on all model pairs' FACT-Score; McNemar for op-type comparisons
- Correlation analysis: FACT-Score component Pearson/Spearman matrix; verify dimensions are non-redundant

**W9–W10 milestone**: All RQ figures complete + RQ4.1 proves diagnostic value + T6 proof-of-concept + all statistical tests complete

---

## Phase 6 — Paper Writing & Release (W11–W12)

### W11 (9/7 → 9/13) — Paper Writing

#### Day 43–44 — Outline + Sections 1–4
- Title: "FACT-Bench: Fine-grained Action and Conversation State Tracking Benchmark for Task-Oriented Dialogue Agents"
- Outline (6 pages ACL + supplementary):
  1. Introduction (0.8 pages)
  2. Related Work (0.5)
  3. FACT-Bench Framework (1.5): T1–T6, design principles
  4. Error Taxonomies (1.0): SE1–SE5 + AE1–AE7
  5. Data Construction (1.0)
  6. Experiments (1.2)
  7. Discussion & Conclusion (0.5)
- Write §1 (motivation from v1.0 §1.1, three contributions), §2 (related work positioning), §3 (T1–T6 clean defs + 1–2 representative examples), §4 (taxonomy tree + confusion matrix + attribution)

#### Day 45–46 — Sections 5–6 + Figures
- Write §5: template-driven methodology, 3-layer filtering, baseline quality metrics, dataset stats, limitations + mitigations
- Write §6: 6.1 setup, 6.2 main results (FACT-Score + per-task), 6.3 error analysis, 6.4 diagnostic case studies (2–3 detailed), 6.5 ablation RQ4.1, 6.6 SOP scaling RQ4.2, 6.7 T6
- Make 8 figures + 2 tables: fig1 task architecture, fig2 error taxonomy, fig3 confusion matrices, fig4 radar, fig5 error profile, fig6 SOP scaling, fig7 diagnostic gap, fig8 targeted improvement, table1 main results, table2 dataset stats
- Output: paper first draft + all figures

#### Day 47–48 — Section 7 + Supplementary + Internal Review
- Write §7: main findings, synthesis method applicability, known limitations, future work
- Write supplementary: complete T1–T6 examples, full SE1–SE5 + AE1–AE7 definitions, template JSON Schema, generation prompts, all evaluation prompts, full experiment results (all metrics + all model breakdowns), slot ontology + action schemas
- First internal review: per-section logic flow, all numbers supported in figures, references complete, figure quality (resolution, fonts, colors)
- Output: paper second draft + supplementary first draft

#### Day 49 — Code Release Prep
- Clean GitHub repo: remove temp/debug code
- Full README.md: install, usage examples, dataset download links, baseline reproduction steps
- Add `CONTRIBUTING.md`, `LICENSE` (CC-BY-4.0 for data, MIT for code)
- Demo notebook: `notebooks/demo_quickstart.ipynb` (5-min quickstart)
- Evaluation notebook: `notebooks/evaluate_your_model.ipynb`
- Upload dataset to HuggingFace Datasets (`fact-bench/v1.0`) + dataset card
- Verify one-key run: `python -m src.evaluation.run_evaluation --model gpt-4o --tasks t1,t2,t3,t4,t5`
- Tag release v1.0.0

**W11–W12 milestone**: paper complete draft + supplementary + all figures finalized + code repo complete + dataset uploaded

### W12 (9/14 → 9/20) — Final Polish + Submission

#### Day 50–51 — Final Paper Polish
- Page-by-page read-through: cross-references correct, all table numbers match `data/results/`, grammar (Grammarly or similar), ACL format compliance (page count, margins, fonts, citation style), anonymization (if ACL submission)
- Find 1–2 colleagues/friends to read + provide feedback (non-domain experts can spot logic issues)
- Apply final revisions
- Generate paper PDF, check rendering
- Output: paper final PDF + supplementary final PDF

#### Day 52–53 — Submission + arXiv
- Confirm target conference + deadlines:
  - EMNLP 2026: usually Jun–Jul cutoffs (may already be passed)
  - AACL 2026: usually Jul–Aug cutoffs
  - NAACL 2027: usually Oct cutoff
  - ACL 2027: usually Dec cutoff
- Final format adjustment per target conference
- Submit via OpenReview or SoftConf
- Upload arXiv preprint (with author info preserved version, refined abstract, cs.CL/cs.AI categories)
- Output: submission confirmation email + arXiv link

#### Day 54–56 — Buffer + Outreach
- Handle submission process issues
- Write Twitter/X thread (core findings)
- Write blog post (optional, Chinese + English each one, on Zhihu / Medium)
- Prepare slide deck (for future talks)
- Share on relevant communities (ACL mailing list, Reddit r/MachineLearning)
- Output: outreach materials + slide deck

---

## Appendix A — Daily Schedule (Solo)

| Time Block | Activity |
|------------|----------|
| 08:00–10:00 | **Deep work** (code, experiments, data analysis — highest cognitive load) |
| 10:00–10:30 | Break |
| 10:30–12:30 | **Deep work** (continue core tasks) |
| 12:30–14:00 | Lunch |
| 14:00–16:00 | **Medium work** (API monitoring, docs, figures) |
| 16:00–16:30 | Break |
| 16:30–18:00 | **Light work** (code cleanup, issue notes, planning review) |
| 18:00–20:00 | Dinner / break |
| 20:00–21:00 | **Async tasks** (long-running API batch calls — overnight no-supervision) |

Key principles:
- API batch calls run overnight / breaks (don't occupy deep-work time)
- Daily MITs (3 most important tasks) at start of day, ensure completion
- Weekly Sunday evening review + next-week micro-adjustment
- Single-thread — don't context-switch between multiple tasks

---

## Appendix B — API Cost Estimate

| Model | Use Case | Est. Calls | Unit Price (1M tok) | Est. Cost |
|-------|----------|------------|---------------------|-----------|
| GPT-4o | Dialogue gen + baseline eval | ~40K | in $2.50, out $10 | ~$800 |
| GPT-4o-mini | Semantic filter | ~1,500 | in $0.15, out $0.60 | ~$15 |
| Claude Sonnet 4 | Dialogue gen + baseline + truth verify | ~25K | in $3, out $15 | ~$600 |
| DeepSeek-V3 | Dialogue gen + baseline eval | ~15K | in $0.27, out $1.10 | ~$50 |
| Qwen-3-70B (TogetherAI) | Baseline eval | ~5K | ~$0.90/M tok | ~$100 |
| Llama-4 (TogetherAI) | Baseline eval | ~5K | ~$0.90/M tok | ~$100 |
| **Total** | | | | **~$1,665** |

Conservative estimate (upper bound). Real cost depends on prompt/output length and API pricing changes. Budget: **$2,000–$2,500**.

---

## Appendix C — Risk Register

| Risk | Trigger | Mitigation | Owner |
|------|---------|------------|-------|
| API rate limit causes generation/eval delay | W3 actual gen slower than expected | Apply for higher API tier early; use multiple accounts | self |
| Template validation pass rate low (LLM gen quality poor) | W2 pass rate <70% | Improve gen prompt, add few-shot, raise temperature | self |
| <1000 dialogues after 3-layer filtering | W3–W4 filter rate >25% | Lower filter thresholds; increase variants/template (5→7); manual template fixes | self |
| Some baseline API unavailable | W7 integration fails | Substitute similar model (Qwen→Yi-Large, Llama→Command-R+) | self |
| No GPU for targeted-improvement fine-tune | W9 no GPU | Replace fine-tune with error-profile few-shot feedback in prompt (already designed as fallback) | self |
| Paper cannot finish in 2 weeks | W11–W12 progress slips | Write methodology + experimental design in W9–10 in parallel; half-auto figure generation | self |