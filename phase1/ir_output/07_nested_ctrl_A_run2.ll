```llvm
; Function Attrs: noinline nounwind optnone uwtable
define dso_local i32 @clamp_walk(i32 %n) #0 {
entry:
  ; Initial values for i and x
  br label %loop.header