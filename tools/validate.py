"""
validate.py -- LLVM IR Validator Scaffold
Phase 4: Validator & Repair Architecture

Checks LLM-generated LLVM IR for:
  Stage 1: Syntax / formatting violations
  Stage 2: SSA correctness and type consistency
  Stage 3: Control flow graph validity

Usage:
    python tools/validate.py <path_to_ir_file.ll>
    python tools/validate.py phase1/ir_output/04_while_loop_A_run1.ll

Returns exit code 0 if all stages pass, 1 if any failures found.
"""

import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class Instruction:
    line_no: int
    raw: str
    result: Optional[str] = None
    result_type: Optional[str] = None
    opcode: Optional[str] = None
    operands: list = field(default_factory=list)
    is_terminator: bool = False


@dataclass
class BasicBlock:
    label: str
    instructions: list = field(default_factory=list)
    predecessors: list = field(default_factory=list)
    successors: list = field(default_factory=list)
    has_terminator: bool = False


@dataclass
class Function:
    name: str
    return_type: str
    params: list = field(default_factory=list)
    blocks: dict = field(default_factory=dict)
    entry: Optional[str] = None


@dataclass
class Diagnostic:
    stage: int
    severity: str   # "ERROR" or "WARNING"
    line_no: int
    message: str

    def __str__(self):
        return f"[STAGE {self.stage} {self.severity}] Line {self.line_no}: {self.message}"


# ---------------------------------------------------------------------------
# Instruction Normalizer
# ---------------------------------------------------------------------------

# LLVM IR qualifiers that don't affect structural analysis
_QUALIFIERS = re.compile(
    r'\b(nsw|nuw|exact|inbounds|volatile|atomic|nnan|ninf|afn|reassoc|arcp|contract|fast)\b\s*'
)
_ALIGN_ATTR = re.compile(r',\s*align\s+\d+')
_EXTRA_SPACE = re.compile(r'\s+')


def _normalize(line: str) -> str:
    """Strip LLVM qualifiers and alignment attributes before structural parsing."""
    line = _QUALIFIERS.sub('', line)
    line = _ALIGN_ATTR.sub('', line)
    line = _EXTRA_SPACE.sub(' ', line).strip()
    return line


# ---------------------------------------------------------------------------
# Stage 1: Syntax Checker
# ---------------------------------------------------------------------------

KNOWN_OPCODES = {
    "add", "sub", "mul", "sdiv", "udiv",
    "and", "or", "xor",
    "icmp", "fcmp",
    "alloca", "load", "store",
    "br", "ret",
    "call",
    "phi",
    "zext", "sext", "trunc", "bitcast", "getelementptr",
}

TERMINATORS = {"br", "ret"}


def stage1_syntax_check(lines: list) -> tuple:
    """
    Parses the IR into a list of Function objects and reports syntax errors.
    Returns (diagnostics, functions).
    """
    diagnostics = []
    functions = []
    current_func = None
    current_block = None
    in_function = False

    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line or line.startswith(";"):
            continue

        # Function definition
        func_match = re.match(
            r"define\s+(\S+)\s+@(\w+)\s*\((.*)\)\s*\{?", line
        )
        if func_match:
            ret_type = func_match.group(1)
            func_name = func_match.group(2)
            params_raw = func_match.group(3)
            params = _parse_params(params_raw)
            current_func = Function(
                name=func_name, return_type=ret_type, params=params
            )
            functions.append(current_func)
            in_function = True
            current_block = None
            continue

        if line == "}" and in_function:
            in_function = False
            current_func = None
            current_block = None
            continue

        if not in_function:
            continue

        # Basic block label
        label_match = re.match(r"^(\w[\w.]*)\s*:", line)
        if label_match:
            label = label_match.group(1)
            current_block = BasicBlock(label=label)
            if current_func.entry is None:
                current_func.entry = label
            current_func.blocks[label] = current_block
            continue

        # Implicit entry block
        if current_block is None and current_func is not None:
            current_block = BasicBlock(label="entry")
            current_func.entry = "entry"
            current_func.blocks["entry"] = current_block

        instr = _parse_instruction(line, lineno, diagnostics)
        if instr:
            current_block.instructions.append(instr)
            if instr.is_terminator:
                current_block.has_terminator = True

    # Every block must have a terminator
    for func in functions:
        for label, block in func.blocks.items():
            if not block.has_terminator:
                diagnostics.append(Diagnostic(
                    stage=1, severity="ERROR", line_no=0,
                    message=(
                        f"Block '%{label}' in @{func.name} has no terminator instruction "
                        f"(expected ret or br)."
                    )
                ))

    return diagnostics, functions


