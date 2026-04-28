```llvm
define i32 @sum_to_n(i32 %n) {
entry:
  ; Initial values for i (0) and total (0) are passed to the loop header's phi nodes.
  br label %loop.header

loop