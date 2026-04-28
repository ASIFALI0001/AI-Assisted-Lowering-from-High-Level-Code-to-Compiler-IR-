```llvm
; ModuleID = "sum_to_n"
source_filename = "sum_to_n.c"

define dso_local i32 @sum_to_n(i32 %n) {
entry:
  ; Initialize