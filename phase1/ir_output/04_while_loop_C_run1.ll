define i32 @sum_to_n(i32 %n) {
entry:
  br label %loop_header

loop_header:
  %i.0 = phi i32 [ 0, %entry ], [ %i.next