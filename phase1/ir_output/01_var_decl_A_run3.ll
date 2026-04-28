define dso_local i32 @main() {
entry:
  %x = alloca i32, align 4
  %y = alloca i32, align 4
  %z = alloca i32, align 4
  store i32 5, i32* %x, align 4
  store i32 10, i32* %y, align 4
  %0 = load i32, i32* %x, align 4
  %1 = load i32, i32* %y, align 4
  %2 = add nsw i32 %0, %1
  store i32 %2, i32* %z, align 4
  %3 = load i32, i32* %z, align 4
  ret i32 %3
}