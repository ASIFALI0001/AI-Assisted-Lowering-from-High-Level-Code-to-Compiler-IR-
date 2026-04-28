define i32 @main() {
entry:
  %x = add i32 0, 5
  %y = add i32 0, 10
  %z = add i32 %x, %y
  ret i32 %z
}