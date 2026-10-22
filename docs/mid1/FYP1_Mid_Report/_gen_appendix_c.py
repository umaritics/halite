#!/usr/bin/env python3
"""Generate compact Appendix C from the OCR draft list."""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "reports" / "chapters" / "appendix_C.tex"
DST = Path(__file__).resolve().parent / "chapters" / "appendix_C.tex"


def unescape_tex(s: str) -> str:
    return (
        s.replace("\\_", "_")
        .replace("\\%", "%")
        .replace("\\&", "&")
        .replace("\\#", "#")
        .replace("\\textgreater{}", ">")
        .replace("$>$", ">")
    )


def esc_path(s: str) -> str:
    """Escape for \\path{...} so long identifiers can wrap."""
    s = unescape_tex(s)
    # \path treats most punctuation as breakable; keep braces safe
    return s.replace("{", "\\{").replace("}", "\\}")


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    out.append("\\chapter{Detailed Test Cases}")
    out.append("")
    out.append(
        "These lists are generated from the test runners by "
        "\\texttt{gen\\_appendix\\_tests.py}; they are not typed by hand. "
        "Test names describe the behaviour checked. The Neo4j repository "
        "contract file is collected here and executed only in CI, against a real Neo4j service."
    )
    out.append("")

    section_re = re.compile(r"^(C\.\d)\s+(.+)$")
    file_re = re.compile(
        r"^([\w./\\]+?\.(?:py|test\.[jt]sx?))\s*(?:\((\d+)\))?\s*$"
    )
    num_re = re.compile(r"^(\d+)\s+(.+)$")

    current_file = None
    tests: list[str] = []

    def flush() -> None:
        nonlocal current_file, tests
        if current_file is None:
            return
        label = unescape_tex(current_file).replace("_", "\\_")
        out.append(f"\\subsubsection*{{\\texttt{{{label}}}}}")
        out.append(
            "\\begin{enumerate}[leftmargin=1.6em,itemsep=0.08em,topsep=0.2em,parsep=0pt,rightmargin=0pt]"
        )
        for t in tests:
            # \path from xurl allows breaks at underscores and dots
            out.append(f"\\item \\path{{{esc_path(t)}}}")
        out.append("\\end{enumerate}")
        out.append("")
        current_file = None
        tests = []

    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("\\chapter") or s.startswith("\\begin") or s.startswith("\\end"):
            continue
        plain = unescape_tex(s)
        if "These lists" in plain or "Test names" in plain or plain.startswith("The Neo4j"):
            continue

        m = section_re.match(plain)
        if m:
            flush()
            # Avoid "C.1 C.1 ..." in the TOC: appendix already numbers sections
            out.append(f"\\section{{{m.group(2)}}}")
            out.append("")
            continue

        m = file_re.match(plain)
        if m:
            flush()
            n = m.group(2)
            current_file = f"{m.group(1)}" + (f" ({n} tests)" if n else "")
            continue

        m = num_re.match(plain)
        if m and current_file is not None:
            tests.append(m.group(2).strip())
            continue

    flush()
    DST.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Wrote {DST} ({len(out)} lines)")


if __name__ == "__main__":
    main()
