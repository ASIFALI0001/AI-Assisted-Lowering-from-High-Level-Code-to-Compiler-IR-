```llvm
; ModuleID = 'abs_val_module'
source_filename = "abs_val.ll"

define i32 @abs_val(i32 %x) {
entry:
  ; Compare %x with 0. If %x is