#!/usr/bin/env bash
# Runs ON the VM (invoked by GitHub Actions over SSH).
# Expects: repo checkout at $DEPLOY_PATH, Docker Compose v2, backend/.env already present.
set -euo pipefail

DEPLOY_PATH="${DEPLOY_PATH:?DEPLOY_PATH is required}"
DEPLOY_SHA="${DEPLOY_SHA:?DEPLOY_SHA is required}"
DEPLOYED_AT="${DEPLOYED_AT:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"

cd "$DEPLOY_PATH"

echo "==> Fetching $DEPLOY_SHA"
git fetch --all --prune
git checkout --force "$DEPLOY_SHA"
git reset --hard "$DEPLOY_SHA"

export GIT_SHA="$DEPLOY_SHA"
export DEPLOYED_AT

echo "==> Building and restarting halite-api"
docker compose -f docker-compose.vm.yml build --build-arg GIT_SHA="$GIT_SHA" --build-arg DEPLOYED_AT="$DEPLOYED_AT"
docker compose -f docker-compose.vm.yml up -d --remove-orphans

echo "==> Waiting for health"
healthy=0
for attempt in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:8002/api/health" >/tmp/halite-health.json; then
    healthy=1
    break
  fi
  sleep 2
done

if [ "$healthy" -ne 1 ]; then
  echo "==> Health check failed" >&2
  docker compose -f docker-compose.vm.yml ps || true
  docker logs --tail=120 halite-api || true
  exit 1
fi

echo "==> Health OK"
cat /tmp/halite-health.json
echo
curl -fsS "http://127.0.0.1:8002/api/ops/version" | tee /tmp/halite-version.json
echo

echo "==> Verifying security posture on localhost:8002"
python3 - <<'PY'
import json
import urllib.error
import urllib.request
from pathlib import Path

env_map: dict[str, str] = {}
for raw_line in Path("backend/.env").read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env_map[k.strip()] = v.strip().strip('"').strip("'")

api_key = env_map.get("HALITE_API_KEY", "").strip()
if not api_key:
    raise SystemExit("FATAL: HALITE_API_KEY is missing in backend/.env on the VM")

health = json.loads(Path("/tmp/halite-health.json").read_text(encoding="utf-8"))
version = json.loads(Path("/tmp/halite-version.json").read_text(encoding="utf-8"))
if version.get("auth_enabled") is not True:
    raise SystemExit(f"FATAL: auth_enabled is not True: {version}")
if version.get("openapi_enabled") is not False:
    raise SystemExit(f"FATAL: openapi_enabled must be False on VM: {version}")
if health.get("auth_db_mode") != "postgresql":
    raise SystemExit(f"FATAL: expected auth_db_mode=postgresql on VM, got {health.get('auth_db_mode')}")

def status_of(path: str, headers: dict[str, str] | None = None, method: str = "GET") -> int:
    req = urllib.request.Request(
        f"http://127.0.0.1:8002{path}",
        headers=headers or {},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
            return resp.status
    except urllib.error.HTTPError as exc:
        exc.read()
        return exc.code

unauth = status_of("/api/maintenance/assets")
if unauth != 401:
    raise SystemExit(f"FATAL: anonymous /api/maintenance/assets returned {unauth}, expected 401")

docs_code = status_of("/docs")
if docs_code != 404:
    raise SystemExit(f"FATAL: /docs returned {docs_code}, expected 404")

webhook_code = status_of("/api/webhook/gitea", method="POST")
if webhook_code != 410:
    raise SystemExit(f"FATAL: /api/webhook/gitea returned {webhook_code}, expected 410")

auth_ok = status_of(
    "/api/maintenance/assets",
    headers={"Authorization": f"Bearer {api_key}"},
)
if auth_ok != 200:
    raise SystemExit(f"FATAL: authenticated /api/maintenance/assets returned {auth_ok}, expected 200")

print("VM security & authenticated smoke checks PASSED (unauth=401, docs=404, gitea=410, auth=200)")
PY
