```llvm
define i32 @factorial(i32 %n) {
entry:
  ; Branch to the loop header to initialize phi nodes
  br label %loop.header

loop.header:
  ; Phi nodes for loop-carried variables: 'i