```llvm
define i32 @sum_to_n(i32 %n) {
entry:
  ; The initial values for i and total are 0.
  ; Branch to the loop header to establish the phi nodes.
  br label %