from pathlib import Path

p = Path(__file__).resolve().parent / "chapters" / "04_requirements.tex"
t = p.read_text(encoding="utf-8")
repls = [
    (
        r"\begin{tabular}{@{}p{0.10\linewidth}p{0.32\linewidth}p{0.40\linewidth}p{0.10\linewidth}@{}}",
        r"\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.10\textwidth} >{\raggedright\arraybackslash}p{0.26\textwidth} L >{\raggedright\arraybackslash}p{0.12\textwidth}@{}}",
    ),
    (
        r"\begin{tabular}{@{}p{0.10\linewidth}p{0.28\linewidth}p{0.42\linewidth}p{0.12\linewidth}@{}}",
        r"\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.10\textwidth} >{\raggedright\arraybackslash}p{0.24\textwidth} L >{\raggedright\arraybackslash}p{0.14\textwidth}@{}}",
    ),
]
for a, b in repls:
    t = t.replace(a, b)
t = t.replace(r"\end{tabular}", r"\end{tabularx}")
p.write_text(t, encoding="utf-8")
print("beg", t.count(r"\begin{tabularx}"), "end", t.count(r"\end{tabularx}"))
