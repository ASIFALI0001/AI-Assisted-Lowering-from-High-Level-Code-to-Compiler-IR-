; Ground Truth: 01_var_decl.src → LLVM IR
; Construct: Variable Declaration & Assignment
; Note: Using alloca/store/load for mutable variables (simpler SSA strategy)

define i32 @main() {
entry:
  %x = alloca i32
  %y = alloca i32
  %z = alloca i32

  store i32 5, i32* %x
  store i32 10, i32* %y

  %x_val = load i32, i32* %x
  %y_val = load i32, i32* %y
  %z_val = add i32 %x_val, %y_val
  store i32 %z_val, i32* %z

  %ret = load i32, i32* %z
  ret i32 %ret
}

; ---------- Validation Notes ----------
; ✓ SSA: Every %register defined exactly once
; ✓ Terminators: entry block ends with ret
; ✓ Types: all i32 operations, correct ret type
; ✓ No phi nodes needed (straight-line code)
