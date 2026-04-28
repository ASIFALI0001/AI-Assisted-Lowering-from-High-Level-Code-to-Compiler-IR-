```llvm
define i32 @factorial(i32 %n) {
entry:
  ; Initialize loop variables and branch to the loop header
  br label %loop_header

loop_header:
  ; Phi nodes to carry the values of i and result across loop