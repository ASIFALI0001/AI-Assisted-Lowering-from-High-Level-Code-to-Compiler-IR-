; Ground Truth: 07_nested_ctrl.src → LLVM IR
; Construct: Nested Conditionals in Loop
; Note: Two-level phi nodes required:
;   - loop.header: carries i and x across iterations
;   - loop.latch:  merges x from then/else before back-edge

define i32 @clamp_walk(i32 %n) {
entry:
  br label %loop.header

loop.header:
  ; Loop-carried variables: i (counter), x (value being walked)
  %i = phi i32 [ 0,       %entry      ], [ %i_next, %loop.latch ]
  %x = phi i32 [ 10,      %entry      ], [ %x_next, %loop.latch ]

  ; while condition: i < n
  %cond = icmp slt i32 %i, %n
  br i1 %cond, label %loop.body, label %loop.exit

loop.body:
  ; inner if: x > 0
  %inner_cond = icmp sgt i32 %x, 0
  br i1 %inner_cond, label %then, label %else

then:
  ; x = x - 1
  %x_dec = sub i32 %x, 1
  br label %loop.latch

else:
  ; x = x + 1
  %x_inc = add i32 %x, 1
  br label %loop.latch

loop.latch:
  ; Merge x from both branches of the inner conditional
  %x_next = phi i32 [ %x_dec, %then ], [ %x_inc, %else ]
  ; i = i + 1
  %i_next = add i32 %i, 1
  br label %loop.header

loop.exit:
  ret i32 %x
}

; ---------- Validation Notes ----------
; ✓ Outer phi nodes at loop.header: (i, x) from entry and loop.latch
; ✓ Inner phi node at loop.latch: x_next from then and else
; ✓ loop.latch is a dedicated block — prevents phi nodes at loop.header
;   from needing then/else as predecessors (they are not direct predecessors)
; ✓ Back-edge: loop.latch → loop.header (correct)
; ✓ loop.exit reads %x (the phi at loop.header, not x_next)
;   because exit is taken before the latch executes on that iteration
; ✓ All 6 blocks have terminators
; ✓ Phi node predecessor lists are exactly correct:
;   - loop.header phi: predecessors = {entry, loop.latch}
;   - loop.latch phi:  predecessors = {then, else}
