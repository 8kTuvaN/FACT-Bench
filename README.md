# FACT-Bench: An Operation-Level Diagnostic Paradigm for Task-Oriented Dialogue Agents

> **Version**: v1.0 (pre-release, active development)  
> **Target Venue**: ACL 2027 / EMNLP 2027  
> **Status**: Phase 1 of 6 (infrastructure & ontology)

## Why This Work

Existing TOD benchmarks answer *whether* an agent succeeded. They cannot answer *why* it failed.

Two agents with **identical JGA and F1 scores** may have categorically different failure profiles — one forgets to DELETE a stale slot, the other hallucinate-ADDs an unrelated one. Existing metrics cannot distinguish them, so practitioners cannot diagnose which capability to fix. This is the gap **FACT-Bench** targets.

**FACT-Bench introduces an operation-level diagnostic paradigm.** Rather than scoring only final state values, we score the *operation type* the agent should have applied to each slot. We extend the same principle to actions (single-step grounding → multi-step planning → SOP compliance) and unify both error streams into a 5×7 attribution matrix.

## Method: Four Contributions

### 1. State Operation Decomposition

Each dialogue turn is annotated with per-slot operations drawn from {**ADD, MODIFY, DELETE, KEEP, CASCADE**}. The evaluator scores:
- **OTA** (Operation Type Accuracy): did the agent choose the right operation?
- **SO-F1** (State Operation F1): did the agent execute the operation correctly?

### 2. CASCADE: A New Operation Class

When a single user intent causes coupled changes across multiple slots (e.g., *"I lost my card, freeze it and update my contact phone"*), the changes cannot be expressed as independent ADD/MODIFY/DELETE without semantic loss. **CASCADE** formalizes three criteria for this class:

1. **Common cause** — multiple slots change due to one root event
2. **Semantic integrality** — slots form a coherent semantic group
3. **Non-decomposability** — treating as independent operations loses meaning

### 3. Hierarchical Action Evaluation

Actions are scored at three granularities, each isolating a distinct capability:
- **T3 SAG** — Single-Step Action Grounding (intent → next action)
- **T4 MAP** — Multi-Step Action Planning (intent → full action sequence)
- **T5 SCD** — SOP Compliance Discrimination (action ↔ documented rule)

### 4. Unified Error Taxonomy

A 5 (state) × 7 (action) error matrix — **17 leaf state error types** + **21 leaf action error types** — maps observed failures to **12 underlying capability gaps** (e.g., value recall, operation-type discrimination, SOP rule following). Each failure is attributed to one cell in the matrix, enabling systematic diagnosis rather than aggregate accuracy.

## Validation: The FACT-Bench Dataset

To validate the paradigm, we release a 1,500-dialogue benchmark spanning:

| Domain | Slots | Semantic Groups | Scenario Coverage |
|--------|-------|------------------|-------------------|
| Finance | 22 | 8 | credit card services, loan consulting, fraud reporting |
| Telecom | 18 | 6 | plan changes, device upgrades, outage reporting, billing disputes |

Dialogues are generated via **template-driven LLM expansion** with three-layer quality filtering and **adversarial validation** (human annotators cannot reliably distinguish FACT-Bench dialogues from human-written ones; AUC < 0.65).

### Six Tasks (T1–T6)

| Axis | Task | Description |
|------|------|-------------|
| State | T1: SOC | State Operation Classification |
| State | T2: SOE | State Operation Execution |
| Action | T3: SAG | Single-Step Action Grounding |
| Action | T4: MAP | Multi-Step Action Planning |
| Action | T5: SCD | SOP Compliance Discrimination |
| End-to-End | T6: IDE | Interactive Dialogue Evaluation |

## Quick Start

### Installation

```bash
git clone git@github.com:8kTuvaN/FACT-Bench.git
cd FACT-Bench
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
# Edit .env with your API keys
```

### Running Evaluation (planned CLI)

```bash
# Evaluate a single model on all tasks
python -m src.evaluation.run_evaluation \
    --model gpt-4o \
    --tasks t1,t2,t3,t4,t5 \
    --dataset data/dialogues/fact_bench_v1.0_test.jsonl

# Generate diagnostic report
python -m src.analysis.diagnostic_report \
    --results data/results/gpt-4o/ \
    --output data/results/gpt-4o/report.pdf
```

## Project Structure

```
FACT-Bench/
├── src/
│   ├── templates/          # Template design & management
│   ├── generation/         # Dialogue generation pipeline
│   ├── evaluation/         # T1-T6 evaluators
│   ├── analysis/           # Error classification & statistics
│   └── utils/              # Shared utilities (config, I/O, logging)
├── data/
│   ├── slots/              # Slot ontology definitions
│   ├── actions/            # Action schema library
│   ├── sop/                # SOP documents
│   ├── templates/          # Raw template files
│   ├── dialogues/          # Generated dialogue data
│   └── results/            # Evaluation results
├── config/                 # API keys, model configs
├── tests/                  # Unit tests
├── notebooks/              # Analysis notebooks
└── paper/                  # LaTeX source for paper
```

## Roadmap (12-Week Single-Author Plan)

| Phase | Weeks | Deliverable |
|-------|-------|-------------|
| 1 | W1-2 | Infrastructure, slot/action/SOP ontology, templates |
| 2 | W3-4 | Dialogue generation pipeline, 1,500 dialogues |
| 3 | W5-6 | T1-T6 evaluators, FACT-Score metric, calibration |
| 4 | W7-8 | Five-model baseline experiments, error analysis |
| 5 | W9-10 | Cross-model / cross-domain / case-study analysis |
| 6 | W11-12 | Paper draft, reproducibility package, submission |

## Why This Work Will Land

1. **Method > dataset.** The operation-level diagnostic paradigm is the contribution. The benchmark validates it.
2. **CASCADE is new.** No existing TOD benchmark treats semantically-coupled multi-slot changes as a first-class operation class with formal criteria.
3. **Cost-efficient.** Template-driven generation eliminates the manual annotation bottleneck that stalled prior TOD benchmarks.
4. **Reproducible.** Templates, generation seeds, evaluation code, and SOPs are all public.

## Citation

```bibtex
@misc{fact-bench-2026,
  title={FACT-Bench: An Operation-Level Diagnostic Paradigm for Task-Oriented Dialogue Agents},
  author={},
  year={2026},
  eprint={},
  archivePrefix={arXiv},
}
```

## License

- Code: MIT License
- Data: CC-BY-4.0