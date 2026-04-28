# Phase 4: Validator & Repair Architecture

## Overview

This document proposes a **3-stage validation pipeline** followed by an **LLM-in-the-loop repair cycle** to improve the correctness of LLM-generated LLVM IR.

The key insight from Phase 3 is that LLMs fail in **systematic, diagnosable ways** — missing phi nodes, type mismatches, missing terminators — rather than random noise. This makes targeted repair feasible.

---

## Stage 1: Syntax / Parser Check

**Purpose:** Catch formatting and grammatical violations before deeper analysis.

**What it checks:**
- Valid LLVM IR instruction mnemonics (`add`, `icmp`, `br`, `ret`, `phi`, etc.)
- Correct operand count per instruction
- Proper basic block label syntax (`label:`)
- No illegal characters or malformed register names
- Every `define` has matching `{` and `}`

**Implementation approach:**
- Regex-based pre-scan for obvious formatting errors
- Feed the IR into `llvm-as` (LLVM assembler) if available, or a lightweight hand-written parser
- If parsing fails: **stop here**, generate Stage 1 diagnostic, skip Stages 2–3

**Example diagnostic output:**
```
[STAGE 1 ERROR] Line 7: Unknown instruction 'addi'. Did you mean 'add'?
[STAGE 1 ERROR] Line 12: Block 'then' has no terminator instruction.
```

---

## Stage 2: SSA & Type Analyzer

**Purpose:** Verify single-assignment rules, phi node correctness, and type consistency.

**What it checks:**

### SSA Violations
- Build a def-use map: for each `%reg`, record exactly one definition site
- Flag any register defined more than once
- Flag any use of a register before its definition (use-before-def)

### Phi Node Correctness
- For every block with multiple predecessors: check that all live-in values have phi nodes
- For every phi node: verify that the set of named predecessors matches the actual predecessor blocks in the control-flow graph
- Flag phi nodes referencing non-predecessor blocks
- Flag missing phi nodes (value defined in only one branch, used after merge)

### Type Consistency
- For each instruction, verify operand types match expected types:
  - `add`, `sub`, `mul`, `sdiv`: both operands must be `i32`
  - `and`, `or`, `xor`: both operands must be `i1`
  - `icmp`: operands must be same type; result is always `i1`
  - `br i1 ...`: condition must be `i1`, not `i32`
  - `call @f(...)`: argument types must match `@f`'s parameter types

**Implementation approach:**
- Two-pass analysis:
  1. First pass: collect all block labels, build CFG (predecessor/successor sets), collect all register definitions
  2. Second pass: check use-before-def, phi predecessor correctness, type rules
- Use a symbol table: `{ reg_name → (type, defining_block) }`

**Example diagnostic output:**
```
[STAGE 2 ERROR] SSA violation: %i defined in both %entry (line 4) and %loop.body (line 11).
[STAGE 2 ERROR] Missing phi node: %result used in block %merge, but defined only in block %then.
                 Predecessors of %merge: {%then, %else}. Add phi for %result.
[STAGE 2 ERROR] Type mismatch at line 9: 'br' condition is i32 (%cond), expected i1.
                 Use 'icmp' to produce an i1 value.
```

---

## Stage 3: Control Flow Verifier

**Purpose:** Verify structural correctness of the CFG — connectivity, loops, and termination.

**What it checks:**

### Basic Block Connectivity
- Every branch target (`label %X`) refers to a block that actually exists in the function
- No block is unreachable (has no path from the entry block)
- No block has zero predecessors except `entry`

### Loop Structure
- Back-edges are correctly directed (loop body → loop header, not body → body)
- Loop headers have the expected phi nodes for loop-carried variables
- No infinite loops in IR (loop must have an exit edge)

### Dominance
- Every use of `%reg` is dominated by its definition
  - i.e., every path from `entry` to the use passes through the definition
- (Simplified check: for now, flag uses where the defining block is not an ancestor in the CFG)

### Termination Guarantee
- Every block that is not `loop.exit` or `ret`-containing has a clear path to a `ret`
- No "dead end" blocks (block with no successor and no `ret`)

**Example diagnostic output:**
```
[STAGE 3 ERROR] Branch target '%loopexit' in block %loop.body does not exist. 
                Did you mean '%loop.exit'?
[STAGE 3 ERROR] Block %else has no successor and no ret instruction (dead end).
[STAGE 3 WARNING] Block %unreachable has no predecessors — it is unreachable from entry.
```

