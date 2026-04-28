```llvm
; ModuleID = 'abs_val_module'
source_filename = "abs_val.ll"

define dso_local i32 @abs_val(i32 %x) {
entry:
  ; The initial 'result