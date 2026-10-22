#!/usr/bin/env python3
"""Clean OCR residue from the mid1/reports draft into FYP1_Mid_Report chapters."""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "reports" / "chapters"
DST = Path(__file__).resolve().parent / "chapters"

KEEP_START = re.compile(
    r"^(\\section|\\subsection|\\subsubsection|\\chapter|\\begin\{|"
    r"\\clearpage|\\newpage|\\item|\\paragraph|\\\[|"
    r"\\Halite|\\label|\\ref|\\textbf\{Problem|\\textbf\{Implemented|"
    r"\\textbf\{Research|\\textbf\{Limitations)"
)

# Lines that look like OCR dumps of table cells / headers
OCR_LINE = re.compile(
    r"""^(?:
        \#\s |
        Pkg\s |
        Path\sContent |
        Component\sResponsibility |
        Method\sPath |
        Member\sCommits |
        Date\s\(2026\) |
        First\scommitted |
        Route\sPage |
        File\sTests |
        ID\s(?:Scenario|Requirement|Risk|Use\scase|Objective) |
        Signal\sWith\sphrase |
        System\sPrecision |
        Measure\sResult |
        Module\sState\snow |
        Period\sWork |
        Weeks?\s |
        Functional\srequirements\s*$ |
        Non-functional\srequirements\s*$ |
        Of\sthe\s35\sfunctional |
        \#\sTask\sOwner |
        \#\sPlanned\sfeature |
        \#\sObjective |
        --\s |
        Usman\sDone |
        Shahmeer\s |
        M0[2-9]\s |
        UC-0[0-9]\s |
        FR-[0-9] |
        NFR-[0-9\s] |
        T[0-9]{1,2}\s |
        R[0-9]{1,2}\s |
        A[0-9]\s |
        Met\s*$ |
        Partial\s*$ |
        Deferred\s*$ |
        Pass\s |
        Partly\s |
        Not\sstarted |
        Done(?:\s|\(|$) |
        Commits? |
        docs/ |
        GET\s/ |
        POST\s/ |
        DELETE/ |
        /app/ |
        backend/ |
        frontend/ |
        knowledge/ |
        \.github/ |
        react-force |
        Vitest, |
        Docker\sCompose |
        GitHub\sActions |
        Vercel\s |
        Groq-hosted |
        Phrasing\sand |
        Explicit\ssupersession |
        Model\ssays |
        New\srecord\sis |
        Source\sauthority |
        Same\spart\sand |
        Within\s30\sdays |
        The\sresult\sis\sclamped |
        Records\sprocessed |
        Model\sclassifications |
        Successful\smodel |
        Tokens\sused |
        Rate-limit |
        SUPERSEDES\sedges |
        Status:\sno_action |
        FAA-recorded |
        Edges\snot\sin |
        Baseline\s\( |
        Engine\s\(threshold |
        Graph\srepository |
        Settings,\sSidebar |
        Interactive\sconversational |
        Detect\ssuper |
        Human\sreview |
        Educational\sdiagnostic |
        Recurring-fault |
        Secure\smulti |
        Evaluation\sagainst |
        Deployment\swith |
        Conflict\sreview |
        API\sintegration |
        Automated\stests |
        GitHub\sActions |
        Review\saction |
        Frontend\stests |
        Backend\stests |
        Pull-request |
        Real\sgraph |
        Setup\son |
        Legacy\sscreen |
        Wrong\sdataset |
        No\shosted |
        Legacy\ssoftware |
        Conflict\smetrics |
        Missing\suniversity |
        Shared\sstaging |
        Model\squota |
        Unauthenticated |
        Addendum\sand |
        Removed\sfrom |
        Staging\sis |
        Daily\sbudget |
        Dataset\sprofile |
        CI\son\smain |
        Isolation\sby |
        This\sreport |
        Maintenance\sdomain |
        The\sfinal\sownership |
        8\s--\s10\sSep |
        15\sOct |
        16\sOct |
        17\sOct |
        18\sOct |
        2026-10- |
        Document\s23 |
        Actor: |
        Main\sflow: |
        Alternative: |
        Postcondition: |
        Precondition: |
        As\sUC-05 |
        Status\skey: |
        Check: |
        Measured: |
        Known\srisk: |
        ID\sRequirement |
        Acceptance\scheck |
        A\scorrected\srecord |
        Context\sis\slimited |
        Ranking\sis\sdeterministic |
        Each\sranked |
        The\sCopilot\sasks |
        Identifiers\sabsent |
        Copilot\ssessions |
        Candidates\scome |
        Each\sresult\sis |
        Contradicts\sand |
        Accept\sstores |
        Status,\sreview |
        FAA-format |
        Tail,\sdate |
        Text\sand\sidentifier |
        Rows\swith\sno |
        Assets\sappear |
        History\sfor |
        Typing\spart |
        After\singest |
        The\sgraph\sview |
        The\slegend |
        A\sCopilot\smessage |
        Structured\sCSV |
        Skipped\srows |
        test_ |
        Edge\slegend |
        Five\slabels |
        Routing\stests |
        No\sreviewer |
        Browser\sstorage |
        Deterministic\sranking |
        Evidence\slinks |
        Copilot\sasks |
        Citation\svalidation |
        Five\slabels |
        Status\sand\snote |
        Case-based |
        Learner\s |
        Feedback\slinked |
        Store\straining |
        Display\srecorded |
        Identify\srepeated |
        Filters\sby |
        Distinguish\sdescriptive |
        Failed\sexternal |
        Citations\sresolve |
        Usability\smeasured |
        Independent\ssetup |
        Review\schanges |
        Bounded\sretries |
        No\suser\sstudy |
        Setup\sguide |
        No\sactor |
        Summary\sof\sfunctional |
        Close\sthe\sopen |
        Measure\slive |
        Embedding-based |
        Diagnostic\sevaluation |
        Roles\sand |
        Server-side |
        Analysis\sof\sthe |
        Quality:\slint |
        Usman,\sUmar |
        Umar,\sUsman |
        Usman,\sShahmeer |
        Umar,\sShahmeer |
        Shahmeer,\sUsman |
        Each\shas\sa |
        Measured\snumbers |
        Runs\son\sthe |
        Metrics\sreproducible |
        Requests\scarry |
        Sessions\ssurvive |
        Coverage\sshown |
        CI\sreports |
        One-shot\sdiagnosis |
        Multi-turn\scopilot |
        Nodes\sand\sedges |
        Deployed\scommit |
        Review\squeue |
        Detected\scorrections |
        Knowledge\sGraph |
        Ingest:\s |
        Assets:\sthe |
        Quick\sdiagnose |
        The\smodel's |
        Asset\sHistory |
        Failure\scase |
        Service\sRecords |
        Maintenance\sproof |
        Mid-I\sengineering |
        Frontend\sS1 |
        Confidence\sand |
        CSV\supload |
        Proposed\sembedding |
        Approximately\s60 |
        Overall\snine |
        Proposal\spanel |
        Clarified |
        Not\sapplicable |
        \d+\sInteractive |
        \d+\sDetect |
        \d+\sHuman |
        \d+\sEducational |
        \d+\sRecurring |
        \d+\sSecure |
        \d+\sEvaluation |
        \d+\sDeployment |
        \d+\sConflict |
        \d+\sAPI |
        \d+\sAutomated |
        \d+\sGitHub |
        \d+\sClose |
        \d+\sMeasure |
        \d+\sEmbedding |
        \d+\sDiagnostic |
        \d+\sRoles |
        \d+\sServer |
        \d+\sAnalysis |
        \d+\sQuality |
        \d+\sof\s3 |
        \d+\s/\s\d+ |
        \d{1,3}\s*$ |
        0\.\d+ |
        \[UNVERIFIED
    )""",
    re.VERBOSE,
)

