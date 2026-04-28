define i32 @factorial(i32 %n) {
entry:
  ; Initialize result and i before entering the loop
  %result_init = i32 1
  %i_init = i32 1
  br label %loop_header

loop_header:
  ; Phi nodes for result and i, carrying values from entry or previous loop iteration
  %current_result = phi i32 [ %result_init, %entry ], [ %next_result, %loop_body ]
  %current_i = phi i32 [ %i_init, %entry ], [ %next_i, %loop_body ]

  ; Loop condition: i <= n
  %cond = icmp sle i32 %current_i, %n
  br i1 %cond, label %loop_body, label %loop_exit

loop_body:
  ; Calculate result = result * i
  %next_result = mul i32 %current_result, %current_i
  ; Calculate i = i + 1
  %next_i = add i32 %current_i, 1
  br label %loop_header

loop_exit:
  ; The final result is the value of current_result when the loop condition failed
  ret i32 %current_result
}