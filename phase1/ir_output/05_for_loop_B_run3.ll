define i32 @factorial(i32 %n) {
entry:
  ; Initialize result and i before entering the loop
  ; result = 1
  ; i = 1
  br label %loop_cond

loop_cond:
  ; Phi nodes for 'i' and 'result' to reconcile values from 'entry' and 'loop_body'
  %i.0 = phi i32 [ 1, %entry ], [ %i.next, %loop_body ]
  %result.0 = phi i32 [ 1, %entry ], [ %result.next, %loop_body ]

  ; Loop condition: i <= n
  %cond = icmp sle i32 %i.0, %n
  br i1 %cond, label %loop_body, label %loop_exit

loop_body:
  ; result = result * i
  %result.next = mul i32 %result.0, %i.0
  ; i = i + 1
  %i.next = add i32 %i.0, 1
  br label %loop_cond

loop_exit:
  ; Return the final result
  ret i32 %result.0
}