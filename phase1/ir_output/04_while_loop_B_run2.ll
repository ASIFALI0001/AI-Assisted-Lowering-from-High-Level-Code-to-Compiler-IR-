```llvm
define i32 @sum_to_n(i32 %n) {
entry:
  br label %loop.cond

loop.cond:
  ; i.0 is the current value of i for this iteration's condition check