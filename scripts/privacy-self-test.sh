#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output="$(KALI_ACADEMY_ROOT="$ROOT" bash "$ROOT/bin/academy" privacy status)"
grep -q "does not make this device invisible or anonymous" <<<"$output"
grep -q "Privacy score:" <<<"$output"
grep -q "Active interface:" <<<"$output"
! grep -q "systemctl restart NetworkManager" "$ROOT/bin/academy-privacy"
grep -q "active SSH session" "$ROOT/bin/academy-privacy"
grep -q "tailscale0" "$ROOT/bin/academy-privacy"
echo "Privacy self-test passed."
