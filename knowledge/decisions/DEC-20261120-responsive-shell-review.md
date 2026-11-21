# Responsive shell review preparation

Status: user-authorized preparation implemented/tested; Shahmeer review/merge pending
Date: 2026-11-20
Owners: Usman (integration preparation), Shahmeer (shared shell review)

## Context

The built question flow worked, but phone visual QA exposed a fixed 256px sidebar
leaving only 134px main width. No horizontal overflow did not prove usable content.
The shell belongs to Shahmeer; the previous routing/auth authorization was not
silently extended to responsive work.

## Decision

Prepared a concrete unapplied App/Sidebar patch. The user then authorized
“Prepare and test the separate layout branch”. Apply exactly that patch on
`codex/usman-mobile-integration`, separate from live-question PR #34. Use a 64px
icon rail below md with accessible names and scrolling navigation. Keep the 256px
desktop layout, all roles/routes/badges/auth behavior and the wider design system.
Main needs min-width:0 for its flex layout.

## Consequences

264 frontend tests pass. The built browser submits a phone-width question, measures
326px main/260px select width, verifies desktop width, no overflow, exact saved
posterior, budget three, keyboard navigation, logout and protected deep-link gate.
The original failure screenshot is retained and explicitly labelled as such.
No backend or selected operating-point change accompanies this integration.
