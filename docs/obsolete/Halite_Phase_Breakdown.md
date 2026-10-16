# Halite — Phase-Wise Breakdown

Supervisor: Syed Muhammad Saad Salman

---

## 1. Proposal defense — done, current state

- **Knowledge graph** — Neo4j schema live: `Component`, `Decision`, `Commit`, `Ticket`, `Document` nodes, 8 edge types
- **DocumentAgent** — extracts decisions from PDF/DOCX/TXT/MD uploads
- **CodeAgent** — infers components from source file structure
- **GiteaAgent** — syncs commits/issues from repo, handles webhooks
- **DecisionAgent** — manual decision entry from UI
- **Invalidation engine** — flags linked decisions `needs_review` when a file changes
- **Chat** — Groq-grounded Q&A citing graph decisions
- **Graph view** — live 3D force-directed visualization
- **Bugs:** decisions go `active` with no review gate; chunking sends everything to extraction regardless of content

## 2. FYP-1 mid — planned

- **DocumentAgent** — add `pending_review` status before a decision goes active
- **DocumentAgent** — add decision-presence filter before extraction (fixes the chunking bug)
- **GiteaAgent** — add full history backfill, not just webhook-forward
- **Invalidation engine** — add co-change weighting to cut false positives
- SRS submitted

## 3. FYP-1 defense — planned, core contribution

- **MCP server** — new, 5 tools: `query_decisions`, `get_component_context`, `record_decision`, `get_alerts`, `get_project_context`
- **Context injection** — pre-prompt hook auto-injects relevant decisions into IDE agent, ~800 token budget
- **Context export** — CLAUDE.md generator, scoped per module
- Must demo live inside Claude Code/Cursor
- SDS submitted

## 4. FYP-2 defense — planned

- **Multi-repo support** — new `Project`/`Repository` nodes, `Repository -[:PART_OF]-> Project` edge
- **Coherence check** — component-name overlap + commit-author overlap + LLM read on README/tech stack before linking repos
- **Schema addition** — `Person` node for author attribution across repos
- **CodeAgent** — extended to handle component inference across multiple linked repos
- **Frontend** — project switcher UI, multi-repo view in graph
- **Evaluation harness** — built out: extraction precision/recall test set, invalidation false-positive test set, MCP injection relevance benchmark vs flat MEMORY.md baseline
- **NFR measurement** — starts: MCP tool latency, chat response time, webhook processing time
- Test report drafting begins
- SDS updated with multi-repo schema

## 5. Pre-job-fair defense — planned, FYP functionally complete

- **Evaluation** — all four numbers finalized: extraction precision/recall, invalidation false-positive rate, MCP injection relevance, coherence check accuracy
- **UAT** — 5-8 devs, 2-week trial, task completion + retrieval accuracy logged
- **Bug pass** — fix issues surfaced by UAT and evaluation runs
- **Deployment** — backend hardened on Docker/VM, frontend on Vercel, installable from README by an outsider
- **NFRs** — closed out with numbers, any misses dispositioned
- **Performance** — MCP context injection tuned to stay inside latency/token targets under real use
- Handover package drafted: source, build steps, dependencies, known limitations
- Demo script for job fair + final defense locked

## 6. Final defense — planned, wrap-up only

- No new features
- **Report set** finalized: SRS, SDS, test report, evaluation results, RAID log, traceability matrix
- **AI usage log** signed off
- Final bug-fix pass on anything flagged during pre-job-fair round
- One end-to-end demo: `DocumentAgent`/`GiteaAgent` ingest → `invalidate_decisions_for_files()` fires → alert appears → MCP injects context live in an IDE → chat cites the decision with a staleness badge
- Backup demo recording prepared in case of live-demo failure
- Presentation rehearsed against the single end-to-end flow
