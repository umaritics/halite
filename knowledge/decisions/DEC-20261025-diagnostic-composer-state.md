---
id: dec-diagnostic-composer-state
title: Persist diagnostic composer visibility with the active workspace
status: accepted
owners: [Shahmeer]
updated: 2026-10-25
---

# DEC-20261025 — Diagnostic composer state

## Context

The full Copilot textarea permanently consumed vertical space after a response.
Hiding only its contents would not return that space to the independently
scrolling conversation, and deriving visibility solely from thread length would
discard a user's deliberate expansion and unsent draft on navigation.

## Decision

- A new investigation starts with the full composer mounted.
- Every successful turn unmounts the full composer and places a compact
  **Continue investigation** control inside the conversation card.
- Manual minimization preserves the draft. Failures keep the composer expanded;
  loading disables duplicate submission and minimization.
- `diagnosticWorkspace` persists `composerExpanded` with the unsaved active
  workspace. Older compatible snapshots derive the state: a draft stays expanded,
  a completed thread without a draft is compact, and an incomplete thread expands.
- Named completed sessions resume compact. Expanding/minimizing is local UI state
  and never performs retrieval, inference, or ranking animation.

## Consequences

- The conversation becomes the flex-growing child when the form is unmounted, so
  collapsed mode returns real height rather than concealing occupied layout.
- Draft restoration remains automatic and independent of manual session saving.
- The compact control remains keyboard reachable at the conversation's lower edge;
  reopening transfers focus to the textarea.

## Owners

Shahmeer

## Date

2026-10-25
