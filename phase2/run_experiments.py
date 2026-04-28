"""
phase2/run_experiments.py — LLM Experimentation Runner (GEMINI Version - New SDK)
Phase 2: Systematic IR generation from Gemini API
"""

import os
import json
import time
import sys
import re
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# NEW SDK: Use google.genai instead of google.generativeai
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: google-genai package not found. Run: pip install google-genai")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL = "gemini-2.5-flash"  # Latest model as of 2026
MAX_TOKENS = 1500
RUNS_PER_VARIANT = 3
DELAY_BETWEEN_CALLS = 2  # seconds, to avoid rate limiting

ROOT = Path(__file__).parent.parent
SRC_DIR = ROOT / "phase1" / "src_programs"
IR_OUT_DIR = ROOT / "phase1" / "ir_output"
RAW_OUT_DIR = ROOT / "phase2" / "raw_outputs"
VALIDATE_SCRIPT = ROOT / "tools" / "validate.py"

CONSTRUCTS = [
    ("01", "var_decl"),
    ("02", "expressions"),
    ("03", "if_else"),
    ("04", "while_loop"),
    ("05", "for_loop"),
    ("06", "functions"),
    ("07", "nested_ctrl"),
]

VARIANTS = ["A", "B", "C"]

# ---------------------------------------------------------------------------
# Prompt Builders (same as before)
# ---------------------------------------------------------------------------

def build_prompt_A(source: str) -> str:
    """Minimal prompt — no rules, no examples."""
    return f"""Translate the following source program into LLVM IR.

Source:
{source}

Produce only the LLVM IR. No explanation."""

def build_prompt_B(source: str) -> str:
    """Detailed prompt with explicit SSA and IR rules."""
    return f"""Translate the following source program into LLVM IR.

Target IR rules you MUST follow:
1. Every virtual register (e.g. %x) must be assigned exactly once (SSA form).
2. Every basic block must end with exactly one terminator: ret, br, or conditional br.
3. At any control-flow merge point (after if/else or at a loop header), use phi nodes
   to reconcile values from different predecessor blocks.
4. Comparison instructions (icmp) return i1. Arithmetic (add, sub, mul, sdiv) uses i32.
5. Do NOT use i32 as a branch condition — only i1 is valid.
6. For mutable variables, use alloca/store/load or phi nodes — never reassign a register.

Source:
{source}

Produce only the LLVM IR. No explanation."""

def build_prompt_C(source: str) -> str:
    """Few-shot prompt with one reference if/else example."""
    return f"""Translate the following source program into LLVM IR.

Target IR rules you MUST follow:
1. Every virtual register must be assigned exactly once (SSA form).
2. Every basic block must end with exactly one terminator: ret, br, or conditional br.
3. At control-flow merge points, use phi nodes.
4. icmp returns i1. Arithmetic uses i32. Do not use i32 as a branch condition.
5. For mutable variables use alloca/store/load or phi nodes.

Example — source:
  func abs_val(x: int) -> int {{
    int result = 0;
    if (x < 0) {{ result = 0 - x; }} else {{ result = x; }}
    return result;
  }}

Example — correct LLVM IR:
  define i32 @abs_val(i32 %x) {{
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
  }}

Now translate this program:

Source:
{source}

Produce only the LLVM IR. No explanation."""

