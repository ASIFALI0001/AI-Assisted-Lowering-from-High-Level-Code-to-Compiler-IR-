"""
test/demo.py  --  Interactive Pipeline Demo
============================================
Shows the FULL pipeline for one program, step by step:

  Step 1: Your source code
  Step 2: The prompt we send to Gemini
  Step 3: What Gemini generates (LLVM IR)
  Step 4: Validator checks it (3 stages)
  Step 5: Compare with the correct ground truth
  Step 6: Repair loop  (feed errors back to Gemini, let it fix them)
  Step 7: Final result

Usage:
    cd "d:\\Projects 2026\\Compiler Design Project\\LLM-Compiler-Lowering"
    python test/demo.py
"""

import os
import re
import sys
import time
from pathlib import Path

# ─── Setup paths ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from dotenv import load_dotenv
load_dotenv(ROOT / "phase2" / ".env")

# ─── Google Gemini SDK ───────────────────────────────────────────────────────
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: google-genai not installed.")
    print("       Run:  pip install google-genai python-dotenv")
    sys.exit(1)

# ─── Our validator ───────────────────────────────────────────────────────────
try:
    import validate as _v
except ImportError:
    print("ERROR: Could not import tools/validate.py")
    print("       Make sure you are running from the project root.")
    sys.exit(1)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

MODEL = "gemini-2.5-flash"
MAX_TOKENS = 4096

# ─── Construct definitions ────────────────────────────────────────────────────
CONSTRUCTS = [
    ("01", "var_decl",    "Variable declarations  (simplest, no control flow)"),
    ("02", "expressions", "Arithmetic expressions (add/sub/mul, logical ops)"),
    ("03", "if_else",     "If/else branch         <- needs phi node at merge"),
    ("04", "while_loop",  "While loop             <- phi nodes at loop header"),
    ("05", "for_loop",    "For loop               <- desugared to while"),
    ("06", "functions",   "Function definitions & calls"),
    ("07", "nested_ctrl", "If/else inside while   <- hardest, 2-level phi"),
]

# ─── Prompt builders ─────────────────────────────────────────────────────────

def prompt_A(source: str) -> str:
    """Minimal: no rules, no examples. Gemini must know everything itself."""
    return (
        "Translate the following source program into LLVM IR.\n\n"
        f"Source:\n{source}\n\n"
        "Produce only the LLVM IR. No explanation. No markdown fences."
    )


def prompt_B(source: str) -> str:
    """Rule-injected: all 6 key LLVM IR rules spelled out."""
    return (
        "Translate the following source program into LLVM IR.\n\n"
        "Rules you MUST follow:\n"
        "1. Every virtual register (%name) must be assigned exactly once (SSA form).\n"
        "2. Every basic block must end with exactly one terminator: ret or br.\n"
        "3. At every control-flow merge point (after if/else, at loop header), add phi nodes.\n"
        "4. icmp returns i1. Arithmetic (add/sub/mul/sdiv) uses i32. Never use i32 as a branch condition.\n"
        "5. For mutable variables: use alloca/store/load. Never reassign a register.\n"
        "6. Do NOT add alignment attributes (align N) or qualifiers (nsw, nuw). Keep it minimal.\n\n"
        f"Source:\n{source}\n\n"
        "Produce only the LLVM IR. No explanation. No markdown fences."
    )