def _parse_params(params_raw: str) -> list:
    if not params_raw.strip():
        return []
    params = []
    for p in params_raw.split(","):
        parts = p.strip().split()
        if len(parts) >= 2:
            params.append((parts[0], parts[1]))
    return params


def _parse_instruction(line: str, lineno: int, diagnostics: list) -> Optional[Instruction]:
    instr = Instruction(line_no=lineno, raw=line)

    # Normalize: strip qualifiers (nsw, nuw, align N, etc.) before structural parsing
    norm = _normalize(line)

    # Result assignment: %reg = opcode ...
    assign_match = re.match(r"(%\w+)\s*=\s*(\w+)\s*(.*)", norm)
    if assign_match:
        instr.result = assign_match.group(1)
        instr.opcode = assign_match.group(2)
        instr.operands = assign_match.group(3).split()

        if instr.opcode not in KNOWN_OPCODES:
            diagnostics.append(Diagnostic(
                stage=1, severity="ERROR", line_no=lineno,
                message=f"Unknown instruction opcode '{instr.opcode}'. Check LLVM IR syntax."
            ))

        # Infer result type
        if instr.opcode == "icmp":
            instr.result_type = "i1"
        elif instr.opcode in ("add", "sub", "mul", "sdiv"):
            if instr.operands:
                instr.result_type = instr.operands[0]
        elif instr.opcode == "load":
            # load i32, i32* %ptr  -> type is first token
            if instr.operands:
                instr.result_type = instr.operands[0].rstrip(",")
        elif instr.opcode == "alloca":
            if instr.operands:
                instr.result_type = instr.operands[0].rstrip(",") + "*"
        return instr

    # Terminator without result
    term_match = re.match(r"(ret|br)\s*(.*)", norm)
    if term_match:
        instr.opcode = term_match.group(1)
        instr.operands = term_match.group(2).split()
        instr.is_terminator = True
        return instr

    # store instruction
    store_match = re.match(r"store\s+(.*)", norm)
    if store_match:
        instr.opcode = "store"
        instr.is_terminator = False
        return instr

    # call without result (void calls)
    call_match = re.match(r"call\s+(.*)", norm)
    if call_match:
        instr.opcode = "call"
        return instr

    # Unrecognized
    diagnostics.append(Diagnostic(
        stage=1, severity="WARNING", line_no=lineno,
        message=f"Could not parse instruction: '{line}'"
    ))
    return None


# ---------------------------------------------------------------------------
# Stage 2: SSA & Type Checker
# ---------------------------------------------------------------------------

