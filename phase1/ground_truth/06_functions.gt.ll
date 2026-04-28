; Ground Truth: 06_functions.src → LLVM IR
; Construct: Function Definition & Call
; Note: Three functions; call instruction types must match signatures exactly

define i32 @multiply(i32 %a, i32 %b) {
entry:
  %result = mul i32 %a, %b
  ret i32 %result
}

define i32 @square(i32 %x) {
entry:
  ; call multiply(x, x)
  %result = call i32 @multiply(i32 %x, i32 %x)
  ret i32 %result
}

define i32 @main() {
entry:
  ; int val = square(7)
  %val = call i32 @square(i32 7)
  ret i32 %val
}

; ---------- Validation Notes ----------
; ✓ Each function has correct return type in signature
; ✓ call instruction types match callee signature
; ✓ Each function has exactly one entry block and one ret
; ✓ No phi nodes needed (straight-line functions)
; ✓ Integer literal 7 used directly in call argument
