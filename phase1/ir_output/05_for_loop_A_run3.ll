```llvm
define i32 @factorial(i32 %n) {
entry:
  %result_ptr = alloca i32, align 4
  %i_ptr = alloca i32, align 4
  store i3