```llvm
; ModuleID = 'compute_module'
source_filename = "compute.ll"

define i1 @compute(i32 %a, i32 %b, i32 %c) {
entry:
  ; Allocate stack space