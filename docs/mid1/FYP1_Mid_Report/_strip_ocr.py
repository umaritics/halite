#!/usr/bin/env python3
"""Second pass: strip OCR residue after figure/table floats."""

from __future__ import annotations

import re
from pathlib import Path

DST = Path(__file__).resolve().parent / "chapters"

STRUCT = re.compile(
    r"^("
    r"\\(chapter|section|subsection|subsubsection|begin|end|label|caption|includegraphics|"
    r"item|paragraph|textbf|textit|texttt|emph|cite|ref|url|clearpage|newpage|\[)"
    r"|[A-Z]\.\s"  # success criteria A. B.
    r"|Halite |Given |Maintenance |This |The |To |We |At |Every |Success |"
    r"Requirement |Status key|Actor:|Main flow|As UC-|Runtime |Domain |"
    r"Source\.|Ground |Ingest |Known |Figure |In outline|GET /api/health |"
    r"Context\.|Ranking\.|Copilot\.|Candidates\.|Classification\.|Confidence\.|Routing\.|"
    r"with H|sfleet|returns counts|Nothing |Dates |A deployed|These lists|"
    r"Of the 115|The evaluated|The initial|The FYP|Three team|Supervisor |"
    r"Dated |One turn|Frontend routes|Functional requirements|"
    r"Non-functional|Summary of|NFR-0|Validated:|To show|An earlier|How far|"
    r"Member |Commit |Generative|No personal|Hybrid |For the|UC-0[3-9] |"
    r"M0[2-6] |Deliver a |Objective\.|Selected |Planned |Development |"
    r"Computerised|Matching |Embedding|Graph retrieval|Case-based|"
    r"Existing |How can|It is a|These are|No panel|The committee|"
    r"Pkg |-- Diagnostic|-- Knowledge"  # keep? no strip these as OCR
    r")"
)

# After float: drop lines until structure/prose
PROSE = re.compile(
    r"^[A-Z][a-z].{40,}"  # starts with capital, reasonably long
)


def strip_file(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    skipping = False
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()

        if s in (r"\end{table}", r"\end{figure}"):
            out.append(line)
            skipping = True
            i += 1
            continue

        if skipping:
            if s == "":
                i += 1
                continue
            # stop skipping on LaTeX structure or real prose
            if s.startswith("\\") and not s.startswith("\\#"):
                skipping = False
            elif PROSE.match(s) and not re.match(r"^\d+\s", s):
                skipping = False
            elif re.match(r"^[A-G]\.\s", s):
                skipping = False
            elif s.startswith("M0") and ". " in s and len(s) > 40:
                skipping = False
            elif s.startswith("UC-0") and len(s) > 20 and not s.startswith("UC-08 Review"):
                # detailed use case headers like "UC-03 View aircraft history"
                if re.match(r"^UC-0\d\s+[A-Z]", s):
                    skipping = False
                else:
                    i += 1
                    continue
            elif s.startswith("NFR-0") and ":" in s:
                skipping = False
            else:
                i += 1
                continue

        out.append(line)
        i += 1

    # collapse blank lines
    cleaned: list[str] = []
    blank = 0
    for line in out:
        if line.strip() == "":
            blank += 1
            if blank <= 1:
                cleaned.append("")
        else:
            blank = 0
            cleaned.append(line.rstrip())

    text = "\n".join(cleaned)

    # join accidental paragraph breaks: "did\n\nnot" / "mes-\n\nsage"
    text = re.sub(r"(\w)-\n\n(\w)", r"\1\2", text)
    text = re.sub(r"\bdid\n\nnot\b", "did not", text)
    text = re.sub(r"\beach\n\nmes\n\nsage\b", "each message", text)
    text = re.sub(r"\bmes\n\nsage\b", "message", text)
    text = re.sub(r"\bIt\n\nreturns\b", "It returns", text)
    text = re.sub(r"\bOnly records\n\nwith\b", "Only records with", text)
    text = re.sub(r"\ba\n\ndifferent\b", "a different", text)
    text = re.sub(r"\boperations\n\ntoken\b", "operations token", text)
    text = re.sub(r"\bcon\n\nflict\b", "conflict", text)
    text = re.sub(r"\bselected\n\nfeatures\b", "selected features", text)
    text = re.sub(
        r"\ban asset history\n\n\n*browser\b",
        "an asset history browser",
        text,
        flags=re.IGNORECASE,
    )

    # merge fragmented itemize
    for _ in range(20):
        nxt = re.sub(
            r"(\\item .+?)\n\\end\{itemize\}\n+\\begin\{itemize\}\n(\\item )",
            r"\1\n\2",
            text,
            flags=re.DOTALL,
        )
        # simpler line-based merge
        nxt = re.sub(
            r"(\\item [^\n]+)\n\\end\{itemize\}\n+\\begin\{itemize\}\n\\item ",
            r"\1\n\\item ",
            text,
        )
        if nxt == text:
            break
        text = nxt

    return text.strip() + "\n"


def main() -> None:
    for path in sorted(DST.glob("*.tex")):
        raw = path.read_text(encoding="utf-8")
        cleaned = strip_file(raw)
        path.write_text(cleaned, encoding="utf-8")
        print(f"stripped {path.name}")


if __name__ == "__main__":
    main()