NARRATIVE_OK = re.compile(
    r"^(The |This |Halite |Maintenance |Given |Development |Selected |"
    r"Planned |Deliverables |Objective\.|Member |Commit |Generative |"
    r"No personal |Hybrid |Validated: |To show |An earlier |How far |"
    r"Every |At commit |We test |For the |Requirement |Status key|"
    r"NFR-|Success |A\. |B\. |C\. |D\. |E\. |F\. |G\. |"
    r"M02 |M03 |M04 |M05 |M06 |"
    r"UC-03 |UC-04 |UC-05 |UC-06 |UC-07 |UC-08 |UC-09 |"
    r"Actor:|Runtime |Domain |Source\.|Ground |Ingest |Status values|"
    r"Known data|Figure |In outline|GET /api/health|"
    r"Context\.|Ranking\.|Copilot\.|Candidates\.|Classification\.|"
    r"Confidence\.|Routing\.|Ingest never|The cascade|with \$|"
    r"sfleet|score\(c\)|returns counts|A row needs|"
    r"These lists|C\.\d|Appendix |Dates follow|A deployed|"
    r"Nothing is|The proposal|Iteration |Tasks are|"
    r"To avoid|The staging|Each week|Of the 115|"
    r"The evaluated|The initial|The FYP Committee|"
    r"Three team|Supervisor |Dated progress|"
    r"One turn|Frontend routes|"
    r"\\)"
)


def collapse_blank(lines: list[str]) -> list[str]:
    out: list[str] = []
    blank = 0
    for line in lines:
        if line.strip() == "":
            blank += 1
            if blank <= 1:
                out.append("")
        else:
            blank = 0
            out.append(line.rstrip())
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    out.append("")
    return out


