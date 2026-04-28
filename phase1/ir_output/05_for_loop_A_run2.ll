```llvm
; ModuleID = 'factorial.ll'
source_filename = "factorial.ll"

define i32 @factorial(i32 %n_param) {
entry:
  ; Allocate stack space for the 'n' parameter and local variables 'result