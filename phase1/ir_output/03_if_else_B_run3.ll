```llvm
define i32 @abs_val(i32 %x) {
entry:
  %cond = icmp slt i32 %x, 0
  br i1 %cond, label %if.then, label %if.else

if