def fix_hyphenation(text: str) -> str:
    fixes = [
        ("unveri- fied", "unverified"),
        ("con- firmed", "confirmed"),
        ("serverside", "server-side"),
        ("midreport", "mid-report"),
        ("repositorycontract", "repository contract"),
        ("perday", "per-day"),
        ("gen\\_appendix\\_tests.py", "gen\\_appendix\\_tests.py"),
        ("partiallysupersedes", "partially\\_supersedes"),
        ("analysis\\_ state", "analysis\\_state"),
        ("UC- 02", "UC-02"),
        ("UC- 08", "UC-08"),
        ("NFR- 02", "NFR-02"),
        ("NFR- 03", "NFR-03"),
        ("NFR- 06", "NFR-06"),
        ("NFR- 07", "NFR-07"),
        ("NFR- 08", "NFR-08"),
        ("NFR- 09", "NFR-09"),
        ("NFR- 10", "NFR-10"),
        ("DELETE/api/graph/reset", "DELETE /api/graph/reset"),
        ("DELETE/api/graph/ reset", "DELETE /api/graph/reset"),
        ("POST /api/maintenance/ diagnose", "POST /api/maintenance/diagnose"),
        ("POST /api/maintenance/ copilot/turn", "POST /api/maintenance/copilot/turn"),
        ("GET/maintenance/", "GET /maintenance/"),
        ("POST/maintenance/", "POST /maintenance/"),
        ("GET /review-queue", "GET /api/review-queue"),
        ("speci- fication", "specification"),
        ("heldout", "held-out"),
        ("15\\_report\\_mid1\\_addendum.mdHalite", "15\\_report\\_mid1\\_addendum.md --- Halite"),
        ("20\\_analysis\\_cost\\_report.mdConflict", "20\\_analysis\\_cost\\_report.md --- Conflict"),
        ("docs/mid1/23\\_single\\_aircraft\\_ analysis\\_evidence.md",
         "docs/mid1/23\\_single\\_aircraft\\_analysis\\_evidence.md"),
        ("\#14 open", "\\#14 open"),
        ("PRs \\#5--\\#7", "PRs \\#5--\\#7"),
    ]
    for a, b in fixes:
        text = text.replace(a, b)
    # join broken mid-word hyphenations like "did\n\nnot"
    text = re.sub(r"(\w)-\n\n(\w)", r"\1\2", text)
    return text


def rewrite_illustration(block: str) -> str:
    """Turn captionof+includegraphics center blocks into HaliteFigure/TableClip."""
    m = re.search(
        r"\\includegraphics\[.*?\]\{(illustrations/[^}]+)\}",
        block,
    )
    if not m:
        return block
    path = m.group(1)
    cap_m = re.search(r"\\captionof\{(figure|table)\}\{((?:[^{}]|\{[^{}]*\})*)\}", block)
    if not cap_m:
        # figure without captionof — keep as figure env with empty? keep includegraphics
        return (
            f"\\begin{{figure}}[htbp]\n\\centering\n"
            f"\\includegraphics[width=0.92\\linewidth,height=0.58\\textheight,keepaspectratio]{{{path}}}\n"
            f"\\end{{figure}}\n"
        )
    kind, caption = cap_m.group(1), cap_m.group(2)
    if kind == "table":
        return (
            f"\\begin{{table}}[htbp]\n\\centering\n"
            f"\\caption{{{caption}}}\n"
            f"\\includegraphics[width=0.98\\linewidth,height=0.62\\textheight,keepaspectratio]{{{path}}}\n"
            f"\\end{{table}}\n"
        )
    return (
        f"\\begin{{figure}}[htbp]\n\\centering\n"
        f"\\includegraphics[width=0.92\\linewidth,height=0.58\\textheight,keepaspectratio]{{{path}}}\n"
        f"\\caption{{{caption}}}\n"
        f"\\end{{figure}}\n"
    )


