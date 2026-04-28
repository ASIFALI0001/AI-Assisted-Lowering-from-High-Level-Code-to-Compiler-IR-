; Ground Truth: 02_expressions.src → LLVM IR
; Construct: Arithmetic & Logical Expressions
; Note: Operator precedence enforced manually — b*c computed before a+b*c

define i1 @compute(i32 %a, i32 %b, i32 %c) {
entry:
  ; int sum = a + b * c
  %bc   = mul i32 %b, %c
  %sum  = add i32 %a, %bc

  ; int diff = sum - a
  %diff = sub i32 %sum, %a

  ; bool cmp1 = diff > 0
  %cmp1 = icmp sgt i32 %diff, 0

  ; bool cmp2 = a != b
  %cmp2 = icmp ne i32 %a, %b

  ; bool result = cmp1 && cmp2
  %result = and i1 %cmp1, %cmp2

  ret i1 %result
}

; ---------- Validation Notes ----------
; ✓ SSA: Every %register defined exactly once
; ✓ Types: mul/add/sub on i32; icmp returns i1; and on i1
; ✓ No implicit type coercions
; ✓ Operator precedence handled by instruction ordering
; ✓ Terminator: single ret i1
