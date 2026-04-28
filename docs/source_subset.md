# Source Language Subset

## Overview

We study a **restricted C-like language** containing exactly **7 constructs**. This subset is intentionally small to enable deep, rigorous analysis rather than shallow breadth.

---

## Constructs Under Study

| # | Construct | Description | Test File |
|---|-----------|-------------|-----------|
| 1 | Variable Declaration & Assignment | `int x = 5;` | `01_var_decl.src` |
| 2 | Arithmetic & Logical Expressions | `x + y * z`, `a && b` | `02_expressions.src` |
| 3 | Conditional (`if/else`) | Single and nested `if/else` | `03_if_else.src` |
| 4 | `while` Loop | Simple counter loop | `04_while_loop.src` |
| 5 | `for` Loop | Index-based iteration | `05_for_loop.src` |
| 6 | Function Definition & Call | Simple functions with return value | `06_functions.src` |
| 7 | Nested Conditionals in Loop | `if/else` inside `while` | `07_nested_ctrl.src` |

---

## Grammar (Informal BNF)

```
program     := func_def*

func_def    := "func" IDENT "(" param_list ")" "->" type "{" stmt* "}"

param_list  := (IDENT ":" type ("," IDENT ":" type)*)?

stmt        := var_decl
             | assign
             | if_stmt
             | while_stmt
             | for_stmt
             | return_stmt
             | func_call ";"

var_decl    := "int" IDENT "=" expr ";"
             | "bool" IDENT "=" expr ";"

assign      := IDENT "=" expr ";"

if_stmt     := "if" "(" expr ")" "{" stmt* "}"
             | "if" "(" expr ")" "{" stmt* "}" "else" "{" stmt* "}"

while_stmt  := "while" "(" expr ")" "{" stmt* "}"

for_stmt    := "for" "(" var_decl expr ";" assign ")" "{" stmt* "}"

return_stmt := "return" expr ";"

func_call   := IDENT "(" arg_list ")"

arg_list    := (expr ("," expr)*)?

expr        := INT_LIT | BOOL_LIT | IDENT
             | expr ("+" | "-" | "*" | "/") expr
             | expr ("==" | "!=" | "<" | ">" | "<=" | ">=") expr
             | expr ("&&" | "||") expr
             | "!" expr
             | func_call

type        := "int" | "bool" | "void"

IDENT       := [a-zA-Z_][a-zA-Z0-9_]*
INT_LIT     := [0-9]+
BOOL_LIT    := "true" | "false"
```

---

## Type System

- **int**: 32-bit signed integer. Maps to `i32` in LLVM IR.
- **bool**: 1-bit boolean. Maps to `i1` in LLVM IR.
- **void**: No return value. Maps to `void` in LLVM IR.
- **Implicit coercions are NOT allowed.** All types must be explicit.

---

## Scoping Rules

- Single flat scope per function (no nested block scopes beyond control flow).
- Variables must be declared before use.
- Function names are globally scoped.

---

## Intentional Exclusions

The following are **out of scope** for this study:
- Pointers and arrays
- Structs / records
- String types
- Multiple return values
- Recursion analysis (function calls are included but recursion correctness is not a focus)
- Exception handling