def prompt_C(source: str) -> str:
    """Few-shot: rules + one worked if/else example."""
    return (
        "Translate the following source program into LLVM IR.\n\n"
        "Rules you MUST follow:\n"
        "1. Every virtual register (%name) must be assigned exactly once (SSA form).\n"
        "2. Every basic block must end with exactly one terminator: ret or br.\n"
        "3. At every control-flow merge point, add phi nodes.\n"
        "4. icmp returns i1. Arithmetic uses i32. Never use i32 as a branch condition.\n"
        "5. For mutable variables: use alloca/store/load.\n"
        "6. No alignment attributes or qualifiers. Minimal LLVM IR only.\n\n"
        "Example -- source:\n"
        "  func abs_val(x: int) -> int {\n"
        "    int result = 0;\n"
        "    if (x < 0) { result = 0 - x; } else { result = x; }\n"
        "    return result;\n"
        "  }\n\n"
        "Example -- correct LLVM IR:\n"
        "  define i32 @abs_val(i32 %x) {\n"
        "  entry:\n"
        "    %cond = icmp slt i32 %x, 0\n"
        "    br i1 %cond, label %then, label %else\n"
        "  then:\n"
        "    %neg = sub i32 0, %x\n"
        "    br label %merge\n"
        "  else:\n"
        "    br label %merge\n"
        "  merge:\n"
        "    %result = phi i32 [ %neg, %then ], [ %x, %else ]\n"
        "    ret i32 %result\n"
        "  }\n\n"
        "Now translate:\n\n"
        f"Source:\n{source}\n\n"
        "Produce only the LLVM IR. No explanation. No markdown fences."
    )


def prompt_repair(source: str, invalid_ir: str, errors: list) -> str:
    """Repair prompt: show Gemini its own errors and ask it to fix them."""
    numbered = "\n".join(f"  {i+1}. {e}" for i, e in enumerate(errors))
    return (
        "The LLVM IR you generated has validation errors. Fix ALL of them.\n\n"
        f"Original source:\n{source}\n\n"
        f"Your LLVM IR (contains errors):\n{invalid_ir}\n\n"
        f"Validation errors found:\n{numbered}\n\n"
        "Rules to fix them:\n"
        "1. Every register must be assigned exactly once (SSA).\n"
        "2. Every block must end with ret or br.\n"
        "3. Phi nodes required at ALL merge points (after if/else, at loop headers).\n"
        "4. icmp returns i1. Arithmetic uses i32. Never use i32 as a branch condition.\n"
        "5. Use alloca/store/load for mutable variables.\n"
        "6. No alignment attributes or qualifiers. Minimal LLVM IR only.\n\n"
        "Produce only the corrected LLVM IR. No explanation. No markdown fences."
    )


PROMPT_FNS = {"A": prompt_A, "B": prompt_B, "C": prompt_C}

PROMPT_DESC = {
    "A": "Minimal     -- just ask, give no rules",
    "B": "Rule-based  -- inject all 6 LLVM IR rules into the prompt",
    "C": "Few-shot    -- rules + one worked if/else example",
}

# ─── Formatting helpers ───────────────────────────────────────────────────────

WIDTH = 66


def banner(title="", char="="):
    if title:
        pad = max(2, (WIDTH - len(title) - 2) // 2)
        right = WIDTH - pad - len(title) - 2
        print(f"\n{char * pad} {title} {char * right}")
    else:
        print(char * WIDTH)


def show_code(text: str, indent=2):
    prefix = " " * indent
    for i, line in enumerate(text.splitlines(), 1):
        print(f"{prefix}{i:3d} | {line}")


def pause(msg="Press Enter to continue..."):
    input(f"\n  [ {msg} ]\n")


# ─── Gemini API ───────────────────────────────────────────────────────────────

def call_gemini(prompt: str, client) -> str:
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=MAX_TOKENS, temperature=0.7),
    )
    return response.text


