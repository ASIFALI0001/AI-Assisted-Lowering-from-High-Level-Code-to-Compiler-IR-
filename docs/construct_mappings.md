# Construct Mappings: Source → LLVM IR Ground Truth

This document defines the **canonical translation rules** for each construct in our source language subset.
These serve as the reference (ground truth) against which LLM outputs are evaluated.

---

## Construct 1: Variable Declaration & Assignment

**Source pattern:**
```c
int x = <expr>;
```

**IR translation rule:**
- Allocate stack space with `alloca`
- Store initial value with `store`
- Every subsequent read uses `load`

**Canonical form:**
```llvm
%x = alloca i32
store i32 <expr_value>, i32* %x
; later reads:
%x_val = load i32, i32* %x
```

**Key rules:**
- The alloca always goes in the `entry` block
- Never reuse the alloca register name for a value; use a fresh `%x_val` on each load

---

## Construct 2: Arithmetic & Logical Expressions

**Source → LLVM instruction mapping:**

| Source | LLVM IR |
|--------|---------|
| `a + b` | `%r = add i32 %a, %b` |
| `a - b` | `%r = sub i32 %a, %b` |
| `a * b` | `%r = mul i32 %a, %b` |
| `a / b` | `%r = sdiv i32 %a, %b` |
| `a == b` | `%r = icmp eq i32 %a, %b` |
| `a != b` | `%r = icmp ne i32 %a, %b` |
| `a < b` | `%r = icmp slt i32 %a, %b` |
| `a > b` | `%r = icmp sgt i32 %a, %b` |
| `a && b` | `%r = and i1 %a, %b` |
| `a \|\| b` | `%r = or i1 %a, %b` |
| `!a` | `%r = xor i1 %a, true` |

**Key rules:**
- Comparisons always return `i1`, NOT `i32`
- Arithmetic operates on `i32`; do not mix types without explicit casts
- Expressions are always flattened into a sequence of named temporaries (no nested expressions in a single IR instruction)

---

## Construct 3: Conditional (`if/else`)

**Source pattern:**
```c
if (cond) {
  <then_body>
} else {
  <else_body>
}
```

**Block structure:**
```
[current block]
  → compute %cond
  → br i1 %cond, label %then, label %else

[then:]
  → <then_body instructions>
  → br label %merge

[else:]
  → <else_body instructions>
  → br label %merge

[merge:]
  → phi nodes (if any value from both branches is used later)
  → <continuation>
```

**Key rules:**
- The branch instruction must use `i1` (boolean condition)
- Both `then` and `else` blocks must branch unconditionally to `merge`
- If a variable is modified in both branches and used after, it requires a `phi` node at `merge`
- An `if` without `else` still creates a `merge` block; the "else" path jumps directly to merge

---

## Construct 4: `while` Loop

**Source pattern:**
```c
while (cond) {
  <body>
}
```

**Block structure:**
```
[pre_header / current block]
  → br label %loop.header

[loop.header:]
  → phi nodes for any variable modified in loop body
  → compute %cond
  → br i1 %cond, label %loop.body, label %loop.exit

[loop.body:]
  → <body instructions>
  → br label %loop.header   ← back-edge

[loop.exit:]
  → <continuation>
```

**Key rules:**
- Loop variables that are updated in the body MUST have phi nodes at `loop.header`
- The back-edge goes from `loop.body` to `loop.header` (not to `loop.body` itself)
- `loop.exit` is entered only when the condition is false

---

## Construct 5: `for` Loop

**Source pattern:**
```c
for (int i = 0; i < n; i = i + 1) {
  <body>
}
```

**Desugaring:** Translate to `while` loop equivalent first, then apply Construct 4 rules.

```
int i = 0;
while (i < n) {
  <body>
  i = i + 1;
}
```

**Block structure:** Identical to `while` loop, with the loop variable `i` in the phi node.

---

## Construct 6: Function Definition & Call

**Function definition:**
```c
func add(a: int, b: int) -> int {
  return a + b;
}
```
```llvm
define i32 @add(i32 %a, i32 %b) {
entry:
  %result = add i32 %a, %b
  ret i32 %result
}
```

**Function call:**
```c
int z = add(x, y);
```
```llvm
%z_val = call i32 @add(i32 %x_val, i32 %y_val)
```

**Key rules:**
- Parameter names in the `define` signature are fresh SSA values — use directly
- Every function must have a `ret` instruction on every exit path
- `void` functions use `ret void`
- Call instruction type must match the function's return type

---

## Construct 7: Nested Conditionals in Loop

**Source pattern:**
```c
while (i < n) {
  if (x > 0) {
    x = x - 1;
  } else {
    x = x + 1;
  }
  i = i + 1;
}
```

**Block structure:**
```
[loop.header:]
  %i     = phi i32 [%i_init, %pre], [%i_next, %loop.latch]
  %x     = phi i32 [%x_init, %pre], [%x_next, %loop.latch]
  %cond1 = icmp slt i32 %i, %n
  br i1 %cond1, label %loop.body, label %loop.exit

[loop.body:]
  %cond2 = icmp sgt i32 %x, 0
  br i1 %cond2, label %then, label %else

[then:]
  %x_dec = sub i32 %x, 1
  br label %loop.latch

[else:]
  %x_inc = add i32 %x, 1
  br label %loop.latch

[loop.latch:]
  %x_next = phi i32 [%x_dec, %then], [%x_inc, %else]
  %i_next = add i32 %i, 1
  br label %loop.header

[loop.exit:]
  ...
```

**Key rules:**
- Two levels of phi nodes: one at `loop.header` for loop-carried values, one at `loop.latch` for values merged from the inner conditional
- `loop.latch` is a dedicated block for merging the inner branches before the back-edge — this avoids phi nodes directly in `loop.header` from non-header predecessors