```llvm
; ModuleID = 'abs_val.ll'
source_filename = "abs_val.c"

define dso_local i32 @abs_val(i32 noundef %x) {
entry:
  ; Allocate space for