def extract_ir(raw: str) -> str:
    """Strip markdown code fences if Gemini wrapped the IR."""
    fence = re.search(r"```(?:llvm|ll)?\s*\n(.*?)```", raw, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return raw.strip()


# ─── Validator wrapper ────────────────────────────────────────────────────────

def run_validator(ir_text: str) -> dict:
    """Call the 3-stage validator on IR text directly. Returns result dict."""
    return _v.validate_ir(ir_text)


def print_validator_results(vr: dict):
    """Print validator results in a human-readable format."""
    print()

    # Stage 1
    if vr["parse_ok"]:
        print("  Stage 1 - Syntax Check   : [PASS] No syntax errors found")
    else:
        print("  Stage 1 - Syntax Check   : [FAIL]")
        for d in vr["stage1_errors"]:
            print(f"      ERROR: {d.message}")
        print()
        print("  Stage 2 - SSA/Type Check : [SKIP] (stage 1 failed, skipping)")
        print("  Stage 3 - CFG Check      : [SKIP] (stage 1 failed, skipping)")
        _print_overall(vr)
        return

    # Stage 2
    if vr["ssa_ok"]:
        print("  Stage 2 - SSA/Type Check : [PASS] All registers single-assigned, types OK")
    else:
        print("  Stage 2 - SSA/Type Check : [FAIL]")
        for d in vr["stage2_errors"]:
            print(f"      ERROR: {d.message}")

    # Stage 3
    if vr["cf_ok"]:
        print("  Stage 3 - CFG Check      : [PASS] All blocks reachable, no dead ends")
    else:
        print("  Stage 3 - CFG Check      : [FAIL]")
        for d in vr["stage3_errors"]:
            print(f"      ERROR: {d.message}")

    if vr["warnings"]:
        print(f"\n  Warnings ({len(vr['warnings'])}):")
        for w in vr["warnings"]:
            print(f"      WARN:  {w}")

    _print_overall(vr)


def _print_overall(vr: dict):
    print()
    if vr["all_ok"]:
        print("  ╔══════════════════════════════════════════════════════╗")
        print("  ║  RESULT:  *** ALL STAGES PASSED ***                 ║")
        print("  ║  The generated LLVM IR is structurally valid.       ║")
        print("  ╚══════════════════════════════════════════════════════╝")
    else:
        n = len(vr["errors"])
        print(f"  RESULT: FAILED -- {n} error(s) found")
        print()
        print("  What the errors mean:")
        for err in vr["errors"]:
            if "SSA violation" in err:
                print(f"    - SSA violation: A variable (%register) was assigned more than once.")
                print(f"      LLVM IR requires each name to be assigned exactly once.")
            elif "phi" in err.lower():
                print(f"    - Missing phi node: After an if/else or at a loop header, when a variable")
                print(f"      can come from two different paths, you need a phi node to pick the right one.")
            elif "terminator" in err.lower():
                print(f"    - Missing terminator: Every code block must end with 'ret' (return) or 'br' (branch).")
            elif "type mismatch" in err.lower() or "i32" in err and "i1" in err:
                print(f"    - Type mismatch: Branch conditions must be i1 (1-bit bool), not i32 (32-bit int).")
                print(f"      Use 'icmp' to compare integers and get an i1 result.")
            elif "branch target" in err.lower() or "does not exist" in err.lower():
                print(f"    - Bad branch target: The IR jumps to a block label that doesn't exist.")
            else:
                print(f"    - {err[:100]}")


# ─── Ground truth comparison ──────────────────────────────────────────────────

def compare_with_ground_truth(cid: str, cname: str, ir_text: str):
    gt_path = ROOT / "phase1" / "ground_truth" / f"{cid}_{cname}.gt.ll"
    if not gt_path.exists():
        print("  (No ground truth file available for custom programs)")
        return

    gt_text = gt_path.read_text(encoding="utf-8")

    print("\n  Ground truth (hand-written CORRECT IR for this program):")
    print("  " + "-" * 60)
    show_code(gt_text, indent=4)
    print()

    # Structural comparison
    gt_blocks = set(re.findall(r"^(\w[\w.]*)\s*:", gt_text, re.MULTILINE))
    llm_blocks = set(re.findall(r"^(\w[\w.]*)\s*:", ir_text, re.MULTILINE))
    gt_phis = len(re.findall(r"=\s*phi\b", gt_text))
    llm_phis = len(re.findall(r"=\s*phi\b", ir_text))
    gt_fns = re.findall(r"define\s+\S+\s+@(\w+)", gt_text)
    llm_fns = re.findall(r"define\s+\S+\s+@(\w+)", ir_text)

    print("  Structural comparison (LLM output vs ground truth):")
    print("  " + "-" * 60)

    # Functions
    if set(gt_fns) == set(llm_fns):
        print(f"  [MATCH]  Functions defined: {gt_fns}")
    else:
        miss = set(gt_fns) - set(llm_fns)
        extra = set(llm_fns) - set(gt_fns)
        if miss:  print(f"  [MISS]   Missing functions: {miss}")
        if extra: print(f"  [EXTRA]  Extra functions:   {extra}")

    # Block labels
    if gt_blocks == llm_blocks:
        print(f"  [MATCH]  Block labels: {sorted(gt_blocks)}")
    else:
        missing_b = gt_blocks - llm_blocks
        extra_b   = llm_blocks - gt_blocks
        if missing_b: print(f"  [MISS]   Missing blocks: {missing_b}")
        if extra_b:   print(f"  [EXTRA]  Extra blocks:   {extra_b}")
        if missing_b:
            print(f"           -> Gemini didn't create the expected basic blocks")

    # Phi nodes
    if gt_phis == llm_phis:
        print(f"  [MATCH]  Phi nodes: {gt_phis}")
    else:
        print(f"  [DIFF]   Phi nodes: ground truth={gt_phis}, Gemini={llm_phis}")
        if llm_phis < gt_phis:
            diff = gt_phis - llm_phis
            print(f"           -> Gemini is MISSING {diff} phi node(s).")
            print(f"              This is the #1 failure mode: LLMs forget phi nodes")
            print(f"              at if/else merge points and loop headers.")
        elif llm_phis > gt_phis:
            print(f"           -> Gemini added EXTRA phi nodes (may still be valid)")


# ─── Repair loop ─────────────────────────────────────────────────────────────

def run_repair_loop(source: str, ir: str, errors: list, client, max_cycles=3):
    """
    Feed errors back to Gemini, let it fix the IR.
    Returns (final_ir, passed, cycles_used).
    """
    current_ir = ir

    for cycle in range(1, max_cycles + 1):
        banner(f"REPAIR CYCLE {cycle} of {max_cycles}", char="-")
        print(f"\n  We found {len(errors)} error(s) in the IR.")
        print("  Sending those errors back to Gemini with a new prompt...")
        print(f"\n  Errors being sent:")
        for i, e in enumerate(errors, 1):
            print(f"    {i}. {e[:120]}")

        print(f"\n  Calling Gemini... ", end="", flush=True)
        try:
            repair_p = prompt_repair(source, current_ir, errors)
            raw = call_gemini(repair_p, client)
            current_ir = extract_ir(raw)
            print("done.\n")
        except Exception as ex:
            print(f"\n  API error during repair: {ex}")
            break

        print("  Gemini's repaired IR:")
        print("  " + "-" * 60)
        show_code(current_ir, indent=4)
        print()

        print("  Re-validating the repaired IR...")
        vr = run_validator(current_ir)
        print_validator_results(vr)

        if vr["all_ok"]:
            print(f"\n  *** REPAIR SUCCEEDED after {cycle} cycle(s)! ***")
            return current_ir, True, cycle

        errors = vr["errors"]
        if cycle < max_cycles:
            print(f"\n  Still {len(errors)} error(s). Trying cycle {cycle + 1}...")
            pause("Press Enter for next repair cycle...")
        else:
            print(f"\n  Max repair cycles ({max_cycles}) reached. Could not fully fix the IR.")

    return current_ir, False, max_cycles


# ─── Interactive pickers ──────────────────────────────────────────────────────

def pick_construct():
    banner("PICK A TEST PROGRAM")
    print()
    for i, (cid, cname, desc) in enumerate(CONSTRUCTS, 1):
        print(f"  [{i}]  {cid}_{cname:<16}  {desc}")
    print(f"  [c]  custom            Write your own (edit test/my_program.src first)")
    print()

    while True:
        choice = input("  Your choice (1-7 or c): ").strip().lower()
        if choice == "c":
            src_path = Path(__file__).parent / "my_program.src"
            if not src_path.exists():
                print(f"  ERROR: {src_path} not found.")
                print(f"         Create test/my_program.src with your program.")
                continue
            source = src_path.read_text(encoding="utf-8")
            return "00", "custom", source
        if choice.isdigit() and 1 <= int(choice) <= 7:
            cid, cname, _ = CONSTRUCTS[int(choice) - 1]
            src_path = ROOT / "phase1" / "src_programs" / f"{cid}_{cname}.src"
            source = src_path.read_text(encoding="utf-8")
            return cid, cname, source
        print("  Invalid. Enter 1-7 or c.")


def pick_variant():
    banner("PICK PROMPT STYLE")
    print()
    print("  This controls what instructions we give Gemini along with the source code.")
    print("  We test 3 styles to see if giving more guidance improves accuracy:\n")
    for key, desc in PROMPT_DESC.items():
        print(f"  [{key}]  {desc}")
    print()
    while True:
        choice = input("  Your choice (A / B / C): ").strip().upper()
        if choice in ("A", "B", "C"):
            return choice
        print("  Enter A, B, or C.")


# ─── Main pipeline ────────────────────────────────────────────────────────────

def main():
    banner("LLM COMPILER LOWERING  --  INTERACTIVE PIPELINE DEMO")
    print("""
  This tool shows the FULL pipeline for one program:

    [1] Source code  -->  [2] Gemini generates LLVM IR
    [3] Validator checks the IR  -->  [4] Compare with correct ground truth
    [5] Repair loop: feed errors back to Gemini  -->  [6] Final result

  LLVM IR is the "internal language" of a compiler.
  It has strict rules: SSA form, phi nodes, correct types, terminators.
  We're testing whether an AI (Gemini) can follow these rules correctly.
""")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  ERROR: GEMINI_API_KEY not found.")
        print("         Check that phase2/.env contains GEMINI_API_KEY=your_key")
        sys.exit(1)

    print("  API key loaded. Connecting to Gemini...", end="", flush=True)
    client = genai.Client(api_key=api_key)
    print(" ready.\n")

    # ── Pick construct & variant ─────────────────────────────────────────────
    cid, cname, source = pick_construct()
    variant = pick_variant()

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Show source code
    # ─────────────────────────────────────────────────────────────────────────
    banner("STEP 1  --  YOUR SOURCE CODE")
    print(f"\n  Program: {cid}_{cname}.src\n")
    show_code(source)
    print("""
  This is written in our custom C-like language.
  The LLM's job: translate this into LLVM IR.
  LLVM IR is what a real compiler produces as its first internal step.
""")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2: Show prompt
    # ─────────────────────────────────────────────────────────────────────────
    banner("STEP 2  --  PROMPT SENT TO GEMINI")
    prompt = PROMPT_FNS[variant](source)
    print(f"\n  Variant {variant}: {PROMPT_DESC[variant]}\n")
    print("  Full prompt:")
    print("  " + "-" * 60)
    show_code(prompt, indent=4)
    print("  " + "-" * 60)
    print("""
  What each variant means:
    A = No guidance -- Gemini must know all LLVM IR rules by itself
    B = Rules given  -- We spell out the 6 key rules in the prompt
    C = Example given -- Rules + a worked if/else example (few-shot)

  Research question: Does giving more guidance help Gemini?
""")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: Call Gemini, show output
    # ─────────────────────────────────────────────────────────────────────────
    banner("STEP 3  --  GEMINI GENERATING LLVM IR")
    print("\n  Calling Gemini API...", end="", flush=True)
    try:
        raw_output = call_gemini(prompt, client)
        print(" done.\n")
    except Exception as e:
        print(f"\n  API ERROR: {e}")
        sys.exit(1)

    ir_text = extract_ir(raw_output)

    print("  Raw response from Gemini (exactly what it returned):")
    print("  " + "-" * 60)
    for line in raw_output.splitlines():
        print(f"    {line}")
    print("  " + "-" * 60)

    print("\n  Extracted IR (markdown fences stripped if present):")
    print("  " + "-" * 60)
    show_code(ir_text, indent=4)
    print("  " + "-" * 60)
    print("""
  This is the LLVM IR Gemini produced. Now we need to check if it's correct.
  The validator will check 3 things:
    Stage 1: Are the instructions valid LLVM syntax?
    Stage 2: Is SSA form correct? (each %register assigned exactly once)
    Stage 3: Is the control flow graph valid? (no missing/dead blocks)
""")
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: Validate
    # ─────────────────────────────────────────────────────────────────────────
    banner("STEP 4  --  RUNNING THE VALIDATOR")
    print("""
  The validator is a Python script we wrote (tools/validate.py).
  It checks Gemini's IR against LLVM IR rules in 3 stages:

    Stage 1 -- SYNTAX:   Are instruction names correct? Does every block
               end with ret or br?
    Stage 2 -- SSA/TYPE: Is each %register defined exactly once?
               Is the branch condition i1 (not i32)?
    Stage 3 -- CFG:      Do all branches point to real blocks?
               Are all blocks reachable from the entry block?
""")

    vr = run_validator(ir_text)
    print_validator_results(vr)

    first_pass = vr["all_ok"]
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: Ground truth comparison
    # ─────────────────────────────────────────────────────────────────────────
    banner("STEP 5  --  COMPARING WITH GROUND TRUTH")
    print("""
  The ground truth is the CORRECT LLVM IR we wrote by hand for each program.
  We compare Gemini's output structurally (blocks, phi nodes, branches).
""")
    compare_with_ground_truth(cid, cname, ir_text)
    pause()

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: Repair loop
    # ─────────────────────────────────────────────────────────────────────────
    final_ir = ir_text
    repair_success = False
    repair_cycles = 0

    banner("STEP 6  --  REPAIR LOOP")

    if vr["all_ok"]:
        print("""
  No repair needed! Gemini's first attempt passed all validation stages.

  This usually happens for simpler constructs (var_decl, expressions)
  that don't need phi nodes or complex control flow.
""")
    else:
        print(f"""
  Gemini's IR failed with {len(vr["errors"])} error(s).

  The repair loop works like this:
    1. Take the exact error messages from the validator
    2. Include them in a new prompt: "Here are your mistakes -- fix them"
    3. Gemini tries again with full knowledge of what went wrong
    4. Re-validate. If still failing, repeat up to 3 times.

  This is the "validator + repair architecture" from Phase 4 of the project.
""")
        go = input("  Start the repair loop? (y/n): ").strip().lower()
        if go == "y":
            final_ir, repair_success, repair_cycles = run_repair_loop(
                source, ir_text, vr["errors"], client, max_cycles=3
            )
        else:
            print("  Skipping repair loop.")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7: Save and final summary
    # ─────────────────────────────────────────────────────────────────────────
    out_file = OUTPUT_DIR / f"{cid}_{cname}_variant{variant}.ll"
    out_file.write_text(final_ir, encoding="utf-8")

    banner("FINAL RESULT")
    print(f"""
  Program tested  : {cid}_{cname}
  Prompt variant  : {variant}  ({PROMPT_DESC[variant]})
  First attempt   : {"PASSED" if first_pass else "FAILED"}""")

    if not first_pass:
        print(f"  Repair result   : {'PASSED' if repair_success else 'STILL FAILED'}")
        print(f"  Repair cycles   : {repair_cycles}")

    print(f"\n  Final IR saved  : {out_file}\n")

    if first_pass:
        print("  What this means:")
        print("  -> Gemini got it right on the first try!")
        print("     This usually happens for simple constructs without phi nodes.")
        print("     (var_decl and expressions are straightforward straight-line code)")

    elif repair_success:
        print("  What this means:")
        print("  -> Gemini failed at first, but fixed it after seeing the errors.")
        print("     This confirms the REPAIR LOOP works.")
        print("     Targeted error feedback helps the LLM understand what it did wrong.")

    else:
        print("  What this means:")
        print("  -> Gemini couldn't fix this even after 3 repair cycles.")
        print("     This usually happens for complex control flow (loops, nested if/else)")
        print("     where phi node reasoning is too difficult without more guidance.")
        print("     Try variant B or C (with explicit rules) for better results.")

    banner()
    print(f"\n  Run again with a different construct or variant to compare results!\n")


if __name__ == "__main__":
    main()
