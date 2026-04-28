```llvm
define i32 @clamp_walk(i32 %n_param) {
entry:
  ; Initial values for i and x
  ; i = 0
  ; x = 10
  br label %loop.header

loop.header