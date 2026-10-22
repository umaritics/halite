#!/usr/bin/env python3
"""Generate native LaTeX tables to replace broken PDF clips."""
from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent / "tables"
OUT.mkdir(exist_ok=True)


def w(name: str, body: str) -> None:
    (OUT / name).write_text(body.strip() + "\n", encoding="utf-8")
    print("wrote", name)


def main() -> None:
    w(
        "tab_objectives.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Project objectives and their status at FYP-1 Mid}
\label{tab:objectives}
\small
\begin{tabularx}{\textwidth}{@{}c >{\raggedright\arraybackslash}p{0.28\textwidth} >{\raggedright\arraybackslash}p{0.16\textwidth} L@{}}
\toprule
\# & Objective & Status & Measurable check \\
\midrule
1 & Structured maintenance knowledge graph & Done (Mid scope) & 2{,}079 records and 118 aircraft in Neo4j; relationships ABOUT, PRECEDED\_BY, SUPERSEDES \\
2 & Record ingestion and normalisation & Partial & CSV ingest with explicit skip counts and duplicate safety; no free-text extraction \\
3 & Asset-aware historical retrieval & Done & Retrieval bounded to aircraft history plus a capped fleet scan \\
4 & Semantic retrieval & Not started & Planned for FYP-1 Final; not claimed \\
5 & Evidence-aware diagnostic ranking & Done (heuristic) & Deterministic, documented weights; scores are not probabilities \\
6 & Interactive conversational investigation & Done (basic) & Multi-turn Copilot with carried case state \\
7 & Detect superseded and contradictory findings & Done & Five-label classifier with confidence and routing \\
8 & Human review for uncertain decisions & Done & Review queue with accept and reject; notes stored \\
9 & Educational diagnostic scenarios & Not started & Training module is FYP-2 \\
10 & Recurring-fault and fleet analytics & Not started & FYP-2 \\
11 & Secure multi-user SaaS application & Not started & No authentication yet \\
12 & Evaluation against controlled baselines & Partial & Historical conflict evaluation exists; diagnostic baselines not yet run \\
13 & Deployment with automated testing and CI/CD & Done & GitHub Actions on every push; CI-gated staging deploy \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_scope_modules.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Scope of the nine proposal modules at FYP-1 Mid}
\label{tab:scope-modules}
\small
\begin{tabularx}{\textwidth}{@{}c >{\raggedright\arraybackslash}p{0.22\textwidth} c L@{}}
\toprule
ID & Module & Mid scope & What is delivered, or why not \\
\midrule
M01 & Workspace and identity & Out & No login, roles or tenancy yet; batch analysis protected only by an operations token \\
M02 & Assets & In & Fleet list, per-aircraft dated history, fleet-wide record search with filters \\
M03 & Knowledge graph & In & Graph in Neo4j; interactive 3D view of one aircraft's stored subgraph \\
M04 & Diagnostics & In & One-shot diagnose and multi-turn Copilot; ranking and citation validation \\
M05 & Conflict intelligence & In & Candidate pairing, classification, confidence, routing, review queue, corrections view \\
M06 & Report intelligence & Partial & CSV upload and single-record entry; no extraction from documents \\
M07 & Technician academy & Out & FYP-2 \\
M08 & Analytics & Out & FYP-2 \\
M09 & Administration & Out & FYP-2; only a read-only system-status page exists \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_stakeholders.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Stakeholders and what each needs}
\label{tab:stakeholders}
\small
\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.22\textwidth} L L@{}}
\toprule
Stakeholder & Role in the system & Need \\
\midrule
Maintenance technician & Reads aircraft history, enters symptoms, opens cited records & Find relevant past cases quickly; avoid repeating a failed repair \\
Maintenance supervisor & Reviews records the system could not resolve & See both records and the reasoning; accept or reject with a note \\
Technician (uploading reports) & Loads new records from a CSV or a single entry & Know exactly how many records were created, skipped or duplicated \\
Project supervisor (evaluator) & Assesses progress & Demonstrable claims that match the code and tests \\
\bottomrule
\end{tabularx}
\end{table}

