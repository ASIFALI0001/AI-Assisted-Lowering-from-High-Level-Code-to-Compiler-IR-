; ModuleID = "compute_module"
source_filename = "compute.swift"

define i1 @compute(i32 %a, i32 %b, i32 %c) {
entry:
  ; int sum = a + b * c;
  %b_times_c = mul i32 %b, %c
  %sum = add i32 %a, %b_times_c

  ; int diff = sum - a;
  %diff = sub i32 %sum, %a

  ; bool cmp1 = diff > 0;
  %cmp1 = icmp sgt i32 %diff, 0

  ; bool cmp2 = a != b;
  %cmp2 = icmp ne i32 %a, %b

  ; bool result = cmp1 && cmp2;
  %result = and i1 %cmp1, %cmp2

  ; return result;
  ret i1 %result
}