PROMPT_BUILDERS = {
    "A": build_prompt_A,
    "B": build_prompt_B,
    "C": build_prompt_C,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_ir(raw_output: str) -> str:
    """Strip markdown code fences if the model wrapped the IR in ```llvm ... ```."""
    fence_match = re.search(r"```(?:llvm|ll)?\s*\n(.*?)```", raw_output, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    return raw_output.strip()

def run_validate(ir_path: Path) -> dict:
    """Run tools/validate.py on the given IR file."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), str(ir_path)],
        capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    return {
        "parse_ok":  "Stage 1 passed" in output,
        "ssa_ok":    "Stage 2 passed" in output,
        "cf_ok":     "Stage 3 passed" in output,
        "all_ok":    "ALL STAGES PASSED" in output,
        "validator_output": output.strip(),
    }

def load_source(construct_id: str, construct_name: str) -> str:
    src_file = SRC_DIR / f"{construct_id}_{construct_name}.src"
    if not src_file.exists():
        print(f"  WARNING: Source file not found: {src_file}")
        return ""
    return src_file.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Main Experiment Loop (NEW SDK version)
# ---------------------------------------------------------------------------

def run_all_experiments():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable not set.")
        print("Make sure you have a .env file with GEMINI_API_KEY=your_key_here")
        sys.exit(1)

    # Initialize the new SDK client
    client = genai.Client(api_key=api_key)

    IR_OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_OUT_DIR.mkdir(parents=True, exist_ok=True)

    total = len(CONSTRUCTS) * len(VARIANTS) * RUNS_PER_VARIANT
    done = 0
    passed = 0

    print(f"\n{'='*65}")
    print(f"  Phase 2 — LLM Experimentation (GEMINI - New SDK)")
    print(f"  Model: {MODEL}")
    print(f"  Constructs: {len(CONSTRUCTS)}  |  Variants: {len(VARIANTS)}  |  Runs each: {RUNS_PER_VARIANT}")
    print(f"  Total API calls: {total}")
    print(f"{'='*65}\n")

    for cid, cname in CONSTRUCTS:
        source = load_source(cid, cname)
        if not source:
            continue

        print(f"\n── Construct {cid}: {cname} {'─'*40}")

        for variant in VARIANTS:
            prompt = PROMPT_BUILDERS[variant](source)

            for run in range(1, RUNS_PER_VARIANT + 1):
                done += 1
                tag = f"{cid}_{cname}_{variant}_run{run}"
                print(f"  [{done:02d}/{total}] {tag} ... ", end="", flush=True)

                raw_path = RAW_OUT_DIR / f"{tag}.json"
                ir_path  = IR_OUT_DIR  / f"{tag}.ll"
                
                if raw_path.exists() and ir_path.exists():
                    print("skipped (already exists)")
                    continue

                try:
                    # NEW SDK API call
                    response = client.models.generate_content(
                        model=MODEL,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            max_output_tokens=MAX_TOKENS,
                            temperature=0.7,
                        )
                    )
                    
                    raw_output = response.text
                    ir_text = extract_ir(raw_output)

                except Exception as e:
                    print(f"API ERROR: {e}")
                    continue

                # Save extracted IR
                ir_path.write_text(ir_text, encoding="utf-8")

                # Validate
                val = run_validate(ir_path)
                if val["all_ok"]:
                    passed += 1
                    status = "✓ PASS"
                else:
                    stages = []
                    if not val["parse_ok"]: stages.append("syntax")
                    if not val["ssa_ok"]:   stages.append("SSA")
                    if not val["cf_ok"]:    stages.append("CF")
                    status = f"✗ FAIL ({', '.join(stages)})"

                print(status)

                # Save full JSON log
                log = {
                    "construct_id":   cid,
                    "construct_name": cname,
                    "prompt_variant": variant,
                    "run_number":     run,
                    "model":          MODEL,
                    "provider":       "gemini",
                    "sdk_version":    "google.genai (new)",
                    "timestamp":      datetime.utcnow().isoformat() + "Z",
                    "source_file":    f"{cid}_{cname}.src",
                    "prompt_sent":    prompt,
                    "raw_output":     raw_output,
                    "ir_extracted":   ir_text,
                    "parse_ok":       val["parse_ok"],
                    "ssa_ok":         val["ssa_ok"],
                    "cf_ok":          val["cf_ok"],
                    "all_ok":         val["all_ok"],
                    "validator_output": val["validator_output"],
                    "notes":          "",
                }
                raw_path.write_text(json.dumps(log, indent=2), encoding="utf-8")

                time.sleep(DELAY_BETWEEN_CALLS)

    # Final summary
    print(f"\n{'='*65}")
    print(f"  PHASE 2 COMPLETE (GEMINI - New SDK)")
    print(f"  Total runs:    {done}")
    print(f"  Fully passed:  {passed} / {done}  ({100*passed//done if done else 0}%)")
    print(f"  Raw logs:      {RAW_OUT_DIR}")
    print(f"  IR files:      {IR_OUT_DIR}")
    print(f"\n  Next step: run  python phase3/analyze_results.py")
    print(f"{'='*65}\n")

if __name__ == "__main__":
    run_all_experiments()