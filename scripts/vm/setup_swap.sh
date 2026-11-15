#!/usr/bin/env bash
# One-time helper for staging VM (run with sudo). See docs/local-llm-staging.md
set -euo pipefail
SWAPFILE=/swapfile
SIZE=4G
if swapon --show | grep -q "$SWAPFILE"; then
  echo "Swap already active on $SWAPFILE"
  exit 0
fi
if [[ ! -f "$SWAPFILE" ]]; then
  fallocate -l "$SIZE" "$SWAPFILE" || dd if=/dev/zero of="$SWAPFILE" bs=1M count=4096
  chmod 600 "$SWAPFILE"
  mkswap "$SWAPFILE"
fi
swapon "$SWAPFILE"
grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
swapon --show
free -h