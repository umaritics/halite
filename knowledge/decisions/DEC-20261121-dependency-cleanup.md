# Remove unused dependency roots while preserving required runtime libraries

- Status: implemented; hosted dependency/regression verification pending
- Date: 2026-11-21
- Owner: Usman

## Context

The master plan names unused dependency cleanup. The previous local restore
failed on a full filesystem, so verification stays hosted. Actual imports show
pandas is needed by maintenance CSV ingest and FAA tools; docx2txt/pypdf still
serve the not-yet-retired document route. Settings/server tooling need dotenv
transitively. The verified baseline installed NumPy 1.26.4 under LangChain's <2
constraint; removing that package must not incidentally upgrade the CSV stack.

## Decision

Remove the three unused direct LangChain requirements, python-docx and the
redundant direct python-dotenv pin. Retain actual ingest/document dependencies
and pin the already-installed NumPy version to preserve the verified stack.
Audit Python imports and store hosted pip install/installed metadata and a
summary alongside test artifacts. Add an actual dotenv-backed Settings test.

## Consequences

This change alone does not retire an API or alter domain defaults. Dotenv remains
transitive and is not falsely reported absent. The separate legacy retirement
proposal has explicit user authorization for preparation/testing; owner review
and merge are still pending. Future intentional dependency changes must update
the audit/baseline explicitly rather than bypassing it.
