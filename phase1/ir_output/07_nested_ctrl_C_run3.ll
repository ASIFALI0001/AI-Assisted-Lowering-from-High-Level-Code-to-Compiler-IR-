define i32 @clamp_walk(i32 %n) {
entry:
  ; Initial values for i and x before the loop.
  ; These are the initial incoming values for the phi nodes in the loop header.
  ; Control flow immediately jumps to the