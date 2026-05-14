export type Variant = 'A' | 'B' | 'C'

export function buildPrompt(source: string, variant: Variant): string {
  if (variant === 'A') {
    return `Translate the following source program into LLVM IR.\n\nSource:\n${source}\n\nProduce only the LLVM IR. No explanation. No markdown fences.`
  }
  if (variant === 'B') {
    return `Translate the following source program into LLVM IR.

Rules you MUST follow:
1. Every virtual register (%name) must be assigned exactly once (SSA form).
2. Every basic block must end with exactly one terminator: ret or br.
3. At every control-flow merge point (after if/else, at loop header), add phi nodes.
4. icmp returns i1. Arithmetic (add/sub/mul/sdiv) uses i32. Never use i32 as a branch condition.
5. For mutable variables: use alloca/store/load. Never reassign a register.
6. Do NOT add alignment attributes (align N) or qualifiers (nsw, nuw). Keep it minimal.

Source:\n${source}\n\nProduce only the LLVM IR. No explanation. No markdown fences.`
  }
  // C: few-shot
  return `Translate the following source program into LLVM IR.

Rules you MUST follow:
1. Every virtual register (%name) must be assigned exactly once (SSA form).
2. Every basic block must end with exactly one terminator: ret or br.
3. At every control-flow merge point, add phi nodes.
4. icmp returns i1. Arithmetic uses i32. Never use i32 as a branch condition.
5. For mutable variables: use alloca/store/load.
6. No alignment attributes or qualifiers. Minimal LLVM IR only.

Example -- source:
  func abs_val(x: int) -> int {
    int result = 0;
    if (x < 0) { result = 0 - x; } else { result = x; }
    return result;
  }

Example -- correct LLVM IR:
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

Now translate:

Source:\n${source}\n\nProduce only the LLVM IR. No explanation. No markdown fences.`
}

export function buildRepairPrompt(source: string, invalidIR: string, errors: string[]): string {
  const numbered = errors.map((e, i) => `  ${i + 1}. ${e}`).join('\n')
  return `The LLVM IR you generated has validation errors. Fix ALL of them.

Original source:\n${source}

Your LLVM IR (contains errors):\n${invalidIR}

Validation errors found:\n${numbered}

Rules:
1. Every register must be assigned exactly once (SSA).
2. Every block must end with ret or br.
3. Phi nodes required at ALL merge points (after if/else, at loop headers).
4. icmp returns i1. Arithmetic uses i32. Never use i32 as a branch condition.
5. Use alloca/store/load for mutable variables.
6. No alignment attributes or qualifiers. Minimal LLVM IR only.

Produce only the corrected LLVM IR. No explanation. No markdown fences.`
}
