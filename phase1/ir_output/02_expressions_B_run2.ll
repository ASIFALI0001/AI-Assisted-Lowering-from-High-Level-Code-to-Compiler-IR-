define i1 @compute(i32 %a, i32 %b, i32 %c) {
entry:
  %0 = mul i32 %b, %c
  %sum_val = add i32 %a, %0
  %diff_val = sub i32 %sum_val, %a
  %cmp1_val = icmp sgt i32 %diff_val, 0
  %cmp2_val = icmp ne i32 %a, %b
  %result_val = and i1 %cmp1_val, %cmp2_val
  ret i1 %result_val
}