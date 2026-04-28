define i32 @factorial(i32 %n) {
entry:
  ; Initialize loop variables and jump to the loop condition check
  br label %loop_cond

loop_cond:
  ; Phi nodes to get the current values of 'i'