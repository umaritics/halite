# Sets GitHub Actions secrets for Halite staging deploy using the DEDICATED deploy key.
# Does NOT upload your personal SSH key.
#
# Prerequisites:
#   - gh auth login
#   - Dedicated key at %USERPROFILE%\.ssh\halite_github_deploy (created during VM setup)
#
# Usage:
#   cd <repo-root>
#   .\scripts\vm\set_github_secrets.ps1

$ErrorActionPreference = "Stop"

$keyPath = Join-Path $env:USERPROFILE ".ssh\halite_github_deploy"
if (-not (Test-Path $keyPath)) {
  throw "Missing dedicated deploy key at $keyPath"
}

Write-Host "Setting secrets on umaritics/halite from dedicated deploy key only..."
gh secret set VM_SSH_HOST --body "dev1.corp.curatech.pk" --repo umaritics/halite
gh secret set VM_SSH_USER --body "umar" --repo umaritics/halite
gh secret set VM_DEPLOY_PATH --body "/home/umar/halite" --repo umaritics/halite
Get-Content -Raw $keyPath | gh secret set VM_SSH_KEY --repo umaritics/halite

Write-Host "OK."
Write-Host "Next: GitHub Settings → Environments → create 'staging' if missing."
Write-Host "Verify: gh secret list --repo umaritics/halite"
