; Ground Truth: 05_for_loop.src → LLVM IR
; Construct: For Loop (desugared to while)
; Note: for(int i=1; i<=n; i=i+1) becomes a while loop with i in phi

define i32 @factorial(i32 %n) {
entry:
  ; result = 1 (initial value before loop)
  br label %loop.header

loop.header:
  ; i starts at 1; result starts at 1
  %i      = phi i32 [ 1, %entry ], [ %i_next, %loop.body ]
  %result = phi i32 [ 1, %entry ], [ %result_next, %loop.body ]

  ; condition: i <= n
  %cond = icmp sle i32 %i, %n
  br i1 %cond, label %loop.body, label %loop.exit

loop.body:
  ; result = result * i
  %result_next = mul i32 %result, %i
  ; i = i + 1
  %i_next = add i32 %i, 1
  br label %loop.header

loop.exit:
  ret i32 %result
}

; ---------- Validation Notes ----------
; ✓ For-loop desugared correctly to while structure
; ✓ Two phi nodes at loop.header (i and result)
; ✓ i_next and result_next flow back to phi nodes
; ✓ Loop exit returns the accumulated result
; ✓ All terminators present and correct
