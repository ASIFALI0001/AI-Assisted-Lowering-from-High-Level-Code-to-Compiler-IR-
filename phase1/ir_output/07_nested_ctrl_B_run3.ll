```llvm
define i32 @clamp_walk(i32 %n) {
entry:
  ; Initial values for i and x
  ; i is initialized to 0
  ; x is initialized to 10
  br label %loop.header