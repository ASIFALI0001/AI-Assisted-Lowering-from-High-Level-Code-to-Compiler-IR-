"""
phase3/analyze_results.py — Results Analyzer
Phase 3: Correctness Analysis & Failure Categorization

Reads all JSON logs from phase2/raw_outputs/
Produces:
  - Console summary table
  - phase3/failure_logs/results_filled.csv  (filled-in version of results.csv)
  - phase3/analysis/summary_report.md       (written report of findings)

Usage (from project root):
    python phase3/analyze_results.py
"""

import json
import csv
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
RAW_OUT_DIR  = ROOT / "phase2" / "raw_outputs"
ANALYSIS_DIR = ROOT / "phase3" / "analysis"
FAILURE_DIR  = ROOT / "phase3" / "failure_logs"

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
# Failure Categorization
# ---------------------------------------------------------------------------

def categorize_failure(log: dict) -> str:
    """
    Infer the primary failure category from validator output.
    Returns one of the 6 taxonomy categories or 'None' if passed.
    """
    if log.get("all_ok"):
        return "None"

    v = log.get("validator_output", "").lower()

    if not log.get("parse_ok"):
        if "unknown instruction" in v or "could not parse" in v:
            return "Syntax/Format Error"
        return "Syntax/Format Error"

    if not log.get("ssa_ok"):
        if "ssa violation" in v or "defined more than once" in v:
            return "SSA Violation"
        if "missing phi" in v or "phi node" in v:
            return "Missing Phi Node"
        if "type mismatch" in v or "i32" in v and "i1" in v:
            return "Type Mismatch"
        return "SSA/Type Error"

    if not log.get("cf_ok"):
        if "does not exist" in v or "branch target" in v:
            return "CF Defect (Bad Branch Target)"
        if "unreachable" in v:
            return "CF Defect (Unreachable Block)"
        if "dead-end" in v or "no successors" in v:
            return "CF Defect (Dead-End Block)"
        return "Control Flow Defect"

    return "Semantic Drift"


# ---------------------------------------------------------------------------
# Load All Logs
# ---------------------------------------------------------------------------

def load_all_logs() -> list[dict]:
    logs = []
    for path in sorted(RAW_OUT_DIR.glob("*.json")):
        try:
            log = json.loads(path.read_text(encoding="utf-8"))
            log["failure_category"] = categorize_failure(log)
            logs.append(log)
        except Exception as e:
            print(f"WARNING: Could not read {path.name}: {e}")
    return logs


# ---------------------------------------------------------------------------
# Build Summary Tables
# ---------------------------------------------------------------------------

def pass_rate_table(logs: list[dict]) -> dict:
    """
    Returns nested dict: stats[construct_id][variant] = {runs, parse, ssa, cf, all}
    """
    stats = defaultdict(lambda: defaultdict(lambda: {
        "runs": 0, "parse": 0, "ssa": 0, "cf": 0, "all": 0
    }))
    for log in logs:
        cid = log["construct_id"]
        var = log["prompt_variant"]
        s = stats[cid][var]
        s["runs"] += 1
        if log.get("parse_ok"): s["parse"] += 1
        if log.get("ssa_ok"):   s["ssa"]   += 1
        if log.get("cf_ok"):    s["cf"]    += 1
        if log.get("all_ok"):   s["all"]   += 1
    return stats


def failure_distribution(logs: list[dict]) -> dict:
    dist = defaultdict(int)
    for log in logs:
        if not log.get("all_ok"):
            dist[log["failure_category"]] += 1
    return dict(sorted(dist.items(), key=lambda x: -x[1]))


# ---------------------------------------------------------------------------
# Print Console Summary
# ---------------------------------------------------------------------------

