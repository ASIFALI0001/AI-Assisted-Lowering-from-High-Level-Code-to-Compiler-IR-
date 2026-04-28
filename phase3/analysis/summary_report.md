# Phase 3: Correctness Analysis — Summary Report

**Total runs:** 63  |  **Passed:** 0  |  **Failed:** 63  |  **Overall pass rate:** 0%

## Pass Rates by Construct and Prompt Variant

| Construct | Variant A | Variant B | Variant C | Total |
|-----------|-----------|-----------|-----------|-------|
| `01_var_decl` | 0/3 | 0/3 | 0/3 | 0/9 |
| `02_expressions` | 0/3 | 0/3 | 0/3 | 0/9 |
| `03_if_else` | 0/3 | 0/3 | 0/3 | 0/9 |
| `04_while_loop` | 0/3 | 0/3 | 0/3 | 0/9 |
| `05_for_loop` | 0/3 | 0/3 | 0/3 | 0/9 |
| `06_functions` | 0/3 | 0/3 | 0/3 | 0/9 |
| `07_nested_ctrl` | 0/3 | 0/3 | 0/3 | 0/9 |

## Stage-Level Pass Rates

| Construct | Parse ✓ | SSA ✓ | CF ✓ | Fully ✓ |
|-----------|---------|-------|------|---------|
| `01_var_decl` | 7/9 | 0/9 | 0/9 | 0/9 |
| `02_expressions` | 7/9 | 0/9 | 0/9 | 0/9 |
| `03_if_else` | 8/9 | 0/9 | 0/9 | 0/9 |
| `04_while_loop` | 5/9 | 0/9 | 0/9 | 0/9 |
| `05_for_loop` | 1/9 | 0/9 | 0/9 | 0/9 |
| `06_functions` | 8/9 | 0/9 | 0/9 | 0/9 |
| `07_nested_ctrl` | 3/9 | 0/9 | 0/9 | 0/9 |

## Failure Mode Distribution

| Failure Category | Count | % of Failures |
|-----------------|-------|---------------|
| SSA/Type Error | 39 | 61% |
| Syntax/Format Error | 24 | 38% |

## Per-Construct Failure Analysis

### `01_var_decl`

- **Pass rate:** 0/9
- **Failure categories:** SSA/Type Error (7x), Syntax/Format Error (2x)

### `02_expressions`

- **Pass rate:** 0/9
- **Failure categories:** Syntax/Format Error (2x), SSA/Type Error (7x)

**Example error (Variant A, Run 1):**
```
  [STAGE 1 ERROR] Line 0: Block '%entry' in @compute has no terminator instruction (expected ret or br).
```

### `03_if_else`

- **Pass rate:** 0/9
- **Failure categories:** SSA/Type Error (8x), Syntax/Format Error (1x)

### `04_while_loop`

- **Pass rate:** 0/9
- **Failure categories:** SSA/Type Error (5x), Syntax/Format Error (4x)

### `05_for_loop`

- **Pass rate:** 0/9
- **Failure categories:** Syntax/Format Error (8x), SSA/Type Error (1x)

**Example error (Variant A, Run 1):**
```
  [STAGE 1 ERROR] Line 0: Block '%entry' in @factorial has no terminator instruction (expected ret or br).
```

### `06_functions`

- **Pass rate:** 0/9
- **Failure categories:** Syntax/Format Error (1x), SSA/Type Error (8x)

**Example error (Variant A, Run 1):**
```
  [STAGE 1 ERROR] Line 0: Block '%entry' in @main has no terminator instruction (expected ret or br).
```

### `07_nested_ctrl`

- **Pass rate:** 0/9
- **Failure categories:** Syntax/Format Error (6x), SSA/Type Error (3x)

**Example error (Variant A, Run 1):**
```
  [STAGE 1 WARNING] Line 7: Could not parse instruction: '%i.0 = phi i32 [ 0, %entry ], [ %i.next'
  [STAGE 1 ERROR] Line 0: Block '%loop.header' in @clamp_walk has no terminator instruction (expected ret or br).
```

## Key Findings

> Fill in after reviewing the data above. Suggested structure:

- **Best performing construct:** _which construct had highest pass rate and why_
- **Worst performing construct:** _which had lowest and what category dominated_
- **Effect of prompt variant:** _did B or C outperform A? By how much?_
- **Most common failure mode:** _which category dominated and what does that imply_
- **Systematic pattern:** _e.g. 'LLMs consistently miss phi nodes at loop headers'_