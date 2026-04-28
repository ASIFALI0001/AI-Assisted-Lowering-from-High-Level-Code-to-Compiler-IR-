# Target IR Specification: LLVM IR

## Why LLVM IR?

- Strict **SSA (Static Single Assignment)** form is mandatory and well-documented
- Extensive verification tooling (`llvm-as`, `opt -verify`, `FileCheck`)
- Dominance and phi-node rules are formal and checkable
- Widely used in research and industry — results are broadly applicable

---

## Core Rules (Constraints the LLM Must Follow)

### 1. SSA Form

- Every **virtual register** (e.g., `%x`, `%tmp1`) is **assigned exactly once**.
- You may never reassign a register: `%x = add i32 %x, 1` is **ILLEGAL**.
- To represent mutable variables, use either:
  - `alloca` / `store` / `load` (memory-based, simpler for LLMs to produce)
  - Or pure SSA with phi nodes at merge points (structurally correct but harder)

### 2. Basic Blocks

- Every function body is split into **basic blocks**.
- A basic block is a maximal sequence of instructions with:
  - **No branch targets in the middle** (entry is only at the top)
  - **Exactly one terminator** at the end (`br`, `ret`, etc.)
- Basic blocks are labeled: `entry:`, `then:`, `merge:`, `loop.header:`, etc.

### 3. Terminator Instructions

Every basic block must end with exactly one of:
- `ret <type> <value>` — return from function
- `br i1 <cond>, label %true_block, label %false_block` — conditional branch
- `br label %target_block` — unconditional branch

**A block with no terminator is a syntax error.**

### 4. Phi Nodes

- At any point where **control flow merges** (e.g., after an `if/else`, at a loop header), SSA values flowing in from different predecessor blocks must be reconciled using a **phi node**.
- Phi nodes must appear at the **very top** of a basic block, before any other instructions.
- Syntax: `%result = phi i32 [ %val_from_blockA, %blockA ], [ %val_from_blockB, %blockB ]`
- Every predecessor block must have an entry in the phi node.

### 5. Type System

| Source Type | LLVM IR Type |
|-------------|-------------|
| `int`       | `i32`       |
| `bool`      | `i1`        |
| `void`      | `void`      |

- Comparison instructions (`icmp`) return `i1`.
- Arithmetic instructions (`add`, `sub`, `mul`, `sdiv`) operate on `i32`.
- You cannot use `i32` where `i1` is expected (e.g., as a branch condition) without an explicit cast.

### 6. Function Signatures

```llvm
define <return_type> @<name>(<type> %<param>, ...) {
  ...
}
```

- All parameter types and the return type must be declared.
- The entry block is always the first block in the function body.

---

## Common Instruction Reference

```llvm
; Arithmetic
%r = add i32 %a, %b
%r = sub i32 %a, %b
%r = mul i32 %a, %b
%r = sdiv i32 %a, %b    ; signed division

; Comparison (returns i1)
%cond = icmp eq  i32 %a, %b
%cond = icmp ne  i32 %a, %b
%cond = icmp slt i32 %a, %b   ; signed less than
%cond = icmp sle i32 %a, %b
%cond = icmp sgt i32 %a, %b
%cond = icmp sge i32 %a, %b

; Boolean / Bitwise
%r = and i1 %a, %b
%r = or  i1 %a, %b
%r = xor i1 %a, true           ; logical NOT

; Memory (for mutable variables)
%ptr = alloca i32              ; stack allocation
store i32 %val, i32* %ptr      ; write
%val = load i32, i32* %ptr     ; read

; Control Flow
br i1 %cond, label %true_bb, label %false_bb
br label %next_bb
ret i32 %val
ret void

; Function Call
%result = call i32 @func_name(i32 %arg1, i32 %arg2)

; Phi Node
%x = phi i32 [ %x_from_entry, %entry ], [ %x_from_loop, %loop.body ]
```

---

## Complete Minimal Example

Source:
```c
func add(a: int, b: int) -> int {
  return a + b;
}
```

LLVM IR (correct):
```llvm
define i32 @add(i32 %a, i32 %b) {
entry:
  %result = add i32 %a, %b
  ret i32 %result
}
```

---

## Common Mistakes to Watch For (LLM Failure Patterns)

| Mistake | Example |
|---------|---------|
| SSA violation | `%x = add i32 %x, 1` |
| Missing terminator | Block ends without `ret` or `br` |
| Missing phi node | Value used after merge without phi |
| Type mismatch | `br i32 %cond, ...` (should be `i1`) |
| Wrong block name in phi | Referencing a block that isn't a predecessor |
| Using undefined register | `%y = add i32 %x, %z` where `%z` was never defined |