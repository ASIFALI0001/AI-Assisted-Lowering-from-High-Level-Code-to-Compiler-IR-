define i32 @sum_to_n(i32 %n) {
entry:
  br label %loop_header

loop_header:
  %i.0 = phi i32 [ 0, %entry ], [ %i.next, %loop_body ]
  %total.0 = phi i32 [ 0, %entry ], [ %total.next, %loop_body ]
  %cond = icmp slt i32 %i.0, %n
  br i1 %cond, label %loop_body, label %loop_exit

loop_body:
  %total.next = add i32 %total.0, %i.0
  %i.next = add i32 %i.0, 1
  br label %loop_header

loop_exit:
  ret i32 %total.0
}