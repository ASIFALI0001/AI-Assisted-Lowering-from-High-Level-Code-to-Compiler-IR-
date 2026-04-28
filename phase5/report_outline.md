# Phase 5: Final Report Outline

## Title
**LLM-Assisted Compiler Lowering: A Correctness Analysis of AI-Generated LLVM IR**

---

## 1. Introduction

- **Problem Statement:** Compiler lowering — translating high-level constructs into structured IR — is a precision-critical task governed by strict formal rules (SSA form, dominance, type safety). Can LLMs perform this task reliably?
- **Motivation:** LLMs show promise for code generation, but compiler backends have zero tolerance for semantic ambiguity. Understanding LLM failure modes here has implications for AI-assisted compilation, fuzzing, and tooling.
- **Research Questions:**
  1. Can LLMs produce syntactically valid LLVM IR?
  2. Do LLMs preserve control flow structure (basic blocks, branches, loops)?
  3. Do LLMs correctly maintain SSA form, including phi nodes?
  4. Can a validation + repair loop meaningfully improve output quality?

---

## 2. Methodology

### 2.1 Source Language Subset
- Define the 7 constructs studied (see `docs/source_subset.md`)
- Rationale for construct selection (increasing SSA complexity)

### 2.2 Target IR: LLVM IR
- Why LLVM IR? (strict SSA, formal verification tools)
- Key constraints: SSA, phi nodes, terminators, type system (see `docs/ir_spec.md`)

### 2.3 Test Suite
- 7 programs in `phase1/src_programs/`
- Ground truth manually constructed (see `phase1/ground_truth/`)
- Construct mappings documented in `docs/construct_mappings.md`

### 2.4 Prompt Design
- 3 prompt variants (A: minimal, B: rule-injected, C: few-shot)
- 3 runs per construct per variant = 63 total generations
- Raw outputs stored in `phase2/raw_outputs/`

### 2.5 Validation Protocol
- Stage 1: Syntax check (parsing)
- Stage 2: SSA + type analysis
- Stage 3: CFG verification
- Structural comparison via `tools/compare.py`
- Failure logging via `phase3/failure_logs/results.csv`

---

## 3. Results

### 3.1 Overall Correctness Statistics

> Fill in after completing Phase 2 and 3.

| Construct | A: Pass Rate | B: Pass Rate | C: Pass Rate | Overall |
|-----------|-------------|-------------|-------------|---------|
| 01 var_decl | | | | |
| 02 expressions | | | | |
| 03 if_else | | | | |
| 04 while_loop | | | | |
| 05 for_loop | | | | |
| 06 functions | | | | |
| 07 nested_ctrl | | | | |

### 3.2 Failure Mode Distribution

> Use data from `phase3/failure_logs/results.csv` to produce a chart.

| Failure Category | Count | % of Total Failures |
|-----------------|-------|---------------------|
| Syntax / Format Errors | | |
| SSA Violations (re-assignment) | | |
| Missing Phi Nodes | | |
| Wrong Phi Predecessors | | |
| Type Mismatches (i32 vs i1) | | |
| Missing Terminators | | |
| CF Defects (bad branch targets) | | |
| Semantic Drift | | |

### 3.3 Per-Construct Analysis

Reference the analysis files in `phase3/analysis/` for each construct.

Key expected findings to discuss:
- **Construct 1–2 (straight-line):** LLMs likely perform well; syntax and types are straightforward
- **Construct 3 (if/else):** Phi node at merge block is commonly omitted in Variant A
- **Construct 4–5 (loops):** Loop-carried phi nodes are the dominant failure — especially with Variant A
- **Construct 7 (nested):** Two-level phi structure (header + latch) expected to be hardest; lowest pass rate

### 3.4 Effect of Prompt Variant

> Did adding IR rules (Variant B) or few-shot examples (Variant C) improve accuracy?
> Quantify: compare pass rates across A, B, C.

---

## 4. Validator & Repair Architecture

Reference `phase4/architecture.md` for the full design.

### 4.1 Pipeline Design Summary
- 3-stage validation: syntax → SSA/type → CFG
- Targeted diagnostic messages
- LLM repair loop (max 3 cycles)

### 4.2 Expected Improvement from Repair Loop
- Use the hypothesis table from `phase4/architecture.md`
- Discuss which failure categories are auto-repairable vs. require LLM re-generation

### 4.3 Architecture Diagram
> Include the repair loop flowchart from `phase4/architecture.md`

### 4.4 Trade-offs
- Rule-based repair vs. LLM-in-the-loop
- Computational cost per repair cycle
- When to fall back to deterministic compiler passes

---

## 5. Discussion

### 5.1 When LLMs Succeed
- Straight-line code with no control flow
- Simple function definitions with known return types
- Arithmetic expressions when types are explicit

### 5.2 When LLMs Fail Systematically
- SSA phi node insertion at control-flow merge points
- Loop-carried variables (require reasoning about back-edges)
- Nested control flow (multi-level phi node chains)
- Type discipline (i32 vs i1 conflation)

### 5.3 Can AI Meaningfully Assist Compiler Lowering?
**Expected nuanced answer:**
- ✓ Useful as scaffolding for boilerplate code generation
- ✓ Effective for simple straight-line constructs with few/no phi nodes
- ✓ Can recover from errors when given precise diagnostic feedback (repair loop)
- ✗ Not reliable as a standalone lowering engine without strict validation guardrails
- ✗ Fails predictably on SSA-sensitive constructs without reminders or examples
- ✗ Cannot guarantee semantic correctness even when structurally valid

### 5.4 Practical Deployment Considerations
- Hybrid architecture: LLM for scaffolding + deterministic validator for correctness
- Cost/benefit of repair cycles vs. traditional lowering passes
- Use cases where LLM assistance adds value (rapid prototyping, IR fuzzing, educational tooling)

---

## 6. Conclusion & Future Work

### 6.1 Summary of Findings
- Bullet points summarizing quantitative results from Section 3

### 6.2 Limitations of This Study
- Small test suite (7 programs, 3 runs each)
- Single LLM (Claude); results may vary with other models
- No evaluation of semantic correctness (only structural)
- No runtime execution of generated IR to verify compute results

### 6.3 Future Work
- Fine-tuning an LLM specifically on (source, IR) pairs
- IR-specific grammar constraints during decoding (constrained generation)
- Extending to more complex constructs (arrays, structs, recursion)
- Benchmarking against traditional compiler frontends for speed/correctness trade-off
- Integrating with LLVM's `opt -verify` for authoritative validation

---

## Appendices

- **Appendix A:** Full test suite (`phase1/src_programs/`)
- **Appendix B:** Ground truth IR (`phase1/ground_truth/`)
- **Appendix C:** Construct mapping rules (`docs/construct_mappings.md`)
- **Appendix D:** Raw LLM outputs (`phase2/raw_outputs/`)
- **Appendix E:** Full failure log (`phase3/failure_logs/results.csv`)
- **Appendix F:** Prompt templates (`phase2/prompts/prompt_templates.md`)