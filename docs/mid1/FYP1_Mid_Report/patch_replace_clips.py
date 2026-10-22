#!/usr/bin/env python3
"""Replace remaining PDF table clips with \\input{tables/...}."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAPTERS = ROOT / "chapters"

# illustration basename -> tables/*.tex
MAP = {
    "tbl_p26_453": "tab_objectives",
    "tbl_p28_90": "tab_scope_modules",
    "tbl_p29_224": "tab_stakeholders",
    "tbl_p35_172": "tab_retrieval_compare",
    "tbl_p37_188": "tab_tech_challenges",
    "tbl_p38_139": "tab_findings_design",
    "tbl_p41_458": "tab_work_packages",
    "tbl_p42_465": "tab_progress",
    "tbl_p44_284": "tab_commits_phase",
    "tbl_p47_490": "tab_usecases",
    "tbl_p54_349": "tab_traceability",
    "tbl_p56_304": "tab_components",
    "tbl_p59_232": "tab_decisions",
    "tbl_p60_168": "tab_design_evolution",
    "tbl_p70_518": "tab_tools",
    "tbl_p81_305": "tab_acceptance",
    "tbl_p84_203": "tab_edge_cases",
    "tbl_p85_90": "tab_defects",
    "tbl_p88_90": "tab_ownership",
    "tbl_p88_467": "tab_activity",
    "tbl_p90_90": "tab_prs",
    "tbl_p90_641": "tab_milestones",
    "tbl_p97_502": "tab_remaining_modules",
    "tbl_p107_409": "tab_all_fr",
    "tbl_p109_470": "tab_all_nfr",
}

# Match a whole table float that only wraps a PDF clip (with optional caption/label)
TABLE_FLOAT = re.compile(
    r"\\begin\{table\}\[[^\]]*\]\s*"
    r"\\centering\s*"
    r"(?:\\caption\{[^}]*\}\s*)?"
    r"(?:\\label\{[^}]*\}\s*)?"
    r"\\includegraphics\[[^\]]*\]\{illustrations/(tbl_p[^}]+)\.pdf\}\s*"
    r"\\end\{table\}",
    re.DOTALL,
)

# Also match bare includegraphics of tables (appendix B style without full float sometimes)
BARE = re.compile(
    r"\\includegraphics\[[^\]]*\]\{illustrations/(tbl_p[^}]+)\.pdf\}"
)


def replace_in(text: str) -> tuple[str, int]:
    count = 0

    def repl_float(m: re.Match) -> str:
        nonlocal count
        key = m.group(1)
        if key not in MAP:
            return m.group(0)
        count += 1
        return f"\\input{{tables/{MAP[key]}}}"

    text = TABLE_FLOAT.sub(repl_float, text)

    def repl_bare(m: re.Match) -> str:
        nonlocal count
        key = m.group(1)
        if key not in MAP:
            return m.group(0)
        # Avoid double-replacing if already inside input
        count += 1
        return f"\\input{{tables/{MAP[key]}}}"

    # Only replace remaining bare includes
    text2 = BARE.sub(repl_bare, text)
    return text2, count


def main() -> None:
    total = 0
    for path in sorted(CHAPTERS.glob("*.tex")):
        raw = path.read_text(encoding="utf-8")
        new, n = replace_in(raw)
        # Clean leftover caption-only wrappers around inputs for appendix B
        new = re.sub(
            r"\\begin\{table\}\[[^\]]*\]\s*\\centering\s*"
            r"\\caption\{[^}]*\}\s*(?:\\label\{[^}]*\}\s*)?"
            r"(\\input\{tables/[^}]+\})\s*\\end\{table\}",
            r"\1",
            new,
        )
        if new != raw:
            path.write_text(new, encoding="utf-8")
            print(f"{path.name}: {n} replacements")
            total += n
        else:
            print(f"{path.name}: no change")
    # Verify no table clips remain
    left = []
    for path in CHAPTERS.glob("*.tex"):
        t = path.read_text(encoding="utf-8")
        for m in re.finditer(r"illustrations/tbl_p[^}]+\.pdf", t):
            left.append(f"{path.name}: {m.group(0)}")
    print("total replacements", total)
    print("remaining table clips:", len(left))
    for x in left:
        print(" ", x)


if __name__ == "__main__":
    main()
