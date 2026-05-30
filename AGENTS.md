# AGENTS.md — LLM-Compiler-Lowering Project Reference

## What This Project Is

A research project that asks: **Can an LLM (Gemini 2.5 Flash) correctly translate simple C-like code into LLVM IR (compiler intermediate representation)?**  
It's Assignment 15 for a Compiler Design course. The goal is to run the LLM, measure how often it fails, categorize the failure types, and then propose (and partially implement) a repair system.

---

## Tech Stack

- **Language:** Python 3
- **LLM:** Google Gemini 2.5 Flash via `google-genai` SDK
- **API key:** stored in `phase2/.env` as `GEMINI_API_KEY`
- **Target IR:** LLVM IR (`.ll` files)
- **No LLVM toolchain required** — validation is done with a hand-written Python validator

---

## Project Structure

```
LLM-Compiler-Lowering/
├── docs/
│   ├── source_subset.md       # The 7 C-like constructs we study (grammar + types)
│   ├── ir_spec.md             # LLVM IR rules the LLM must follow
│   └── construct_mappings.md  # Manual correct translations (ground truth rules)
├── phase1/
│   ├── src_programs/          # .src source files for 7 constructs
│   ├── ground_truth/          # Hand-written correct .ll files
│   └── ir_output/             # LLM-generated .ll files (63 total: 7x3x3)
├── phase2/
│   ├── run_experiments.py     # Main script — calls Gemini API, saves output, runs validator
│   ├── prompts/               # Prompt template documentation
│   ├── raw_outputs/           # JSON logs of every API call (63 files)
│   └── .env                   # GEMINI_API_KEY (never commit this)
├── phase3/
│   ├── analyze_results.py     # Reads JSON logs, prints stats, writes CSV + report
│   ├── failure_logs/
│   │   ├── results.csv        # Empty template
│   │   └── results_filled.csv # Auto-generated from analyze_results.py
│   └── analysis/
│       └── summary_report.md  # Auto-generated analysis report
├── phase4/
│   └── architecture.md        # Proposed validator + repair loop design doc
├── phase5/
│   └── report_outline.md      # Final report structure (fill in manually)
└── tools/
    ├── validate.py            # 3-stage Python validator (syntax → SSA → CFG)
    └── compare.py             # Diff tool: ground truth vs LLM output
```

---

## The 7 Source Constructs

| # | Name | What it tests |
|---|------|---------------|
| 01 | `var_decl` | Variable declaration, alloca/store/load |
| 02 | `expressions` | Arithmetic + logical ops, type rules |
| 03 | `if_else` | Branch blocks, phi nodes at merge |
| 04 | `while_loop` | Loop header, back-edge, phi for loop vars |
| 05 | `for_loop` | Desugared to while, phi for index |
| 06 | `functions` | define, call, ret, parameter types |
| 07 | `nested_ctrl` | if/else inside while, 2-level phi nodes |

---

## Experiment Design

- **3 prompt variants per construct:**
  - **A** — Minimal: "translate this, produce only IR"
  - **B** — Rule-injected: lists 6 explicit LLVM IR rules
  - **C** — Few-shot: rules + one example if/else program
- **3 runs per variant** → 7 × 3 × 3 = **63 total API calls**
- Each run: saved as `phase2/raw_outputs/<tag>.json` + `phase1/ir_output/<tag>.ll`

---

## Validator (tools/validate.py)

Three sequential stages:

| Stage | What it checks |
|-------|----------------|
| 1 — Syntax | Known opcodes, block labels, every block has a terminator (ret/br) |
| 2 — SSA/Type | Each register defined exactly once; br uses i1 not i32 |
| 3 — CFG | Branch targets exist; no unreachable blocks; no dead-end blocks |

Run manually: `python tools/validate.py phase1/ir_output/03_if_else_A_run1.ll`

---

## Current Results (Phase 3 — already run, BUT results were wrong)

**Critical bug found:** The original validator crashed on Windows with a `UnicodeEncodeError` (the `✓` symbol couldn't encode). This caused ALL 63 runs to show as failed — the 0% pass rate was a validator bug, not actual IR failures.

**Bug fixed** in `tools/validate.py` on 2026-05-13:
- Replaced all `✓`/`✗` Unicode symbols with ASCII `[OK]`/`[FAIL]`
- Added normalization to strip `nsw`, `nuw`, `align N` qualifiers (Gemini uses these but our validator didn't handle them)
- Added `validate_ir(ir_text)` function for use by the repair loop
- After fix: `01_var_decl_A_run1.ll` now **passes all 3 stages**

**Action needed:** Re-run `python phase3/analyze_results.py` to get real pass rates.
- Results CSV: `phase3/failure_logs/results_filled.csv`
- Summary report: `phase3/analysis/summary_report.md` (Key Findings still needs fill-in after re-run)

---

## test/ folder (added 2026-05-13)

Interactive demo showing the full pipeline for one program at a time:
- `test/demo.py` — run with `python test/demo.py` from project root
- `test/my_program.src` — edit this to test custom programs
- `test/output/` — saved .ll files from demo runs

The demo does: source → Gemini → validator → ground truth compare → repair loop → final result.

## What Still Needs to Be Done

| Phase | Task | Status |
|-------|------|--------|
| Phase 3 | Re-run `python phase3/analyze_results.py` with fixed validator | Pending |
| Phase 3 | Fill in "Key Findings" in summary_report.md | Pending |
| Phase 4 | Repair loop is **implemented in test/demo.py** — needs formal integration into phase4 | Done (demo) |
| Phase 5 | Write final report using report_outline.md | Pending |
| Phase 5 | Final presentation | Pending |

---

## Key Commands

```bash
# Run all 63 experiments (needs GEMINI_API_KEY in phase2/.env)
python phase2/run_experiments.py

# Analyze results and generate summary
python phase3/analyze_results.py

# Validate a single IR file
python tools/validate.py phase1/ir_output/03_if_else_A_run1.ll

# Compare LLM output vs ground truth
python tools/compare.py phase1/ground_truth/03_if_else.gt.ll phase1/ir_output/03_if_else_A_run1.ll
```

---

## Important Notes

- The 0% pass rate may partly be a validator strictness issue — the SSA checker is failing everything even when Stage 1 passes. Worth investigating before drawing conclusions.
- `phase2/.env` contains the API key — never commit it to git.
- All 63 JSON logs and .ll files already exist — re-running experiments will skip existing files (skip guard in run_experiments.py).
- The report's "Key Findings" section in `phase3/analysis/summary_report.md` needs human analysis to fill in.
