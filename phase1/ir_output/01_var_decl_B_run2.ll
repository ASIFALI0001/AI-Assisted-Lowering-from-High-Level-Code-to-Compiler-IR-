define i32 @main() {
entry:
  ; int x = 5;
  ; The constant value 5 is directly used.

  ; int y = 10;
  ; The constant value 10 is directly used.

  ; int z = x + y;
  %z = add i32 5, 10

  ; return z;
  ret i32 %z
}