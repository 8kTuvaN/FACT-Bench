# FACT-Bench: Fine-grained Action and Conversation State Tracking Benchmark

> **Version**: v1.0  
> **Target Venue**: ACL 2027 / EMNLP 2026

FACT-Bench is the first benchmark that enables **operation-level diagnostics** for dialogue state tracking and **hierarchical evaluation** of action selection in task-oriented dialogue agents.

## Overview

Existing TOD benchmarks can tell you *whether* an agent succeeded, but not *why* it failed. FACT-Bench decomposes state updates into operation types (ADD, MODIFY, DELETE, KEEP, CASCADE) and evaluates actions at three levels (single-step grounding, multi-step planning, SOP compliance), enabling fine-grained error attribution.

### Six Tasks (T1–T6)

| Axis | Task | Description |
|------|------|-------------|
| State | T1: SOC | State Operation Classification |
| State | T2: SOE | State Operation Execution |
| Action | T3: SAG | Single-Step Action Grounding |
| Action | T4: MAP | Multi-Step Action Planning |
| Action | T5: SCD | SOP Compliance Discrimination |
| End-to-End | T6: IDE | Interactive Dialogue Evaluation |

### Error Taxonomies

- **State Errors (SE1–SE5)**: 17 leaf error types covering operation type errors, value errors, omissions, commissions, and temporal errors
- **Action Errors (AE1–AE7)**: 21 leaf error types covering selection, parameter, sequencing, omission, commission, SOP violation, and abstention errors

## Quick Start

### Installation

```bash
git clone https://github.com/your-username/FACT-Bench.git
cd FACT-Bench
pip install -r requirements.txt
```

### Configuration

Copy the environment template and add your API keys:

```bash
cp .env.example .env
# Edit .env with your API keys
```

### Running Evaluation

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
│   └── utils/              # Shared utilities
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

## Domains

- **Finance** (22 slots): credit card services, loan consulting, fraud reporting
- **Telecom** (18 slots): plan changes, device upgrades, outage reporting, billing disputes

## Citation

```bibtex
@misc{fact-bench-2026,
  title={FACT-Bench: Fine-grained Action and Conversation State Tracking Benchmark for Task-Oriented Dialogue Agents},
  author={},
  year={2026},
  eprint={},
  archivePrefix={arXiv},
}
```

## License

- Code: MIT License
- Data: CC-BY-4.0
