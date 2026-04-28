```llvm
define i32 @factorial(i32 %n) {
entry:
  %result_init = i32 1
  %i_init = i32 1
  br label %loop_header

loop_header: