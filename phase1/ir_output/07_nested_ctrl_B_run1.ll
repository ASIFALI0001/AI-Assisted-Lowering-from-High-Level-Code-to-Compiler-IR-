```llvm
; ModuleID = "clamp_walk"
source_filename = "clamp_walk.ll"

define i32 @clamp_walk(i32 %n) {
entry:
  ; Initial values for i and x before entering the loop