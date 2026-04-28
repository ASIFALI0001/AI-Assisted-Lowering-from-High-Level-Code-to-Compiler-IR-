; Ground Truth: 04_while_loop.src → LLVM IR
; Construct: While Loop
; Note: Two loop-carried variables (i, total) → two phi nodes at loop.header

define i32 @sum_to_n(i32 %n) {
entry:
  br label %loop.header

loop.header:
  ; phi nodes for loop-carried variables
  %i     = phi i32 [ 0, %entry ], [ %i_next, %loop.body ]
  %total = phi i32 [ 0, %entry ], [ %total_next, %loop.body ]

  ; while condition: i < n
  %cond = icmp slt i32 %i, %n
  br i1 %cond, label %loop.body, label %loop.exit

loop.body:
  ; total = total + i
  %total_next = add i32 %total, %i
  ; i = i + 1
  %i_next = add i32 %i, 1
  br label %loop.header

loop.exit:
  ret i32 %total
}

; ---------- Validation Notes ----------
; ✓ SSA: %i and %total are phi-node results, never reassigned
; ✓ Phi nodes: entry provides initial values (0,0); loop.body provides updated values
; ✓ Back-edge: loop.body → loop.header (correct)
; ✓ Terminators: entry→br, loop.header→br(cond), loop.body→br, loop.exit→ret
; ✓ Loop exit: reached when cond is false
