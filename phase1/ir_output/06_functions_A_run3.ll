```llvm
; ModuleID = 'source.ll'
source_filename = "source.ll"

define i32 @multiply(i32 %a, i32 %b) {
entry:
  %a.addr = alloca i32, align 4
  %b.addr = alloca i32, align 4
  store i32 %a, i32* %a.addr, align 4
  store i32 %b, i32* %b.addr, align 4
  %val_a = load i32, i32* %a.addr, align 4
  %val_b = load i32, i32* %b.addr, align 4
  %mul_res = mul nsw i32 %val_a, %val_b
  ret i32 %mul_res
}

define i32 @square(i32 %x) {