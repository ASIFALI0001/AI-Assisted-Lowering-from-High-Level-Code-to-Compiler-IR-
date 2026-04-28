; ModuleID = 'source_program'
source_filename = "source_program"

define i32 @main() {
entry:
  ; Allocate space for local variables
  %x = alloca i32, align 4
  %y = alloca i32, align 4
  %z = alloca i32, align 4

  ; int x = 5;
  store i32 5, i32* %x, align 4

  ; int y = 10;
  store i32 10, i32* %y, align 4

  ; int z = x + y;
  %0 = load i32, i32* %x, align 4 ; Load value of x
  %1 = load i32, i32* %y, align 4 ; Load value of y
  %add_tmp = add nsw i32 %0, %1 ; Perform addition
  store i32 %add_tmp, i32* %z, align 4 ; Store result in z

  ; return z;
  %2 = load i32, i32* %z, align 4 ; Load value of z
  ret i32 %2
}