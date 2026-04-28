```llvm
; ModuleID = "abs_val.ll"
source_filename = "abs_val.ll"

define dso_local i32 @abs_val(i32 %x) {
entry:
  ; Allocate stack space for the '