{\footnotesize Only the technician and maintenance-supervisor roles are exercised in this iteration, and they are not yet separated by authentication.\par}
""",
    )

    w(
        "tab_retrieval_compare.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Architectural comparison of retrieval approaches}
\label{tab:retrieval-compare}
\footnotesize
\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.16\textwidth} >{\raggedright\arraybackslash}p{0.12\textwidth} >{\raggedright\arraybackslash}p{0.14\textwidth} >{\raggedright\arraybackslash}p{0.14\textwidth} L@{}}
\toprule
Capability & Keyword & Semantic RAG & Graph RAG & Halite (at Mid) \\
\midrule
Natural-language input & Limited & Yes & Yes & Yes (lexical matching only) \\
Asset-specific context & Manual & Filter & Graph & Graph (aircraft history plus capped fleet scan) \\
Historical corrections & No & Not intrinsic & Possible & Explicit SUPERSEDES edges; superseded records down-weighted \\
Ranked hypotheses & No & Generated text & Generated text & Deterministic, documented heuristic \\
Evidence checking & Manual & Partial & Partial & Every cited record identifier checked against the graph \\
Uncertainty handling & No & Model-based & Model-based & Heuristic labelled not-a-probability; unanalysed state shown; model failure reported \\
Semantic similarity & No & Yes & Yes & Not implemented (planned) \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_tech_challenges.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Technical challenges met in this iteration}
\label{tab:tech-challenges}
\small
\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.22\textwidth} L@{}}
\toprule
Challenge & What we found and did \\
\midrule
Query fan-out & The first service-record view issued one request per aircraft (1+118 on load). It now loads two page-initiated calls; the assets list is one aggregation query ($\approx$1.0\,s on staging). \\
Cost of conflict analysis & On the real corpus, 1{,}835 of 2{,}079 records have a candidate. Five-vote classification projects to 9{,}175 model requests vs a free-tier limit of 1{,}000/day. An opt-in cascade projects to 2{,}062--5{,}155 requests. Full-corpus token cost is not yet measured. \\
Model instability & On one pair, two models gave different labels. We record method, model and votes for every classification and do not tune thresholds to look better. \\
Legacy placeholder data & Early ingest carried confidence 1.0 without analysis. The API now reports such untouched values as unanalysed. \\
Provider limits & HTTP 429 is normal (27 on a 13-record run). Retries are bounded; a daily budget stops runs cleanly; a missing live model fails closed. \\
Empty model output & Staging fresh diagnoses returned no explanation text. Empty model output is an explicit HTTP 503, never a blank success. \\
Dense graphs & The largest aircraft produces a 305-edge subgraph; the interface shows one aircraft at a time. \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_findings_design.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{How findings shaped the design}
\label{tab:findings-design}
\small
\begin{tabularx}{\textwidth}{@{}L L@{}}
\toprule
Finding & Design decision \\
\midrule
Corrections change the component in 65.2\% of FAA-recorded pairs & Represent SUPERSEDES explicitly; down-weight superseded records in ranking (factor 0.3); show the corrector next to a corrected record \\
Exhaustive pairing is quadratic & Only compare within the same aircraft, only with earlier records, only when at least one matching signal exists, at most 25 candidates \\
Models disagree and fail & Ranking is deterministic and needs no model; the model only phrases it; failures are reported, not hidden \\
Model-generated identifiers can be invented & Every identifier in the text is checked against the graph; unmatched ones are marked unverified \\
Analysis is expensive and rate-limited & Ingest stores records as unanalysed; analysis is a separate, resumable, budgeted step; the interface shows ``Not analysed'' honestly \\
Labels come free from the data & Use FAA-recorded supplemental pairs as ground truth rather than hand labels \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_work_packages.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Work packages of Iteration 1}
\label{tab:work-packages}
\small
\begin{tabularx}{\textwidth}{@{}c L >{\raggedright\arraybackslash}p{0.16\textwidth} >{\raggedright\arraybackslash}p{0.16\textwidth}@{}}
\toprule
Pkg & Work package & Owner & Status \\
\midrule
S1 & Maintenance-only navigation; isolate legacy screens & Shahmeer & Done \\
S2 & Asset list and dated history & Shahmeer & Done \\
S3 & Diagnostic workspace states and safety & Shahmeer & Done \\
S4 & Evidence navigation and review UI & Shahmeer & Done \\
S5 & Frontend tests and build quality & Shahmeer & Done; no linter yet \\
U1 & Audit of existing diagnostics & Umar & Done \\
U2 & Real-data graph retrieval (bounded) & Umar & Done \\
U3 & Deterministic fault ranking & Umar & Done \\
U4 & Citation validation and model boundary & Umar & Done \\
U5 & Diagnostic backend tests & Umar & Done \\
A1 & Data and environment baseline & Usman & Done \\
A2 & Maintenance APIs and conflict workflow & Usman & Done \\
A3 & GitHub Actions and repository health & Usman & Done \\
A4 & Backend wiring and documentation & Usman & Done \\
-- & Diagnostic Copilot, confidence/corrections, cost cascade (PRs \#5--\#7) & Usman & Done \\
-- & Knowledge graph view, CSV upload, evidence refresh (PRs \#9--\#13) & Shahmeer & Done; \#14 open at writing \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_progress.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Planned Iteration 1 features against delivered state}
\label{tab:progress}
\small
\begin{tabularx}{\textwidth}{@{}c >{\raggedright\arraybackslash}p{0.24\textwidth} >{\raggedright\arraybackslash}p{0.16\textwidth} L@{}}
\toprule
\# & Planned feature & Status & Delivered state and evidence \\
\midrule
1 & Maintenance-focused UI & Done & Sidebar lists only maintenance screens; legacy URLs redirect \\
2 & Asset history browser & Done & 118 aircraft; dated history with FAA identifiers \\
3 & Live knowledge graph & Done & Neo4j graph; interactive 3D view of one aircraft's subgraph \\
4 & Symptom-based diagnostic input & Done & One-shot diagnose and multi-turn Copilot \\
5 & Historical evidence retrieval & Done (lexical) & Bounded retrieval; semantic retrieval not built \\
6 & Ranked investigation suggestions & Done (heuristic) & Deterministic ranking with documented weights \\
7 & Conflict review capability & Done & Review queue, corrections view \\
8 & API integration & Done & Axios client to FastAPI routes; contract tests \\
9 & Automated tests & Done & 194 backend and 171 frontend tests pass in CI \\
10 & GitHub Actions CI/CD & Done & CI on designated branches and PRs; CI-gated staging deploy \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_commits_phase.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Commits by phase (counts at \texttt{36a98a3})}
\label{tab:commits-phase}
\small
\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.22\textwidth} c L@{}}
\toprule
Dates (2026) & Commits & What the work was \\
\midrule
11 Jul -- 18 Aug & 9 & Earlier software-engineering prototype of the same stack (later set aside; frozen legacy with regression tests) \\
8 -- 10 Sep & 29 & Maintenance proof of concept: domain registry, FAA acquisition, conflict engine, evaluation harness, first maintenance screens \\
15 -- 18 Oct & 77 & Mid-I integration: contract freeze, frontend rework, copilot, confidence/corrections, cost cascade, CI on main, evidence \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_usecases.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Use cases in scope at FYP-1 Mid}
\label{tab:usecases}
\small
\begin{tabularx}{\textwidth}{@{}c >{\raggedright\arraybackslash}p{0.26\textwidth} >{\raggedright\arraybackslash}p{0.18\textwidth} L@{}}
\toprule
ID & Use case & Primary actor & Entry point in the application \\
\midrule
UC-03 & View aircraft history & Technician & Assets, Asset History, Service Records \\
UC-04 & Upload report & Technician & Ingest (CSV upload, single record) \\
UC-05 & Start diagnosis & Technician & Diagnostics, Quick diagnose \\
UC-06 & Ask follow-up & Technician & Diagnostics, Copilot \\
UC-07 & Inspect evidence & Technician & Evidence links from Diagnostics and the review queue \\
UC-08 & Review conflict & Maintenance supervisor & Review Queue, Detected corrections \\
UC-09 & Explore graph & Technician & Knowledge Graph \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_traceability.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Traceability of central requirements}
\label{tab:traceability}
\small
\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.12\textwidth} L L >{\raggedright\arraybackslash}p{0.22\textwidth}@{}}
\toprule
FR & Design element & Implementation & Tests \\
\midrule
FR-06, 08 & Asset history API and page & \texttt{maintenance.py}, \texttt{AssetHistory.jsx} & \texttt{test\_api\_maintenance}; AssetHistory.test (12) \\
FR-13 & Graph schema, ingest & \texttt{maintenance\_agent.py}, \texttt{queries.py} & \texttt{test\_maintenance\_agent} (10) \\
FR-14, 15 & Graph view & \texttt{Graph.jsx}, \texttt{graphScope.js} & Graph.test (18), graphScope.test (10) \\
FR-17--19 & Retrieval and ranking & \texttt{diagnostic\_retrieval.py} & \texttt{test\_diagnostic\_retrieval} (26) \\
FR-21 & Citation validation & \texttt{citation\_validation.py} & \texttt{test\_citation\_validation} (6) \\
FR-23--25 & Conflict engine & \texttt{conflict\_engine.py} & \texttt{test\_conflict\_engine} (32), cascade (11) \\
FR-26 & Review actions & \texttt{maintenance.py}, \texttt{ReviewQueue.jsx} & ReviewQueue.test (18) \\
FR-09, 12 & CSV upload & \texttt{MaintenanceIngest.jsx} & MaintenanceIngest.test (17) \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_components.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Components and responsibilities}
\label{tab:components}
\small
\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.22\textwidth} L >{\raggedright\arraybackslash}p{0.28\textwidth}@{}}
\toprule
Component & Responsibility & Main files \\
\midrule
React application & Pages for assets, history, service records, diagnostics, review, graph, ingest; every failure state shown honestly & \texttt{frontend/src/pages}, \texttt{components}, \texttt{utils} \\
API client & One Axios instance and the functions for every endpoint & \texttt{frontend/src/api/client.js} \\
API routes & HTTP contracts, validation, controlled errors (404, 409, 422, 503) & \texttt{backend/api/routes} \\
Ingest agent & Validated, idempotent loading of FAA records; explicit skip counts & \texttt{agents/maintenance\_agent.py} \\
Retrieval and ranking & Bounded graph context; deterministic ranking; copilot context and ranking delta & \texttt{services/diagnostic\_retrieval.py} \\
Citation validation & Extract FAA-shaped identifiers and check them against the graph & \texttt{services/citation\_validation.py} \\
Conflict engine & Candidate pairing, classification, adjudication, confidence, routing & \texttt{services/conflict\_engine.py}, \texttt{conflict\_screen.py} \\
Analysis state and budget & Honest unanalysed state; per-day request and token budget & \texttt{analysis\_state.py}, \texttt{analysis\_budget.py} \\
Model client & Calls Groq; rejects empty content; bounded retries & \texttt{services/groq\_service.py} \\
Graph repository & One query layer over Neo4j or the in-memory store & \texttt{graph/queries.py}, \texttt{schema.py} \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_decisions.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Selected architecture and process decisions}
\label{tab:decisions}
\small
\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.30\textwidth} L@{}}
\toprule
Decision (date) & Rationale \\
\midrule
Maintenance-only frontend (16 Oct) & The product is maintenance diagnostics; legacy software screens stay in the repository but are unreachable \\
Frontend reflects backend outputs (16 Oct) & The interface may add labels and warnings but must never hide, alter or invent a backend value \\
Review actions are server-confirmed (16 Oct) & Accept/reject change real data; the screen updates only after the server confirms \\
Centralised staging and CI-gated release (16 Oct) & One shared staging API; only a commit that passed full CI on main is deployed, with recorded rollback \\
Honest analysis state (17 Oct) & Analysis state is stored separately from confidence; ``unscored'' is never shown as a confident result \\
Fleet-wide paginated records (17 Oct) & Replaced a 119-request fan-out with one paginated, filterable endpoint \\
Opt-in cost cascade (17 Oct) & Pre-registered, off by default: deterministic text screen before the model, then adaptive voting \\
Diagnostic copilot scope waiver (16 Oct) & Limited ownership exception so the copilot could be built across route, retrieval and UI \\
Graph shows one aircraft (17 Oct) & Whole graph is too dense; one aircraft's stored subgraph is readable and every drawn edge is stored \\
Knowledge bank and agent protocol (16 Oct) & Versioned memory of context, flows and decisions updated in the same change as the code \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_design_evolution.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Design as proposed against design as built}
\label{tab:design-evolution}
\small
\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.18\textwidth} L L@{}}
\toprule
Aspect & Proposal & Built at Mid, and why \\
\midrule
Retrieval & Graph-constrained plus embedding-based hybrid & Graph-bounded with lexical (Jaccard) similarity; embeddings deferred so the baseline is measured first \\
Ranking & Hybrid evidence score with a historical correction penalty & Deterministic: recency and similarity weights, factor 0.3 for superseded records \\
Conflict engine & Five-label classifier with human review & As proposed; plus stored analysis state, daily budget, and opt-in cost cascade after measuring 9{,}175 projected requests \\
Tenancy and identity & PostgreSQL, organisations, roles & Not built; reviewer identity is therefore not recorded \\
Sessions & Server-side diagnostic session storage & Client-side state only; the server is stateless \\
Interface & Chat-centred workspace & Asset-first workspace with a Copilot tab; one-shot diagnose kept as the stable contract \\
Corpus & About 60 airframes & 118 aircraft, because every aircraft with a ground-truth pair is kept first \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_tools.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{External components and tools}
\label{tab:tools}
\small
\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.30\textwidth} >{\raggedright\arraybackslash}p{0.18\textwidth} L@{}}
\toprule
Component & Version & Purpose \\
\midrule
FastAPI, Uvicorn & 0.111.0, 0.30.1 & Backend web framework and server \\
Pydantic Settings & 2.3.1 & Configuration and request validation \\
Neo4j (database, Python driver) & 5, 5.20.0 & Graph storage and queries \\
Groq Python client & 0.9.0 & Calls to the hosted language model \\
pandas & 2.2.2 & CSV loading and data preparation \\
PyTest, pytest-cov & 8.2.2, 5.0.0 & Backend tests \\
React, React Router & 18.3, 6.24 & Frontend framework and routing \\
Vite, Tailwind CSS & 5.3, 3.4 & Build tool and styling \\
Axios & 1.7 & HTTP client \\
react-force-graph-3d, three & 1.24, 0.185 & Interactive 3D graph \\
Vitest, Testing Library, jsdom & 2.1, 16, 29 & Frontend tests \\
Docker Compose & v2 & Local and CI full-stack runs \\
GitHub Actions & --- & CI and staging deployment \\
Vercel & --- & Frontend hosting and previews \\
Groq-hosted model & openai/gpt-oss-120b (eval); gpt-oss-20b (staging default) & Phrasing and classification; replaceable \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_acceptance.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Acceptance tests and results}
\label{tab:acceptance}
\small
\begin{tabularx}{\textwidth}{@{}c >{\raggedright\arraybackslash}p{0.26\textwidth} >{\raggedright\arraybackslash}p{0.10\textwidth} L@{}}
\toprule
ID & Scenario & Result & Evidence and caveat \\
\midrule
T01 & Application opens the maintenance workspace & Pass & Route smoke log; Sidebar tests. Browser console was not audited systematically \\
T02 & API lists loaded assets & Pass & \texttt{test\_api\_maintenance}; staging lists 118 aircraft \\
T03 & Selected asset history is displayed & Pass & AssetHistory tests; Figure~6.7 \\
T04 & Diagnosis returns graph-backed evidence and ranking & Partly & Full result with a live model locally (Figure~6.2); on staging fresh diagnoses returned no explanation text on 16~Oct \\
T05 & Explanation cites a real record that opens & Pass & \texttt{test\_citation\_validation}; Figure~6.3 \\
T06 & Unknown asset request & Pass & Controlled 404, ``Aircraft not found'', no invented history \\
T07 & Model unavailable & Pass & HTTP 503 with a reason; Figure~6.5 \\
T08 & Empty or ambiguous evidence & Pass & Explicit ``no relevant history''; ranking withheld when there is no evidence \\
T09 & Review queue shows a known case & Pass & Figure~6.8 \\
T10 & Review action on a test case & Pass & ReviewQueue and API tests; accept/reject not exercised live on shared data \\
T11 & Frontend tests and build & Pass & 171 tests pass; production build passes \\
T12 & Backend tests & Pass & 194 tests pass in CI \\
T13 & Pull-request CI runs and passes & Pass & Run \texttt{39068741787} on \texttt{36a98a3} succeeded \\
T14 & Real graph health & Pass & Staging reports Neo4j, live model, 2{,}079 records (18~Oct); Compose smoke \\
T15 & Setup on a clean machine & Partly & CI builds from a clean checkout; nobody outside the team has followed the guide \\
T16 & Legacy screen isolation & Pass & Sidebar and DomainContext tests; legacy URLs redirect \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_edge_cases.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Edge and failure cases, and the behaviour tested}
\label{tab:edge-cases}
\small
\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.30\textwidth} L@{}}
\toprule
Case & Behaviour \\
\midrule
Unknown aircraft & 404 and ``Aircraft not found'', never an empty history \\
Aircraft looked up by tail number & History route takes the UUID; a tail number returns 404 \\
No live model & HTTP 503 with a reason; Copilot returns an empty reply but keeps ranking and evidence \\
Empty model output & Explicit 503, never a blank success \\
Invented record identifier & Marked \texttt{[UNVERIFIED]} and left out of the valid list \\
Rate limit & Bounded retries; a daily budget stops runs cleanly \\
Superseded record in the Copilot & Visible as evidence, excluded from recommendations \\
Legacy confidence 1.0 & Reported as unscored with null confidence \\
Review action on a non-reviewable record & HTTP 409; the queue is unchanged \\
Reject without a note & Rejected by validation (HTTP 422) \\
Oversize or non-CSV upload & Rejected in the browser before anything is sent \\
Re-upload of the same CSV & Every record counted as already stored; nothing changes \\
Unreadable CSV & Backend may raise HTTP 500; interface wording discloses this (open issue) \\
Browser storage denied or corrupt & Copilot remains usable; a warning is shown \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_defects.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Defects found and their resolution}
\label{tab:defects}
\small
\begin{tabularx}{\textwidth}{@{}c L L >{\raggedright\arraybackslash}p{0.10\textwidth}@{}}
\toprule
\# & Defect & Corrective action & State \\
\midrule
1 & Frontend CI failed: review-queue test mock lacked \texttt{getRecord} & Mock fixed; storage shim added & Fixed \\
2 & Review-queue history links used tail numbers and led to 404 & Resolve aircraft UUID; hide link if unresolved & Fixed \\
3 & Deep link did not scroll while loading skeleton was shown & Scroll effect depends on loading state & Fixed \\
4 & Service Records issued 1+118 requests on load & Fleet-wide paginated endpoint; two page-initiated calls & Fixed \\
5 & Assets list was slow (one history query per aircraft) & Single aggregation query; $\approx$1.0\,s on staging & Fixed \\
6 & Placeholder confidence 1.0 shown as a real result & Honest analysis state; placeholders reported as unscored & Fixed \\
7 & Graph requested 200 nodes yet claimed ``Capped at 2000'' & Request 3{,}000; truthful counts; warning when cap is hit & Fixed \\
8 & CSV upload client posted to a path-only route & Posts to the upload route; new upload panel & Fixed \\
9 & Small graphs hid edges behind large nodes & Spacing and node size changed & Fixed \\
10 & Staging fresh diagnoses returned no explanation text & Cause not established; API reports empty output as 503 & Open \\
11 & Unreadable CSV returns unhandled HTTP 500 & Interface wording only; backend change still open & Open \\
12 & One staging record has no ABOUT link & Re-running ingest repairs it; not applied without approval & Open \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_ownership.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Ownership of files and work packages}
\label{tab:ownership}
\small
\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.26\textwidth} L >{\raggedright\arraybackslash}p{0.26\textwidth}@{}}
\toprule
Member & Owns & Work packages \\
\midrule
Shahmeer Atif (23I-0711) & React pages and components, the Axios client, frontend tests & S1--S5, then the graph view, CSV upload, evidence refresh \\
Muhammad Umar (23I-0782) & Graph schema and queries, diagnose internals, ranking, citation validation, diagnostic tests & U1--U5 \\
Muhammad Usman Al Haq (23I-0585) & Ingest, maintenance APIs, conflict engine, Docker Compose, CI, application wiring & A1--A4, then copilot, confidence and corrections, cost cascade \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_activity.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Repository activity by member}
\label{tab:activity}
\small
\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.18\textwidth} c >{\raggedright\arraybackslash}p{0.24\textwidth} L@{}}
\toprule
Member & Commits & Pull requests authored & Main deliverables \\
\midrule
Shahmeer & 20 & \#3, \#4, \#8--\#13 merged; \#14 open & Frontend rework and tests; graph view; CSV upload; evidence documents; this report \\
Umar & 19 & none on GitHub; merged via integration branches & Bounded retrieval (U2), ranking (U3), citation boundary and tests (U4, U5); staging workflow and ops API; knowledge bank \\
Usman & 59 & \#2, \#5, \#6, \#7 merged; \#1 closed & Maintenance domain and conflict engine, FAA ingest, evaluation harness, maintenance APIs, CI, copilot, cost cascade \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_prs.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Pull requests}
\label{tab:prs}
\small
\begin{tabularx}{\textwidth}{@{}c >{\raggedright\arraybackslash}p{0.16\textwidth} >{\raggedright\arraybackslash}p{0.10\textwidth} L@{}}
\toprule
PR & Author & State & Title \\
\midrule
\#1 & Usman & closed & Maintenance domain integration (September PoC; commits in main via integration branch) \\
\#2 & Usman & merged & Mid-I backend release hygiene closure \\
\#3 & Shahmeer & merged & Frontend maintenance UX, Service Records performance, diagnose and review hardening \\
\#4 & Shahmeer & merged & Frontend reflects backend outputs \\
\#5 & Usman & merged & Evidence-grounded diagnostic copilot \\
\#6 & Usman & merged & Confidence, corrections, conflict-cost evidence \\
\#7 & Usman & merged & Opt-in conflict-analysis cost cascade \\
\#8 & Shahmeer & merged & Documentation sync after \#5--\#7 \\
\#9 & Shahmeer & merged & Knowledge graph focused on one aircraft \\
\#10 & Shahmeer & merged & CSV upload with honest counts and inline errors \\
\#11 & Shahmeer & merged & Graph spacing and layout settling \\
\#12 & Shahmeer & merged & Single-aircraft analysis evidence \\
\#13 & Shahmeer & merged & Frontend evidence and demo script refresh \\
\#14 & Shahmeer & open & WebGL check and error boundary for the graph \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_milestones.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Milestone log with evidence}
\label{tab:milestones}
\small
\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.18\textwidth} L >{\raggedright\arraybackslash}p{0.28\textwidth}@{}}
\toprule
Date (2026) & Milestone & Evidence \\
\midrule
8--10 Sep & Maintenance proof of concept: domain registry, FAA acquisition, conflict engine, evaluation harness, first maintenance screens & Commits T0--T10 and related \\
15 Oct & Mid-I engineering blueprint; runtime smoke test fixed in CI & \texttt{docs/halite\_work\_division\_mid1.pdf}; commit \texttt{2651eab} \\
16 Oct & Frontend S1--S5; retrieval, ranking and citation boundary U2--U5; staging deployment; PRs \#2--\#5 merged & Commits; \texttt{docs/mid1/02}, 08, 11--13 \\
17 Oct & Confidence and corrections; cost cascade; knowledge graph; PRs \#6, \#7, \#9 & \texttt{docs/mid1/19--21} \\
18 Oct & CSV upload; evidence refresh; one-aircraft analysis; this report; PRs \#10--\#13 & \texttt{docs/mid1/23}; CI run \texttt{39068741787} \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_remaining_modules.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{Remaining work by module}
\label{tab:remaining-modules}
\small
\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.22\textwidth} >{\raggedright\arraybackslash}p{0.22\textwidth} L@{}}
\toprule
Module & State now & Remaining \\
\midrule
M01 Workspace & Not started & Authentication, roles, organisations, reviewer identity in the audit trail \\
M02 Assets & Working & Manual asset registration; component view \\
M03 Knowledge graph & Working (one aircraft) & Component-level graph; path exploration; WebGL fallback (PR open) \\
M04 Diagnostics & Working (lexical, heuristic) & Semantic and hybrid retrieval; baselines; server-side session history \\
M05 Conflict intelligence & Working; mostly unanalysed & Token measurement; full-corpus analysis with cascade; review audit log \\
M06 Report intelligence & CSV and single record & Extraction from documents; ambiguous-field flags \\
M07 Academy & Not started & Case-based scenarios, learner steps, feedback linked to evidence \\
M08 Analytics & Not started & Recurring-fault and fleet views with descriptive statistics only \\
M09 Administration & Status page only & Audit, configuration, governance \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    w(
        "tab_all_fr.tex",
        r"""
