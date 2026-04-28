define i1 @compute(i32 %a, i32 %b, i32 %c) {
entry:
  %mul_tmp = mul i32 %b, %c
  %sum = add i32 %a, %mul_tmp
  %diff = sub i32 %sum, %a
  %cmp1 = icmp sgt i32 %diff, 0
  %cmp2 = icmp ne i32 %a, %b
  %result = and i1 %cmp1, %cmp2
  ret i1 %result
}