def clean_file(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = fix_hyphenation(text)

    # Remove clearpage before figures (we float them)
    text = re.sub(r"\\clearpage\\noindent\s*", "", text)
    text = re.sub(r"\\noindent\s*", "", text)

    # Replace center illustration blocks
    def repl_center(m: re.Match) -> str:
        return rewrite_illustration(m.group(0))

    text = re.sub(
        r"\\begin\{center\}.*?\\end\{center\}",
        repl_center,
        text,
        flags=re.DOTALL,
    )

    lines = text.split("\n")
    out: list[str] = []
    i = 0
    in_env = 0
    skip_ocr = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # track environments
        if re.search(r"\\begin\{", stripped):
            in_env += len(re.findall(r"\\begin\{", stripped))
        if re.search(r"\\end\{", stripped):
            in_env -= len(re.findall(r"\\end\{", stripped))

        # After a table/figure float ends, enter OCR-skip mode until structure
        if stripped.startswith(r"\end{table}") or stripped.startswith(r"\end{figure}"):
            out.append(line)
            skip_ocr = True
            i += 1
            continue

        if skip_ocr:
            if stripped == "":
                i += 1
                continue
            if KEEP_START.match(stripped) or (
                NARRATIVE_OK.match(stripped) and not OCR_LINE.match(stripped)
            ):
                skip_ocr = False
                # fall through to emit
            elif OCR_LINE.match(stripped) or (
                len(stripped) < 120
                and not stripped.startswith("\\")
                and not stripped.startswith("%")
                and (
                    re.match(r"^[\w./#\-→,\s()]+$", stripped)
                    or "Done" in stripped
                    or "Met" == stripped
                    or "Partial" == stripped
                )
            ):
                i += 1
                continue
            else:
                # ambiguous: if it looks like prose paragraph, keep
                if len(stripped) > 80 and " " in stripped and not OCR_LINE.match(stripped):
                    skip_ocr = False
                else:
                    i += 1
                    continue

        # Compact one-item itemize blocks: leave as-is (cleaner later)
        out.append(line)
        i += 1

    text = "\n".join(collapse_blank(out))

    # Merge split itemize singletons into one list where consecutive
    text = re.sub(
        r"\\begin\{itemize\}\\item\s*(.*?)\\end\{itemize\}\n+\\begin\{itemize\}\\item\s*",
        r"\\begin{itemize}\n\\item \1\n\\item ",
        text,
    )
    # Repeated merges
    for _ in range(12):
        text2 = re.sub(
            r"(\\item [^\n]+)\n\\end\{itemize\}\n+\\begin\{itemize\}\n\\item ",
            r"\1\n\\item ",
            text,
        )
        if text2 == text:
            break
        text = text2

    # Expand remaining single-line itemize
    text = re.sub(
        r"\\begin\{itemize\}\\item\s*(.*?)\\end\{itemize\}",
        r"\\begin{itemize}\n\\item \1\n\\end{itemize}",
        text,
    )

    return text


def convert_appendix_c(text: str) -> str:
    """Turn OCR test dump into compact enumerate/description style."""
    text = fix_hyphenation(text)
    lines = [ln.rstrip() for ln in text.split("\n")]
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

    current_file = None
    tests: list[str] = []

    def flush():
        nonlocal current_file, tests
        if current_file is None:
            return
        out.append(f"\\subsubsection*{{{current_file}}}")
        out.append("\\begin{enumerate}[leftmargin=1.8em,itemsep=0.05em,topsep=0.2em]")
        for t in tests:
            out.append(f"\\item \\texttt{{{t}}}")
        out.append("\\end{enumerate}")
        out.append("")
        current_file = None
        tests = []

    section_pat = re.compile(r"^(C\.\d)\s+(.+)$")
    file_pat = re.compile(r"^([\w./]+\.py)\s*\((\d+)\)\s*$")
    file_pat2 = re.compile(r"^([\w./]+\.test\.[jt]sx?)\s*\((\d+)\)\s*$")
    num_test = re.compile(r"^(\d+)\s+(.+)$")

    i = 0
    # skip original chapter header
    while i < len(lines) and not lines[i].startswith("\\chapter"):
        i += 1
    i += 1

    while i < len(lines):
        s = lines[i].strip()
        i += 1
        if not s or s.startswith("%"):
            continue
        if s.startswith("\\"):
            continue
        m = section_pat.match(s)
        if m:
            flush()
            out.append(f"\\section{{{m.group(1)} {m.group(2)}}}")
            out.append("")
            continue
        m = file_pat.match(s) or file_pat2.match(s)
        if m:
            flush()
            current_file = f"{m.group(1)} ({m.group(2)} tests)"
            continue
        # bare filename lines like test_api_copilot.py (10)
        if ".py" in s or ".test." in s:
            flush()
            current_file = s
            continue
        m = num_test.match(s)
        if m and current_file is not None:
            name = m.group(2).replace("_", "\\_").replace(">", "\\textgreater{}")
            tests.append(name)
            continue
        # prose lines in appendix C intro already handled
        if "These lists" in s or "Test names" in s or "Neo4j" in s:
            continue
    flush()
    return "\n".join(out) + "\n"


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    for path in sorted(SRC.glob("*.tex")):
        raw = path.read_text(encoding="utf-8")
        if path.name == "appendix_C.tex":
            cleaned = convert_appendix_c(raw)
        else:
            cleaned = clean_file(raw)
        (DST / path.name).write_text(cleaned, encoding="utf-8")
        print(f"Wrote {path.name} ({len(cleaned.splitlines())} lines)")


if __name__ == "__main__":
    main()