\begin{longtable}{@{}c >{\raggedright\arraybackslash}p{0.30\textwidth} >{\raggedright\arraybackslash}p{0.14\textwidth} p{0.40\textwidth}@{}}
\caption{All functional requirements and their Mid status}\label{tab:all-fr}\\
\toprule
ID & Requirement & Mid status & Evidence or reason \\
\midrule
\endfirsthead
\toprule
ID & Requirement & Mid status & Evidence or reason \\
\midrule
\endhead
\midrule\multicolumn{4}{r@{}}{\emph{Continued}}\\\midrule\endfoot
\bottomrule\endlastfoot
FR-01 & Authenticate authorised users & Deferred & No authentication yet \\
FR-02 & Associate users with organisations & Deferred & No organisations yet \\
FR-03 & Enforce role-based permissions & Deferred & FYP-1 Final \\
FR-04 & Prevent cross-tenant access & Deferred & No tenancy \\
FR-05 & Register maintenance assets & Partial & Assets created by ingest; no registration screen \\
FR-06 & Show chronological records for an asset & Met & AssetHistory.test (12); API 404 for unknown asset \\
FR-07 & Search assets by identifier & Met & Assets.test \\
FR-08 & Show record-linked diagnostic and conflict information & Met & Corrected-by banner; ServiceRecords.test (22) \\
FR-09 & Accept supported report formats & Partial & FAA CSV by upload or path; single record; no PDF/DOCX \\
FR-10 & Extract available fields & Partial & Structured CSV fields only; no free-text extraction \\
FR-11 & Retain the original source record & Met & Text and identifier stored; reject never deletes \\
FR-12 & Flag ambiguous or invalid fields & Partial & Skipped rows counted by reason; no per-field flags \\
FR-13 & Create relationships among entities & Met & \texttt{test\_maintenance\_agent} (10) \\
FR-14 & Traverse related historical cases & Met & Graph.test, graphScope.test \\
FR-15 & Expose provenance of graph results & Met & Edge legend; record source \\
FR-16 & Accept natural-language symptoms & Met & \texttt{test\_api\_diagnostics}, \texttt{test\_api\_copilot} \\
FR-17 & Retrieve relevant historical evidence & Met (lexical) & \texttt{test\_diagnostic\_retrieval} (26) \\
FR-18 & Rank hypotheses when evidence suffices & Met (heuristic) & Deterministic ranking tests \\
FR-19 & Display supporting record references & Met & Evidence links; Diagnostics.test (29) \\
FR-20 & Request clarification when information is missing & Partial & Copilot asks at most one question \\
FR-21 & Distinguish unsupported from verified & Met & \texttt{test\_citation\_validation} (6) \\
FR-22 & Preserve diagnostic session history & Partial & Browser storage only \\
FR-23 & Compare new records with prior records & Met & \texttt{test\_conflict\_engine} (32) \\
FR-24 & Classify potential conflicts & Met & Five labels; parse-failure routing \\
FR-25 & Route uncertain cases for review & Met & Routing tests; threshold 0.50 \\
FR-26 & Record supervisor review decisions & Met & No reviewer identity \\
FR-27 & Audit trail of status changes & Partial & Status and note stored; no actor or event log \\
FR-28 & Start a training case & Deferred & FYP-2 \\
FR-29 & Record learner steps & Deferred & FYP-2 \\
FR-30 & Feedback linked to case evidence & Deferred & FYP-2 \\
FR-31 & Store training completion history & Deferred & FYP-2 \\
FR-32 & Display recorded fault trends & Deferred & FYP-2 \\
FR-33 & Identify repeated faults on the same asset & Deferred & FYP-2 \\
FR-34 & Filters by asset, component and date range & Partial & Service Records filters exist; no analytics view \\
FR-35 & Distinguish descriptive statistics from predictions & Deferred & FYP-2 \\
\end{longtable}
""",
    )

    w(
        "tab_all_nfr.tex",
        r"""
