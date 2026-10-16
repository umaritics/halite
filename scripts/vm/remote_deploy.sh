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
for attempt in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:8002/api/health" >/tmp/halite-health.json; then
    echo "==> Health OK"
    cat /tmp/halite-health.json
    echo
    curl -fsS "http://127.0.0.1:8002/api/ops/version" || true
    echo
    exit 0
  fi
  sleep 2
done

echo "==> Health check failed" >&2
docker compose -f docker-compose.vm.yml ps || true
docker logs --tail=120 halite-api || true
exit 1