def stage2_ssa_type_check(functions: list) -> list:
    diagnostics = []

    for func in functions:
        defined_regs = {}
        phi_regs = set()

        # First pass: collect all definitions
        for label, block in func.blocks.items():
            for instr in block.instructions:
                if instr.result:
                    if instr.result in defined_regs:
                        prev = defined_regs[instr.result]
                        diagnostics.append(Diagnostic(
                            stage=2, severity="ERROR", line_no=instr.line_no,
                            message=(
                                f"SSA violation: '{instr.result}' is defined more than once. "
                                f"First definition in block '%{prev[1]}' at line {prev[2]}. "
                                f"SSA requires each register to be assigned exactly once."
                            )
                        ))
                    else:
                        defined_regs[instr.result] = (instr.result_type, label, instr.line_no)

                    if instr.opcode == "phi":
                        phi_regs.add(instr.result)

        # Second pass: check branch condition types
        for label, block in func.blocks.items():
            for instr in block.instructions:
                if instr.opcode == "br" and instr.operands:
                    if instr.operands[0] == "i32":
                        diagnostics.append(Diagnostic(
                            stage=2, severity="ERROR", line_no=instr.line_no,
                            message=(
                                f"Type mismatch in block '%{label}': 'br' condition type is 'i32' "
                                f"but must be 'i1'. Use 'icmp' to produce an i1 condition value."
                            )
                        ))
                    cond_reg = next(
                        (op for op in instr.operands if op.startswith("%")), None
                    )
                    if cond_reg and cond_reg in defined_regs:
                        cond_type = defined_regs[cond_reg][0]
                        if cond_type and cond_type not in ("i1", None):
                            diagnostics.append(Diagnostic(
                                stage=2, severity="ERROR", line_no=instr.line_no,
                                message=(
                                    f"Branch condition '{cond_reg}' has type '{cond_type}', "
                                    f"but 'br' requires i1. Use icmp to generate a boolean."
                                )
                            ))

    return diagnostics


# ---------------------------------------------------------------------------
# Stage 3: Control Flow Verifier
# ---------------------------------------------------------------------------

def stage3_cfg_check(functions: list) -> list:
    diagnostics = []

    for func in functions:
        all_labels = set(func.blocks.keys())
        for label, block in func.blocks.items():
            for instr in block.instructions:
                if instr.opcode == "br":
                    targets = re.findall(r"label\s+%?(\w[\w.]*)", instr.raw)
                    for target in targets:
                        if target not in all_labels:
                            diagnostics.append(Diagnostic(
                                stage=3, severity="ERROR", line_no=instr.line_no,
                                message=(
                                    f"Branch target '%{target}' in block '%{label}' "
                                    f"does not exist in function @{func.name}. "
                                    f"Available blocks: {sorted(all_labels)}"
                                )
                            ))
                        else:
                            block.successors.append(target)
                            func.blocks[target].predecessors.append(label)

        if func.entry:
            reachable = _bfs(func.entry, func.blocks)
            for label in all_labels:
                if label not in reachable and label != func.entry:
                    diagnostics.append(Diagnostic(
                        stage=3, severity="WARNING", line_no=0,
                        message=(
                            f"Block '%{label}' in @{func.name} is unreachable from the entry block. "
                            f"It may be dead code or a missing branch target."
                        )
                    ))

        for label, block in func.blocks.items():
            has_ret = any(i.opcode == "ret" for i in block.instructions)
            if block.has_terminator and not has_ret and not block.successors:
                diagnostics.append(Diagnostic(
                    stage=3, severity="ERROR", line_no=0,
                    message=(
                        f"Block '%{label}' in @{func.name} has no successors and no 'ret'. "
                        f"This is a dead-end block -- add a branch or return."
                    )
                ))

    return diagnostics


def _bfs(start: str, blocks: dict) -> set:
    visited = set()
    queue = [start]
    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        for succ in blocks.get(node, BasicBlock(label=node)).successors:
            if succ not in visited:
                queue.append(succ)
    return visited


# ---------------------------------------------------------------------------
# validate_ir() -- callable from other scripts (no file I/O, no printing)
# ---------------------------------------------------------------------------

