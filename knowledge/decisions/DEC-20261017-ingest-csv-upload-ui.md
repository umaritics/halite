---
id: dec-ingest-csv-upload-ui
title: Ingest page uploads a CSV through the existing upload route
status: accepted
owners: [Shahmeer]
updated: 2026-10-17
---

# DEC-20261017 — Ingest page: CSV upload, honest counts, inline errors

## Context

`maintenanceAPI.ingestFile` posted a file to `/maintenance/ingest`, which accepts
only JSON with a server-side `csv_path`, and no screen called it. The Ingest page
could therefore only load a path that already existed on the API server. Failures
were browser `alert()` pop-ups, and the result card labelled `assets_created`
"Assets Created" although the backend sets it to `len(asset_latest)`: the distinct
aircraft among valid rows, including aircraft that already existed.

## Decision

- `ingestFile` posts multipart (`file`) to the existing `POST /maintenance/ingest/upload`.
  No backend change.
- The page gains an **Upload CSV** panel. Choosing a file changes nothing; the
  user must press **Ingest this file**, because ingesting writes to the connected
  graph. The file must be `.csv` and at most 10 MB (mirrors `MAX_UPLOAD_MB`; the
  server still enforces its own limit).
- The server-path panel stays, labelled as a server file.
- Counts are the backend's own numbers, relabelled for what they count
  ("Aircraft in file", "Already in graph", skip reasons). The summary lines
  ("No records were created", "Nothing new") are derived from those counts only.
- Failures render inline. The backend only accepts `DifficultyDate` as
  `MM/DD/YYYY`, so the UI says so.
- New records are `unscored`; the result links to
  `/app/records?analysis_state=unscored`. The UI does not trigger analysis.

## Consequences

An unparseable CSV (for example an empty file) makes the upload route raise an
unhandled `pandas` error: HTTP 500 without CORS headers, which a browser reports as
a network failure. The UI therefore words an upload network error as "no readable
reply: the API may be unreachable, or it could not read the file". A backend fix
(return 400 for an unreadable CSV) belongs to Usman and would let the UI show the
real reason. Verified locally against an in-memory backend, not against staging.
