; ModuleID = "source_program"
source_filename = "source_program"

define i32 @multiply(i32 %a, i32 %b) {
entry:
  %1 = mul i32 %a, %b
  ret i32 %1
}

define i32 @square(i32 %x) {
entry:
  %1 = call i32 @multiply(i32 %x, i32 %x)
  ret i32 %1
}

define i32 @main() {
entry:
  %val = call i32 @square(i32 7)
  ret i32 %val
}