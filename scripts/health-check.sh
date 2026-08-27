#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "$ROOT/VERSION")"
TEMP_HOME="$(mktemp -d)"
trap 'rm -rf -- "$TEMP_HOME"' EXIT

bash "$ROOT/scripts/self-test.sh"
command -v python3 >/dev/null
python3 -c 'import rich'
[[ "$(KALI_ACADEMY_ROOT="$ROOT" bash "$ROOT/bin/academy" version)" == "Kali Academy $VERSION" ]]
HOME="$TEMP_HOME" KALI_ACADEMY_ROOT="$ROOT" python3 "$ROOT/academy/app.py" knowledge --no-animation >/dev/null

command -v ollama >/dev/null
ollama list >/dev/null
ollama show qwen3:4b >/dev/null
ollama show qwen3:1.7b >/dev/null
[[ "$(ollama list | awk '$1 == "qwen3:4b" {print $2; exit}')" == 359d7dd4bcda* ]]
[[ "$(ollama list | awk '$1 == "qwen3:1.7b" {print $2; exit}')" == 8f68893c685c* ]]
bash "$ROOT/bin/academy-model" resolve tutor >/dev/null
bash "$ROOT/bin/academy-model" resolve codex >/dev/null
command -v codex >/dev/null
codex --version >/dev/null

if docker info >/dev/null 2>&1; then
  KALI_ACADEMY_ROOT="$ROOT" bash "$ROOT/bin/labctl" status >/dev/null
elif sudo -n docker info >/dev/null 2>&1; then
  KALI_ACADEMY_ROOT="$ROOT" bash "$ROOT/bin/labctl" status >/dev/null
else
  echo "Health check failed: Docker daemon is unavailable to the current user." >&2
  exit 1
fi

echo "Academy health check passed."
