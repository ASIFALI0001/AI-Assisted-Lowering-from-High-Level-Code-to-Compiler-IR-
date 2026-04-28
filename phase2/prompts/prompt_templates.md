# Phase 2 Prompt Templates

This file defines the prompt variants used for LLM experimentation.
Each variant is used across all 7 test programs to study how prompt
design affects output quality.

---

## PROMPT VARIANT A — Minimal Prompt

> Use this to establish a baseline. No IR rules, no examples.

```
Translate the following source program into LLVM IR.

Source:
<INSERT SOURCE PROGRAM HERE>

Produce only the LLVM IR. No explanation.
```

---

## PROMPT VARIANT B — Detailed Prompt (with SSA rules)

> Provides IR constraints explicitly. Tests whether rule reminders help.

```
Translate the following source program into LLVM IR.

Target IR rules you MUST follow:
1. Every virtual register (e.g. %x) must be assigned exactly once (SSA form).
2. Every basic block must end with exactly one terminator: ret, br, or conditional br.
3. At any control-flow merge point (after if/else or at a loop header), use phi nodes
   to reconcile values from different predecessor blocks.
4. Comparison instructions (icmp) return i1. Arithmetic (add, sub, mul, sdiv) uses i32.
5. Do NOT use i32 as a branch condition — only i1 is valid.

Source:
<INSERT SOURCE PROGRAM HERE>

Produce only the LLVM IR. No explanation.
```

---

## PROMPT VARIANT C — Detailed Prompt with One Reference Example

> Adds a worked example. Tests whether few-shot helps with phi nodes.

```
Translate the following source program into LLVM IR.

Target IR rules you MUST follow:
1. Every virtual register must be assigned exactly once (SSA form).
2. Every basic block must end with exactly one terminator: ret, br, or conditional br.
3. At control-flow merge points, use phi nodes.
4. icmp returns i1. Arithmetic uses i32. Do not use i32 as branch condition.

Example — source:
  func abs_val(x: int) -> int {
    int result = 0;
    if (x < 0) { result = 0 - x; } else { result = x; }
    return result;
  }

Example — correct LLVM IR:
  define i32 @abs_val(i32 %x) {
  entry:
    %cond = icmp slt i32 %x, 0
    br i1 %cond, label %then, label %else
  then:
    %neg = sub i32 0, %x
    br label %merge
  else:
    br label %merge
  merge:
    %result = phi i32 [ %neg, %then ], [ %x, %else ]
    ret i32 %result
  }

Now translate this program:

Source:
<INSERT SOURCE PROGRAM HERE>

Produce only the LLVM IR. No explanation.
```

---

## PROMPT VARIANT D — Repair / Feedback Prompt

> Used in Phase 4 validation loop. Fed back to LLM after a failed validation.

```
The following LLVM IR is invalid. Fix it based on the error diagnostics provided.

Original source program:
<INSERT SOURCE PROGRAM HERE>

Invalid IR (your previous output):
<INSERT INVALID IR HERE>

Validation errors:
<INSERT DIAGNOSTIC MESSAGES HERE>

Rules reminder:
- Every register is assigned exactly once (SSA).
- Every block must end with a terminator (ret or br).
- Phi nodes are required at every control-flow merge point.
- Branch conditions must be i1 (from icmp), not i32.

Produce corrected LLVM IR only. No explanation.
```

---

## Experiment Logging Template

For each run, record the following in `phase2/raw_outputs/`:

```json
{
  "construct_id": "04",
  "construct_name": "while_loop",
  "prompt_variant": "B",
  "run_number": 1,
  "model": "claude-sonnet-4-20250514",
  "timestamp": "2025-01-01T00:00:00Z",
  "source_file": "04_while_loop.src",
  "prompt_sent": "...",
  "raw_output": "...",
  "parse_ok": null,
  "ssa_ok": null,
  "cf_ok": null,
  "type_ok": null,
  "notes": ""
}
```

`parse_ok`, `ssa_ok`, `cf_ok`, `type_ok` are filled in during Phase 3.