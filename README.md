# LLM-Assisted Compiler Lowering: Correctness Analysis

## Project Overview

This project investigates how well Large Language Models (LLMs) can perform **compiler lowering** — translating source-language constructs into structured compiler Intermediate Representations (IR). We evaluate correctness, categorize failures, and propose a validator/repair architecture.

---

## Research Objectives

- **(a)** Measure syntactic correctness of LLM-generated IR
- **(b)** Evaluate control flow preservation (branches, loops, basic blocks)
- **(c)** Analyze data flow and SSA form correctness (phi nodes, single-assignment)
- **(d)** Design a validation + repair loop that improves LLM output

---

## Project Structure

```
llm-compiler-lowering/
├── README.md
├── .vscode/
│   └── settings.json
├── docs/
│   ├── ir_spec.md               # Target IR constraints & rules
│   ├── source_subset.md         # Defined source language subset
│   └── construct_mappings.md    # Manual ground-truth IR translations
├── phase1/
│   ├── src_programs/            # Test programs (.src files, one per construct)
│   ├── ground_truth/            # Hand-written correct IR for each program
│   └── ir_output/               # LLM-generated IR (populated in Phase 2)
├── phase2/
│   ├── prompts/                 # Prompt templates (.txt)
│   └── raw_outputs/             # Raw LLM output logs (JSON)
├── phase3/
│   ├── analysis/                # Per-construct analysis reports
│   └── failure_logs/            # Structured failure records (CSV/JSON)
├── phase4/
│   └── architecture.md          # Validator & repair loop design
├── phase5/
│   └── report_outline.md        # Final report structure
└── tools/
    ├── validate.py              # Syntactic/structural validator scaffold
    └── compare.py               # Ground truth vs LLM output diff tool
```

---

## Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Define scope, source subset, ground truth | 🔄 In Progress |
| 2 | LLM experimentation & prompt design | ⏳ Pending |
| 3 | Correctness analysis & failure taxonomy | ⏳ Pending |
| 4 | Validator & repair architecture | ⏳ Pending |
| 5 | Report & presentation | ⏳ Pending |

---

## Getting Started

1. Read `docs/source_subset.md` to understand the language fragment under study
2. Read `docs/ir_spec.md` for LLVM IR rules and constraints
3. Review `docs/construct_mappings.md` for the ground-truth translations
4. Run programs in `phase1/src_programs/` and compare against `phase1/ground_truth/`

---

## Source Language

A restricted C-like subset. See `docs/source_subset.md`.

## Target IR

LLVM IR (`.ll` format). See `docs/ir_spec.md`.