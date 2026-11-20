# Local machine storage incident — 20 November 2026

The user reported two full-machine freezes requiring forced power-off. Project
execution was stopped for lightweight diagnosis. The exact freeze cause is not
proven. The two interrupted boot journals contain no recorded OOM kill/GPU hang;
startup graphics/firmware warnings are not evidence of the freeze trigger.
An earlier boot has explicit system-log write failures from a full filesystem.
Local dependency restoration had also failed with ENOSPC. Continuing installation
attempts with so little headroom was inappropriate; future verification must
check available space before allocating local resources.

## User-authorized cleanup, verified

- Earlier authorization: clear rebuildable npm content cache only; completed.
- Subsequent authorization: empty Trash and remove downloaded app installers.
- Emptied Trash files and metadata (12 top-level trashed entries); no errors.
- Removed exactly four app downloads: Antigravity IDE.tar.gz, Antigravity.tar.gz,
  google-chrome-stable_current_amd64.deb and code.deb (about 518 MiB total).
- Chrome and VS Code were confirmed installed before removing their installers.
- This cleanup freed 19,537,694,720 bytes (about 18.2 GiB). The system filesystem
  now reports about 21 GiB available / 77% used, versus 98% used before cleanup.
- Project/research/report archives, source projects, installed apps, development
  tools, Docker objects/volumes and browser profiles were retained.
- No FYP test/build/model/installer process was running at the final process check.
- Current memory snapshot: about 11 GiB available, no swap in use. This is current
  health only and does not prove the machine's resource state before a freeze.

## Larger retained items for the user's decision

Sizes are inventories, not guaranteed reclaimable space; shared storage overlaps.

| Item | Measured size | Meaning |
| --- | --- | --- |
| Docker build cache | 3.309 GB; Docker estimates 2.955 GB reclaimable | Rebuildable; not deleted |
| Docker images | 5.229 GB; Docker estimates 1.629 GB reclaimable | Some unused images; not deleted |
| Docker volumes | 7.959 GB; 0 B reported reclaimable | Active project data; do not prune |
| Flatpak apps/shared runtimes | 6.8 GiB, including 5.7 GiB runtimes | Installed ZapZap, Kooha, VLC and dependencies; review unused runtimes before any uninstall |
| Editor extensions | VS Code 1.8 GiB, Cursor 1.8 GiB, Antigravity IDE 1.6 GiB | Remove only tools/extensions the user no longer needs |
| Extracted Antigravity folders in Downloads | 741 MiB + 476 MiB | May be the actual portable apps; retained |
| Chrome cache | 1.1 GiB | Rebuildable; not the browser profile |
| NuGet packages/cache | about 1.8 GiB across two directories | Downloaded development dependencies; retained |
| Playwright/Puppeteer browsers | about 1.0 GiB combined | Automation tools may need them; retained |
| Codex runtime cache | 1.9 GiB | Active tooling; retained |
| Chrome profile | 2.2 GiB | User browser data; do not delete as cache |
| Desktop projects | 6.9 GiB combined | User work; retained |

## Local execution policy for this task

Use hosted CI for full suites, container builds and database-backed regression.
Do not start multiple local heavy jobs together. Check storage/memory before local
verification and stop allocations if free storage is below 10 GiB (a conservative
project guard, not a proven OS threshold). Keep any necessary lightweight local
checks serial and resource-limited. No stress testing, driver changes or blanket
Docker/volume pruning is authorized by this cleanup request.

The storage pressure has been relieved. The root cause of the hard freezes remains
unconfirmed; do not claim the machine is guaranteed fixed by freeing disk space.

## Follow-up diagnosis and additional cache cleanup

- Last interrupted project activity was research-results API implementation and
  restoration of test dependencies. Research API/publication files were saved at
  approximately 17:57:13 +05; the previous boot's journal stops at 17:57:06. Timing
  alone does not establish a cause. No real local LLM comparison was running.
- Removed only Docker build cache after the user's follow-up cleanup request.
  Docker reported 3.309 GB reclaimed; subsequent `docker system df` reports zero
  build cache. Containers, images and volumes were retained.
- Verified root filesystem after cleanup: 24 GiB available, 74% used.
- Three unrelated running Kubernetes control-plane containers remain. A single
  sample showed memory usage of 1.038, 1.481 and 1.156 GiB (about 3.7 GiB combined),
  with CPU roughly 8–9% each. These are potential background load, not proven freeze
  causes. Do not stop them without confirming they are not needed.
- No additional reboot or goal restart is required for storage cleanup. Continue
  project verification through hosted CI; do not recreate the earlier local
  dependency-install/build load. Preserve at least 10 GiB free before local work.
- No further app, project, volume or user-profile deletion is needed now.