def validate_ir(ir_text: str) -> dict:
    """
    Run all three validation stages on an IR string directly.
    Returns a dict with keys: parse_ok, ssa_ok, cf_ok, all_ok, errors, warnings,
    stage1_errors, stage2_errors, stage3_errors.
    Used by test/demo.py and the repair loop.
    """
    lines = ir_text.splitlines(keepends=True)

    s1_diags, functions = stage1_syntax_check(lines)
    s1_errors = [d for d in s1_diags if d.severity == "ERROR"]
    s1_warns  = [d for d in s1_diags if d.severity == "WARNING"]

    result = {
        "parse_ok":      len(s1_errors) == 0,
        "ssa_ok":        False,
        "cf_ok":         False,
        "all_ok":        False,
        "errors":        [str(d) for d in s1_errors],
        "warnings":      [str(d) for d in s1_warns],
        "stage1_errors": s1_errors,
        "stage2_errors": [],
        "stage3_errors": [],
    }

    if s1_errors:
        return result

    s2_diags = stage2_ssa_type_check(functions)
    s2_errors = [d for d in s2_diags if d.severity == "ERROR"]
    result["ssa_ok"] = len(s2_errors) == 0
    result["stage2_errors"] = s2_errors
    result["errors"].extend(str(d) for d in s2_errors)

    s3_diags = stage3_cfg_check(functions)
    s3_errors = [d for d in s3_diags if d.severity == "ERROR"]
    s3_warns  = [d for d in s3_diags if d.severity == "WARNING"]
    result["cf_ok"]   = len(s3_errors) == 0
    result["all_ok"]  = result["ssa_ok"] and result["cf_ok"]
    result["stage3_errors"] = s3_errors
    result["errors"].extend(str(d) for d in s3_errors)
    result["warnings"].extend(str(d) for d in s3_warns)

    return result


# ---------------------------------------------------------------------------
# validate() -- file-based entry point (used by run_experiments.py)
# ---------------------------------------------------------------------------

def validate(filepath: str) -> bool:
    """
    Run all three validation stages on the given .ll file.
    Returns True if all stages pass, False if any errors found.
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"ERROR: File not found: {filepath}")
        return False

    all_diagnostics = []

    print(f"\n{'='*60}")
    print(f" Validating: {filepath}")
    print(f"{'='*60}")

    # Stage 1
    print("\n[Stage 1] Syntax Check...")
    s1_diags, functions = stage1_syntax_check(lines)
    all_diagnostics.extend(s1_diags)

    if any(d.severity == "ERROR" for d in s1_diags):
        for d in s1_diags:
            print(f"  {d}")
        print("\n  [FAIL] Stage 1 FAILED -- skipping deeper checks.")
        return False

    print(f"  [OK] Stage 1 passed ({len(functions)} function(s) parsed)")

    # Stage 2
    print("\n[Stage 2] SSA & Type Check...")
    s2_diags = stage2_ssa_type_check(functions)
    all_diagnostics.extend(s2_diags)

    if any(d.severity == "ERROR" for d in s2_diags):
        for d in s2_diags:
            print(f"  {d}")
        print("\n  [FAIL] Stage 2 FAILED -- fix SSA/type issues before CFG check.")
    else:
        print(f"  [OK] Stage 2 passed")

    # Stage 3
    print("\n[Stage 3] Control Flow Check...")
    s3_diags = stage3_cfg_check(functions)
    all_diagnostics.extend(s3_diags)

    if any(d.severity == "ERROR" for d in s3_diags):
        for d in s3_diags:
            print(f"  {d}")
        print("\n  [FAIL] Stage 3 FAILED")
    else:
        print(f"  [OK] Stage 3 passed")

    errors   = [d for d in all_diagnostics if d.severity == "ERROR"]
    warnings = [d for d in all_diagnostics if d.severity == "WARNING"]

    print(f"\n{'='*60}")
    if not errors:
        print(f" RESULT: [OK] ALL STAGES PASSED ({len(warnings)} warning(s))")
    else:
        print(f" RESULT: [FAIL] FAILED -- {len(errors)} error(s), {len(warnings)} warning(s)")
    print(f"{'='*60}\n")

    return len(errors) == 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/validate.py <path_to_ir.ll>")
        sys.exit(1)
    ok = validate(sys.argv[1])
    sys.exit(0 if ok else 1)
