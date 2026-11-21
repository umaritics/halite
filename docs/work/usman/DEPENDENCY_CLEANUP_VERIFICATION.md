# Dependency cleanup — verified review preparation

Source commit: `c2936e4` (PR #42). [Successful hosted run](https://github.com/umaritics/halite/actions/runs/44881901280).

All three CI jobs passed: **450 backend tests**, **279 frontend tests**, Ruff,
both frontend builds, real disposable Neo4j/PostgreSQL maintenance/session smoke,
and production-browser research/source highlighting verification. Broad backend
coverage remains **5,037 / 6,484 statements = 77.68%**; the 80% target remains open.

The pip transaction decreased from **89 to 66 selected distributions** against
the retained source baseline. The committed summary names all 23 no-longer-selected
packages. These are measured transaction counts, not an invented disk-size saving.
LangChain roots/core, LangSmith and python-docx are absent. Pandas 2.2.2, NumPy
1.26.4 and requests 2.34.2 preserve their actual baseline versions. Dotenv remains
transitive and the new real env-file Settings test passed.

The first run failed at pytest collection because retained verification scripts
import requests, previously supplied transitively by LangChain. It was declared
directly and the full workflow rerun successfully. No failed-run success claim.

Evidence: `evidence/phase12-dependencies/` contains the baseline, import audit,
raw pip resolution report, installed inventory, package delta, JUnit and job/hash
metadata. No local package install or heavy build was run. Owner review/merge
and the separate retirement PR remain pending; staging is unchanged.
