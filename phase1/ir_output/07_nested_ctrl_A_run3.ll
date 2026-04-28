```llvm
define i32 @clamp_walk(i32 %n) {
entry:
  br label %loop_cond

loop_cond:                                        ; preds = %loop_body_end, %entry
  %i.0 = phi