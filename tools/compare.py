"""
compare.py — Ground Truth vs LLM Output Diff Tool
Phase 3: Correctness Analysis

Compares a ground-truth .ll file against an LLM-generated .ll file
and produces a structured report highlighting structural differences.

Usage:
    python tools/compare.py <ground_truth.gt.ll> <llm_output.ll>

Example:
    python tools/compare.py phase1/ground_truth/04_while_loop.gt.ll \
                            phase1/ir_output/04_while_loop_B_run1.ll
"""

import re
import sys
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# IR Structural Extraction
# ---------------------------------------------------------------------------

@dataclass
class IRSummary:
    filepath: str
    functions: list = field(default_factory=list)   # list of function names
    block_labels: dict = field(default_factory=dict) # func_name -> set of labels
    phi_nodes: dict = field(default_factory=dict)    # func_name -> count
    terminators: dict = field(default_factory=dict)  # block_label -> terminator type
    branch_targets: dict = field(default_factory=dict)  # block_label -> list of targets
    register_defs: dict = field(default_factory=dict)   # func_name -> set of defined regs
    has_alloca: bool = False


def extract_summary(filepath: str) -> IRSummary:
    """Parse a .ll file and extract structural facts for comparison."""
    summary = IRSummary(filepath=filepath)

    try:
        with open(filepath) as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    current_func = None
    current_block = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            continue

        # Function definition
        func_match = re.match(r"define\s+\S+\s+@(\w+)", stripped)
        if func_match:
            current_func = func_match.group(1)
            summary.functions.append(current_func)
            summary.block_labels[current_func] = set()
            summary.phi_nodes[current_func] = 0
            summary.register_defs[current_func] = set()
            continue

        if stripped == "}" :
            current_func = None
            current_block = None
            continue

        if current_func is None:
            continue

        # Block label
        label_match = re.match(r"^(\w[\w.]*)\s*:", stripped)
        if label_match:
            current_block = label_match.group(1)
            summary.block_labels[current_func].add(current_block)
            continue

        # Track allocas
        if "alloca" in stripped:
            summary.has_alloca = True

        # Track phi nodes
        if re.match(r"%\w+\s*=\s*phi\b", stripped):
            summary.phi_nodes[current_func] += 1

        # Track terminators
        term_match = re.match(r"(ret|br)\b", stripped)
        if term_match and current_block:
            summary.terminators[current_block] = term_match.group(1)

        # Track branch targets
        if stripped.startswith("br") and current_block:
            targets = re.findall(r"label\s+%?(\w[\w.]*)", stripped)
            summary.branch_targets[current_block] = targets

        # Track defined registers
        reg_match = re.match(r"(%\w+)\s*=", stripped)
        if reg_match and current_func:
            summary.register_defs[current_func].add(reg_match.group(1))

    return summary


# ---------------------------------------------------------------------------
# Comparison & Report
# ---------------------------------------------------------------------------

def compare(gt_path: str, llm_path: str):
    print(f"\n{'='*65}")
    print(f" COMPARISON REPORT")
    print(f"  Ground Truth : {gt_path}")
    print(f"  LLM Output   : {llm_path}")
    print(f"{'='*65}")

    gt = extract_summary(gt_path)
    llm = extract_summary(llm_path)

    issues = []
    passes = []

    # --- Functions ---
    gt_funcs = set(gt.functions)
    llm_funcs = set(llm.functions)

    missing_funcs = gt_funcs - llm_funcs
    extra_funcs = llm_funcs - gt_funcs

    if missing_funcs:
        issues.append(f"Missing function(s): {missing_funcs}")
    if extra_funcs:
        issues.append(f"Extra function(s) not in ground truth: {extra_funcs}")
    if gt_funcs == llm_funcs:
        passes.append(f"Function names match: {gt_funcs}")

    # --- Per-function checks ---
    for func in gt_funcs & llm_funcs:
        gt_blocks = gt.block_labels.get(func, set())
        llm_blocks = llm.block_labels.get(func, set())

        # Block labels
        missing_blocks = gt_blocks - llm_blocks
        extra_blocks = llm_blocks - gt_blocks
        if missing_blocks:
            issues.append(f"@{func}: Missing block(s): {missing_blocks}")
        if extra_blocks:
            issues.append(f"@{func}: Extra block(s) not in ground truth: {extra_blocks}")
        if gt_blocks == llm_blocks:
            passes.append(f"@{func}: Block labels match: {gt_blocks}")

        # Phi node count
        gt_phi = gt.phi_nodes.get(func, 0)
        llm_phi = llm.phi_nodes.get(func, 0)
        if gt_phi != llm_phi:
            issues.append(
                f"@{func}: Phi node count mismatch — ground truth has {gt_phi}, "
                f"LLM output has {llm_phi}. "
                + ("Missing phi nodes — likely SSA merge point not handled." if llm_phi < gt_phi else "Unexpected extra phi nodes.")
            )
        else:
            passes.append(f"@{func}: Phi node count matches ({gt_phi})")

        # Terminator coverage
        gt_term_blocks = set(gt.terminators.keys())
        llm_term_blocks = set(llm.terminators.keys())
        missing_terms = gt_term_blocks - llm_term_blocks
        if missing_terms:
            issues.append(
                f"@{func}: Block(s) {missing_terms} have terminators in ground truth "
                f"but not in LLM output."
            )
        else:
            passes.append(f"@{func}: All terminator blocks present")

        # Branch targets
        for block, gt_targets in gt.branch_targets.items():
            llm_targets = llm.branch_targets.get(block, [])
            if set(gt_targets) != set(llm_targets):
                issues.append(
                    f"@{func} block '%{block}': Branch targets differ — "
                    f"expected {gt_targets}, got {llm_targets}"
                )

    # --- Alloca strategy ---
    if gt.has_alloca != llm.has_alloca:
        issues.append(
            f"alloca usage mismatch: ground truth {'uses' if gt.has_alloca else 'does not use'} "
            f"alloca, but LLM output {'uses' if llm.has_alloca else 'does not use'} alloca. "
            f"(Different SSA strategies — may still be semantically equivalent)"
        )
    else:
        passes.append(f"alloca strategy matches ({'used' if gt.has_alloca else 'not used'})")

    # --- Print Results ---
    print(f"\n  ✓ PASSING CHECKS ({len(passes)}):")
    for p in passes:
        print(f"    ✓ {p}")

    print(f"\n  ✗ ISSUES FOUND ({len(issues)}):")
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"    {i}. {issue}")
    else:
        print("    (none — LLM output matches ground truth structure)")

    # --- Score ---
    total_checks = len(passes) + len(issues)
    score = len(passes) / total_checks * 100 if total_checks > 0 else 0
    print(f"\n  STRUCTURAL MATCH SCORE: {score:.0f}% ({len(passes)}/{total_checks} checks passed)")
    print(f"{'='*65}\n")

    return len(issues) == 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python tools/compare.py <ground_truth.gt.ll> <llm_output.ll>")
        sys.exit(1)
    ok = compare(sys.argv[1], sys.argv[2])
    sys.exit(0 if ok else 1)