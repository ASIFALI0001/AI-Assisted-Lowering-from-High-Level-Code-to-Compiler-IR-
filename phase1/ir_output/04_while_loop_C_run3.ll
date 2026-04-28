define i32 @sum_to_n(i32 %n) {
entry:
  br label %loop_header

loop_header:
  ; Initialize i to 0 from 'entry' block, or take i's updated value from 'loop