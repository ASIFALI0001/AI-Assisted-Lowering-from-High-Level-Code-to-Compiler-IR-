define i32 @multiply(i32 %a, i32 %b) {
entry:
  %mul = mul i32 %a, %b
  ret i32 %mul
}

define i32 @square(i32 %x) {
entry:
  %call = call i32 @multiply(i32 %x, i32 %x)
  ret i32 %call
}

define i32 @main() {
entry:
  %val = call i32 @square(i32 7)
  ret i32 %val
}