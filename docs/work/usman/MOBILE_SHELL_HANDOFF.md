# Shared-shell mobile integration review proposal

A built-browser visual check at 390px exposed the existing 256px sidebar leaving
only 134px for the workspace. The question flow and saved state work, but the
phone layout is not usable. A no-horizontal-overflow assertion alone was too
weak to establish usability; the initial phone screenshot is failure evidence.

`MOBILE_SHELL_HANDOFF.patch` is a concrete, unapplied patch for App.jsx and
Sidebar.jsx. It passes `git apply --check`. Shared source files are unchanged in
the live-question package. The proposal keeps the desktop layout at md and above,
uses a 64px icon rail below md, retains accessible navigation/sign-out names,
allows navigation scrolling, and adds min-width:0 to the content flex item.
It changes no routes, roles, auth or other feature behavior.

AGENTS.md: “Respect Mid-I ownership (do not edit another owner’s files without a
handoff decision)”. The current plan assigns the shell to Shahmeer. The earlier
user authorization covered session registration/auth integration; this additional
responsive change is therefore proposed as a distinct review preparation rather
than silently extending that authorization. The user has now explicitly authorized: “Prepare and test the separate layout branch”. Apply/test on that separate review
branch, retain Shahmeer review/merge pending, and
verify real browser desktop/phone geometry plus keyboard/link names and logout.
