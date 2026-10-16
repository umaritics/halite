# Mid-I evidence and progress (agent entry)

Read this folder for **dated Mid-I progress, audits, and partner handoffs**.  
Durable architecture lives in [`knowledge/`](../../knowledge/README.md). Universal agent rules: [`AGENTS.md`](../../AGENTS.md).

## How to use (reduce ambiguity)

1. Start with the **owner audit** for the person whose code you will touch.  
2. Open linked **knowledge** modules before editing.  
3. Treat **PASS** only when a command/test/staging observation is recorded.  
4. Do not “fix” another owner’s files without a handoff DEC.

## Index

| Doc | Owner | Purpose |
| --- | --- | --- |
| [04_data_conflict_devops_evidence.md](04_data_conflict_devops_evidence.md) | Usman | Data/conflict/DevOps evidence |
| [05_usman_final_audit.md](05_usman_final_audit.md) | Usman | A1–A4 audit verdicts |
| [06_frontend_review_queue_handoff.md](06_frontend_review_queue_handoff.md) | Usman → Shahmeer | Frontend CI test mock handoff |
| [07_usman_release_readiness.md](07_usman_release_readiness.md) | Usman | Release readiness / blockers |
| [08_umar_progress.md](08_umar_progress.md) | Umar | **Umar final Mid-I audit** (U1–U5 + CD + open team work) |
| [09_frontend_shared_api.md](09_frontend_shared_api.md) | Umar (team) | Vite → staging; ECONNREFUSED root cause |
| [10_perf_assets_api_handoff.md](10_perf_assets_api_handoff.md) | Shahmeer + Usman | Assets N+1 + history fan-out; no Redis first |
| [11_u2_real_data_retrieval.md](11_u2_real_data_retrieval.md) | Umar | U2 staging Neo4j retrieval proof + bounds |
| [12_u4_u5_diagnostics_handoff.md](12_u4_u5_diagnostics_handoff.md) | Umar → Shahmeer | Citation/LLM boundary + diagnose UI contract |
| [13_u3_deterministic_ranking.md](13_u3_deterministic_ranking.md) | Umar | U3 ranking weights, tie-break, schema |
| [14_usman_umar_integration.md](14_usman_umar_integration.md) | Usman + Umar | Combined audit, rubric mapping, performance closure, remaining Shahmeer work |
| [15_report_mid1_addendum.md](15_report_mid1_addendum.md) ([PDF](Halite_FYP_Report_Mid1_Addendum.pdf)) | Team | Report implementation correction and responsible tool disclosure |
| [16_usman_conflict_score_backfill_handoff.md](16_usman_conflict_score_backfill_handoff.md) | **Usman** | All records confidence=1 / auto_accepted — ingest vs conflict backfill; demo Review Queue |

## Partner agents — start here

| Role | Read first |
| --- | --- |
| Any agent | [`08_umar_progress.md`](08_umar_progress.md) + [`knowledge/README.md`](../../knowledge/README.md) |
| Frontend / Vite broken | [`09`](09_frontend_shared_api.md) then [`10`](10_perf_assets_api_handoff.md) |
| Diagnostics UI | [`12`](12_u4_u5_diagnostics_handoff.md) + [`13`](13_u3_deterministic_ranking.md) |
| Staging / CD / logs | [`knowledge/context/modules/remote_backend.md`](../../knowledge/context/modules/remote_backend.md) |
| Usman reconciliation | [`05`](05_usman_final_audit.md) + note staging corpus now live (Umar U2) |
| **Usman — empty Review Queue / all confidence 1** | **[`16_usman_conflict_score_backfill_handoff.md`](16_usman_conflict_score_backfill_handoff.md)** |

## Branch map

| Branch | Owner focus |
| --- | --- |
| `usman` | A1–A4 maintenance/conflict/CI evidence |
| `umar/mid1-graph-diagnostics` | Umar — U1–U5 diagnostics + staging CD (team referral branch) |
| Shahmeer frontend branch | CI mock + UI + perf load patterns |
