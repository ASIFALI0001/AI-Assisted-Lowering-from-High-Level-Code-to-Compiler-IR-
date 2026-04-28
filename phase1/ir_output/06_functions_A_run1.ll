```llvm
; ModuleID = "source_program"
source_filename = "source_program"

; Function Definition: multiply
define i32 @multiply(i32 %a, i32 %b) {
entry:
  %1 = mul i32 %a, %b
  ret i32 %1
}

; Function Definition: square
define i32 @square(i32 %x) {
entry:
  ; Call multiply(x, x)
  %1 = call i32 @multiply(i32 %x, i32 %x)
  ret i32 %1
}

; Function Definition: main
define i32 @main() {
entry:
  ; int val = square