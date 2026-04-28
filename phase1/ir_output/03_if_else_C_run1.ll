define i32 @abs_val(i32 %x) {
entry:
  %cond = icmp slt i32 %x, 0
  br i1 %cond, label %then, label %else
then:
  %neg = sub i32 0, %x
  br label %merge
else:
  br label %merge
merge:
  %result = phi i32 [ %neg, %then ], [ %x, %else ]
  ret i32 %result
}