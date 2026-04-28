define i1 @compute(i32 %a, i32 %b, i32 %c) {
entry:
  %1 = mul i32 %b, %c
  %2 = add i32 %a, %1
  %3 = sub i32 %2, %a
  %4 = icmp sgt i32 %3, 0
  %5 = icmp ne i32 %a, %b
  %6 = and i1 %4, %5
  ret i1 %6
}