; Ground Truth: 03_if_else.src → LLVM IR
; Construct: Conditional (if/else)
; Note: 'result' is assigned in both branches → phi node required at merge

define i32 @abs_val(i32 %x) {
entry:
  %cond = icmp slt i32 %x, 0
  br i1 %cond, label %then, label %else

then:
  %neg = sub i32 0, %x
  br label %merge

else:
  ; result = x (no transformation)
  br label %merge

merge:
  ; phi: result comes from 'then' as %neg, or from 'else' as %x
  %result = phi i32 [ %neg, %then ], [ %x, %else ]
  ret i32 %result
}

; ---------- Validation Notes ----------
; ✓ SSA: %cond, %neg, %result each defined once
; ✓ Phi node at merge: both predecessors (then, else) covered
; ✓ Terminators: entry→br, then→br, else→br, merge→ret
; ✓ Branch condition uses i1 (%cond from icmp)
; ✓ No alloca needed — x is a parameter, result resolved by phi