def print_summary(logs: list[dict], stats: dict):
    total = len(logs)
    passed = sum(1 for l in logs if l.get("all_ok"))

    print(f"\n{'='*70}")
    print(f"  PHASE 3 — RESULTS SUMMARY")
    print(f"  Total runs analyzed: {total}   |   Overall pass rate: {passed}/{total} ({100*passed//total if total else 0}%)")
    print(f"{'='*70}")

    # Per-construct pass rate table
    print(f"\n  Pass Rate by Construct and Prompt Variant (fully correct / runs)\n")
    header = f"  {'Construct':<22} {'Variant A':>10} {'Variant B':>10} {'Variant C':>10} {'Total':>10}"
    print(header)
    print(f"  {'-'*62}")

    construct_names = {cid: name for cid, name in CONSTRUCTS}

    for cid, cname in CONSTRUCTS:
        row = f"  {cid}_{cname:<20}"
        total_c = 0
        pass_c  = 0
        for var in VARIANTS:
            s = stats[cid][var]
            r, a = s["runs"], s["all"]
            row += f"  {a}/{r}".rjust(10)
            total_c += r
            pass_c  += a
        row += f"  {pass_c}/{total_c}".rjust(10)
        print(row)

    # Failure distribution
    dist = failure_distribution(logs)
    total_failures = sum(dist.values())
    print(f"\n  Failure Mode Distribution ({total_failures} total failures)\n")
    for cat, count in dist.items():
        pct = 100 * count // total_failures if total_failures else 0
        bar = "█" * (count * 20 // max(dist.values(), default=1))
        print(f"  {cat:<40} {count:>3}  {pct:>3}%  {bar}")

    print(f"\n{'='*70}\n")


# ---------------------------------------------------------------------------
# Write Filled CSV
# ---------------------------------------------------------------------------

def write_filled_csv(logs: list[dict]):
    out_path = FAILURE_DIR / "results_filled.csv"
    FAILURE_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "construct_id", "construct_name", "prompt_variant", "run_number",
        "parse_ok", "ssa_ok", "cf_ok", "all_ok",
        "failure_category", "validator_output_summary"
    ]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for log in logs:
            # Shorten validator output for CSV readability
            val_summary = (log.get("validator_output") or "")[:200].replace("\n", " | ")
            writer.writerow({
                "construct_id":   log["construct_id"],
                "construct_name": log["construct_name"],
                "prompt_variant": log["prompt_variant"],
                "run_number":     log["run_number"],
                "parse_ok":       log.get("parse_ok"),
                "ssa_ok":         log.get("ssa_ok"),
                "cf_ok":          log.get("cf_ok"),
                "all_ok":         log.get("all_ok"),
                "failure_category": log["failure_category"],
                "validator_output_summary": val_summary,
            })

    print(f"  ✓ Filled CSV written: {out_path}")


# ---------------------------------------------------------------------------
# Write Markdown Summary Report
# ---------------------------------------------------------------------------

