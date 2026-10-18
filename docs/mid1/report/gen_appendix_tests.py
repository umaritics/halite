#!/usr/bin/env python3
"""Generates chapters/appendix_test_cases.tex from the real test runners (names, not hand-typed).

Backend:  pytest --collect-only (test_graph_maintenance.py is collected, never executed, so no database is touched)
Frontend: vitest --reporter=json
Run from docs/mid1/report:  python3 gen_appendix_tests.py
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # repository root

def esc(s: str) -> str:
    s = s.replace("\\", r"\textbackslash{}")
    for a, b in [("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")]:
        s = s.replace(a, b)
    for a, b in [("\u2019", "'"), ("\u2018", "'"), ("\u201c", "``"), ("\u201d", "''"), ("\u2014", "---"), ("\u2013", "--"), ("\u2192", "$\\to$")]:
        s = s.replace(a, b)
    return s.replace("->", "$\\to$")

def backend():
    out = subprocess.run([str(ROOT / "backend/venv/bin/python"), "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
                         cwd=ROOT / "backend", capture_output=True, text=True).stdout
    files = {}
    for line in out.splitlines():
        if "::" not in line:
            continue
        f, *rest = line.split("::")
        files.setdefault(f.replace("tests/", ""), []).append(" > ".join(rest))
    return files

def frontend():
    out = subprocess.run(["npx", "vitest", "run", "--reporter=json"], cwd=ROOT / "frontend", capture_output=True, text=True).stdout
    d = json.loads(out[out.index("{"):])
    files = {}
    for f in sorted(d["testResults"], key=lambda x: x["name"]):
        name = f["name"].split("/src/test/")[1]
        files[name] = [a["fullName"] for a in f["assertionResults"]]
    return files

def section(title, files, label):
    n = sum(len(v) for v in files.values())
    lines = [rf"\section{{{title} ({n} tests)}}\label{{{label}}}", r"\small"]
    for f, names in files.items():
        lines.append(rf"\subsection*{{\texttt{{{esc(f)}}} ({len(names)})}}")
        lines.append(r"\begin{longtable}{p{0.05\textwidth}p{0.9\textwidth}}")
        for i, nm in enumerate(names, 1):
            lines.append(rf"{i} & {esc(nm)} \\")
        lines.append(r"\end{longtable}")
    lines.append(r"\normalsize")
    return "\n".join(lines)

b, f = backend(), frontend()
tex = "\n".join([
    r"\chapter{Detailed Test Cases}\label{app:tests}",
    "These lists are generated from the test runners by \\texttt{gen\\_appendix\\_tests.py}; they are not typed by hand. "
    "Test names describe the behaviour checked. The Neo4j repository-contract file is collected here and executed only in CI, against a real Neo4j service.",
    section("Backend tests", b, "app:tests-backend"),
    section("Frontend tests", f, "app:tests-frontend"),
])
(Path(__file__).parent / "chapters" / "appendix_test_cases.tex").write_text(tex + "\n", encoding="utf-8")
print("backend", sum(len(v) for v in b.values()), "frontend", sum(len(v) for v in f.values()))
