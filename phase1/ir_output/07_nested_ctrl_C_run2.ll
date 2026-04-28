```llvm
define i32 @clamp_walk(i32 %n) {
entry:
  br label %loop.header

loop.header:
  %i.0 = phi i32 [ 0, %entry ], [ %i.next, %