def write_summary_report(logs: list[dict], stats: dict):
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ANALYSIS_DIR / "summary_report.md"

    total  = len(logs)
    passed = sum(1 for l in logs if l.get("all_ok"))
    dist   = failure_distribution(logs)
    total_failures = sum(dist.values())
    construct_names = {cid: name for cid, name in CONSTRUCTS}

    lines = []
    lines.append("# Phase 3: Correctness Analysis — Summary Report\n")
    lines.append(f"**Total runs:** {total}  |  **Passed:** {passed}  |  **Failed:** {total - passed}  |  **Overall pass rate:** {100*passed//total if total else 0}%\n")

    # Pass rate table
    lines.append("## Pass Rates by Construct and Prompt Variant\n")
    lines.append("| Construct | Variant A | Variant B | Variant C | Total |")
    lines.append("|-----------|-----------|-----------|-----------|-------|")
    for cid, cname in CONSTRUCTS:
        cells = []
        total_c = pass_c = 0
        for var in VARIANTS:
            s = stats[cid][var]
            r, a = s["runs"], s["all"]
            cells.append(f"{a}/{r}")
            total_c += r; pass_c += a
        lines.append(f"| `{cid}_{cname}` | {' | '.join(cells)} | {pass_c}/{total_c} |")
    lines.append("")

    # Stage-level breakdown
    lines.append("## Stage-Level Pass Rates\n")
    lines.append("| Construct | Parse ✓ | SSA ✓ | CF ✓ | Fully ✓ |")
    lines.append("|-----------|---------|-------|------|---------|")
    for cid, cname in CONSTRUCTS:
        runs = parse = ssa = cf = all_ = 0
        for var in VARIANTS:
            s = stats[cid][var]
            runs  += s["runs"]
            parse += s["parse"]
            ssa   += s["ssa"]
            cf    += s["cf"]
            all_  += s["all"]
        pct = lambda n: f"{n}/{runs}" if runs else "0/0"
        lines.append(f"| `{cid}_{cname}` | {pct(parse)} | {pct(ssa)} | {pct(cf)} | {pct(all_)} |")
    lines.append("")

    # Failure distribution
    lines.append("## Failure Mode Distribution\n")
    lines.append("| Failure Category | Count | % of Failures |")
    lines.append("|-----------------|-------|---------------|")
    for cat, count in dist.items():
        pct = f"{100*count//total_failures}%" if total_failures else "0%"
        lines.append(f"| {cat} | {count} | {pct} |")
    lines.append("")

    # Per-construct analysis
    lines.append("## Per-Construct Failure Analysis\n")
    for cid, cname in CONSTRUCTS:
        construct_logs = [l for l in logs if l["construct_id"] == cid]
        failures = [l for l in construct_logs if not l.get("all_ok")]
        fail_cats = defaultdict(int)
        for l in failures:
            fail_cats[l["failure_category"]] += 1

        lines.append(f"### `{cid}_{cname}`\n")
        total_c = len(construct_logs)
        pass_c  = sum(1 for l in construct_logs if l.get("all_ok"))
        lines.append(f"- **Pass rate:** {pass_c}/{total_c}")

        if fail_cats:
            lines.append(f"- **Failure categories:** " + ", ".join(f"{k} ({v}x)" for k, v in fail_cats.items()))
        else:
            lines.append("- **No failures recorded.**")

        # Show one example failure if any
        for log in failures[:1]:
            val_out = (log.get("validator_output") or "").strip()
            if val_out:
                # Extract just the error lines
                error_lines = [ln for ln in val_out.splitlines() if "ERROR" in ln or "WARNING" in ln]
                if error_lines:
                    lines.append(f"\n**Example error (Variant {log['prompt_variant']}, Run {log['run_number']}):**")
                    lines.append("```")
                    lines.extend(error_lines[:3])
                    lines.append("```")
        lines.append("")

    # Key findings
    lines.append("## Key Findings\n")
    lines.append("> Fill in after reviewing the data above. Suggested structure:\n")
    lines.append("- **Best performing construct:** _which construct had highest pass rate and why_")
    lines.append("- **Worst performing construct:** _which had lowest and what category dominated_")
    lines.append("- **Effect of prompt variant:** _did B or C outperform A? By how much?_")
    lines.append("- **Most common failure mode:** _which category dominated and what does that imply_")
    lines.append("- **Systematic pattern:** _e.g. 'LLMs consistently miss phi nodes at loop headers'_")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ Summary report written: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"\nLoading logs from {RAW_OUT_DIR} ...")
    logs = load_all_logs()

    if not logs:
        print(f"\nNo JSON logs found in {RAW_OUT_DIR}")
        print("Run phase2/run_experiments.py first to generate outputs.")
        sys.exit(1)

    print(f"Loaded {len(logs)} log(s).\n")

    stats = pass_rate_table(logs)
    print_summary(logs, stats)
    write_filled_csv(logs)
    write_summary_report(logs, stats)

    print(f"\n  Next step: review phase3/analysis/summary_report.md")
    print(f"             and fill in 'Key Findings' section manually.\n")


if __name__ == "__main__":
    main()