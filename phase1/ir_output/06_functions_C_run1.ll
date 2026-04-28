define i32 @multiply(i32 %a, i32 %b) {
entry:
  %mul_res = mul i32 %a, %b
  ret i32 %mul_res
}

define i32 @square(i32 %x) {
entry:
  %call_multiply = call i32 @multiply(i32 %x, i32 %x)
  ret i32 %call_multiply
}

define i32 @main() {
entry:
  %call_square = call i32 @square(i32 7)
  ret i32 %call_square
}