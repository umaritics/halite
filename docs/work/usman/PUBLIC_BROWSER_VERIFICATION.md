# Actual signed-in public website

Story: the dedicated authorized account signs in through the canonical website,
reads real research/home/history data, renews its session and signs out.

Public frontend: https://halite-mu.vercel.app

Backend: https://dev1.corp.curatech.pk/halite-api

Merged main `db574acadd4caf5cf60be45559708c82319711a6` passed CI44988523496
and deploy44988762837. Public health independently reported that exact revision,
Neo4j, live phi4-mini configuration, PostgreSQL and 2,079 maintenance records.

The real manual browser run
[44988921561](https://github.com/umaritics/halite/actions/runs/44988921561)
passed on that same revision. Chromium ran on GitHub, never on the laptop.

| Boundary | Actual evidence |
| --- | --- |
| Signed-out deep link | Research URL redirects to login |
| Login and destination | Real authorized account login200; returns to requested research page |
| Research API to charts | Authenticated experiments200; source artifact hashes match checkout; rendered157cases/7answers/5matches match saved data |
| Session renewal | Three observed refresh200 responses across full-page navigation/reloads; research still loads |
| Themes and geometry | Desktop1280; light/dark390 phone views; no document overflow; phone main width326px |
| Home data | All three real summary endpoints200; empty retrieval/integrity stats explicitly labelled unavailable; actual session counts zero |
| Investigation history | Real sessions200; zero matching cases; empty state and creation form render |
| Quick diagnosis entry | Real form renders on phone; no diagnosis request made by this browser instrument |
| Logout and privacy | Logout200, session refresh storage cleared, protected deep link returns to login without research heading |
| Errors and mutation guard | Zero page errors; zero prohibited requests; no model/corpus/session mutations |

Reviewed all six actual screenshots: research desktop dark, research phone
light/dark, home desktop, history phone and quick-entry phone. All hashes match
the record. Initial/final signed-out refresh401 responses are expected; no token
or password was written to the artifact. Source/merge/main-CI/deploy/browser raw
proof is retained under `evidence/phase26-public-release/`.

The read story is verified. Empty history does not prove production creation,
turn persistence, closure or printing; those complete lifecycle flows have
disposable full-stack evidence but need a separate labelled production account
check. The browser run did not invoke a model or certify repair correctness.
Independent owner review, human grounding labels and M4 decisions remain separate.