---

## The Repair Loop

```
┌─────────────────────────────────────────────────────────┐
│                      SOURCE PROGRAM                     │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
                      ┌─────────────┐
                      │  LLM CALL   │  (Prompt Variant B or C)
                      └──────┬──────┘
                             │  generated IR
                             ▼
              ┌──────────────────────────────┐
              │   STAGE 1: Syntax Check      │
              └──────────────┬───────────────┘
                    pass     │     fail
                             │──────────────────────────────┐
                             ▼                              │
              ┌──────────────────────────────┐              │
              │   STAGE 2: SSA + Type Check  │              │
              └──────────────┬───────────────┘              │
                    pass     │     fail                     │
                             │──────────────────┐           │
                             ▼                  │           │
              ┌──────────────────────────────┐  │           │
              │   STAGE 3: CFG Verifier      │  │           │
              └──────────────┬───────────────┘  │           │
                    pass     │     fail          │           │
                             │──────────┐        │           │
                             ▼          │        │           │
                          ACCEPT    COLLECT  COLLECT     COLLECT
                                   DIAGS    DIAGS       DIAGS
                                       │        │           │
                                       └────────┴───────────┘
                                                │
                                                ▼
                                   ┌─────────────────────┐
                                   │  Repair iterations   │
                                   │  (max 3 cycles)      │
                                   │                      │
                                   │  Feed diagnostics    │
                                   │  + original source   │
                                   │  + invalid IR        │
                                   │  → Prompt Variant D  │
                                   └──────────┬──────────┘
                                              │
                                    re-enter validation
                                    (loop back to Stage 1)
```

### Repair Cycle Details

- **Iteration limit:** 3 repair cycles maximum to avoid infinite loops
- **Diagnostic specificity:** Diagnostics must name the exact block, register, and rule violated — vague errors do not help the LLM repair effectively
- **Partial repair tracking:** Record which stages pass after each repair cycle to quantify improvement
- **Fallback:** After 3 failed cycles, mark the output as "unrepairable by LLM" and log for manual analysis

---

## Trade-offs & Design Decisions

| Decision | Rationale |
|----------|-----------|
| Use `alloca`/`store`/`load` strategy over pure SSA phi nodes | Easier for LLMs to produce; fewer phi nodes required. Trade-off: more instructions, less optimal IR. |
| Rule-based Stage 1 & 2 vs. LLM-based repair | Deterministic validation is faster and cheaper. LLM repair is reserved for semantic-level fixes. |
| Max 3 repair cycles | Empirically, if 3 rounds of feedback don't fix structural errors, the issue is likely beyond prompt-level repair. |
| Separate `loop.latch` block | Prevents phi predecessor complexity at `loop.header`; easier for both LLMs and validators to reason about. |

---

## Expected Success Rates (Hypothesis)

| Failure Category | Auto-Fixable (Rule-Based)? | Fixable by LLM after 1 repair? | Notes |
|-----------------|---------------------------|-------------------------------|-------|
| Syntax errors | ✓ Often yes | ✓ Yes | LLM responds well to exact line/error |
| Missing terminator | ✓ Can auto-insert `br` | ✓ Yes | Deterministic fix in most cases |
| Type mismatch (i32 vs i1) | ✓ Auto-insert `icmp ne i32 %x, 0` | ✓ Yes | |
| SSA violation (re-assignment) | ✗ Requires renaming strategy | ~ Partial | LLM sometimes re-introduces violations |
| Missing phi node (if/else) | ✗ Requires dataflow | ✓ Yes with specific diagnostic | |
| Missing phi node (loop) | ✗ Complex loop analysis | ~ Partial | Hardest case; often needs 2–3 rounds |
| Wrong phi predecessors | ✗ Requires CFG | ~ Partial | LLM confuses block names |
| Semantic drift | ✗ Beyond structural repair | ✗ Rarely | Requires understanding semantics |

---

## Limitations

- The validator cannot check **semantic correctness** (does the IR compute the right value?), only structural correctness
- LLM repair may introduce **new errors** while fixing old ones — all repaired outputs must re-enter Stage 1
- For production compilers, traditional frontend lowering passes are still preferred; this system is appropriate for scaffolding, rapid prototyping, or educational tooling