\begin{table}[!htbp]
\centering
\caption{All non-functional requirements and their Mid status}
\label{tab:all-nfr}
\small
\begin{tabularx}{\textwidth}{@{}c >{\raggedright\arraybackslash}p{0.28\textwidth} >{\raggedright\arraybackslash}p{0.16\textwidth} L@{}}
\toprule
ID & Requirement & Mid status & Evidence or reason \\
\midrule
NFR-01 & Availability & Partial & Staging reachable at each check; no uptime monitoring \\
NFR-02 & API performance, p95 $\leq$500\,ms & Not met / not measured & Assets list 0.99\,s as one request; no load test \\
NFR-03 & Diagnostic latency measured & Not measured & Fresh diagnoses call an external model \\
NFR-04 & 80\% coverage of core backend modules & Not measured & No coverage run; test counts only \\
NFR-05 & No unauthorised tenant access & Deferred & No tenancy yet \\
NFR-06 & Failed external operations reported and retried safely & Met & Bounded retries; 503; failure states \\
NFR-07 & Citations resolve to real record IDs & Met & Citation validation and tests \\
NFR-08 & Usability measured & Not measured & No user study \\
NFR-09 & Independent setup succeeds & Partial & Setup guide and CI Compose smoke; no outside run \\
NFR-10 & Review changes traceable to actor and time & Partial & No actor recorded \\
\bottomrule
\end{tabularx}
\end{table}
""",
    )

    print("all tables generated")


if __name__ == "__main__":
    main()
