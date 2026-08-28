#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failed=0

while IFS= read -r -d '' file; do
  if ! bash -n "$file"; then
    echo "bash syntax failed: $file"
    failed=1
  fi
done < <(find "$ROOT/bin" "$ROOT/scripts" -type f ! -name '*.py' ! -path '*/__pycache__/*' -print0; printf '%s\0' "$ROOT/install.sh" "$ROOT/apply.sh")

python3 -m py_compile "$ROOT"/academy/*.py
PYTHONPATH="$ROOT/academy" python3 -c 'import state; assert state.STATE_SCHEMA_VERSION == state.DEFAULT_STATE["schema_version"]'
python3 "$ROOT/scripts/learning-self-test.py"
python3 "$ROOT/scripts/notes-self-test.py"
python3 "$ROOT/scripts/docs-self-test.py"
python3 "$ROOT/scripts/wifi-self-test.py"
bash "$ROOT/scripts/privacy-self-test.sh"
bash "$ROOT/scripts/model-self-test.sh"
[[ -s "$ROOT/VERSION" ]] || { echo "VERSION is missing or empty"; failed=1; }
HOME="${TMPDIR:-/tmp}" bash "$ROOT/bin/academy-storage" status >/dev/null
grep -q "128 GB Academy SSD" "$ROOT/bin/rescue"
grep -q "ntfsfix -n" "$ROOT/bin/rescue"
if grep -Eq '^[[:space:]]*(sudo[[:space:]]+)?ddrescue[[:space:]]' "$ROOT/bin/rescue"; then
  echo "rescue must not execute ddrescue"
  failed=1
fi
[[ "$(KALI_ACADEMY_ROOT="$ROOT" bash "$ROOT/bin/academy" version)" == "Kali Academy $(cat "$ROOT/VERSION")" ]] || {
  echo "academy version failed"
  failed=1
}
grep -q 'git status --porcelain' "$ROOT/bin/academy-update"
grep -q 'git pull --ff-only' "$ROOT/bin/academy-update"
grep -q -- '--backup-only' "$ROOT/bin/academy-update"
grep -q -- '--rollback --no-backup' "$ROOT/bin/academy-update"
if grep -Rq -- '_complete-lab' "$ROOT/academy" "$ROOT/bin"; then echo "direct lab XP command remains"; failed=1; fi
grep -q 'award_verified_xp "$id"' "$ROOT/bin/labctl"
grep -q 'scripts/health-check.sh' "$ROOT/apply.sh" "$ROOT/bin/academy-update"
grep -q 'learner-snapshot' "$ROOT/apply.sh"
if grep -q 'zoxide starship' "$ROOT/install.sh"; then echo "starship is still required"; failed=1; fi
if grep -q 'build_images rebuild' "$ROOT/bin/labctl"; then echo "normal reset still rebuilds images"; failed=1; fi
grep -q '@sha256:' "$ROOT/labs/linux-target/Dockerfile"
grep -q '@sha256:' "$ROOT/labs/net-tools/Dockerfile"
[[ "$(grep -c 'storage_preflight "' "$ROOT/install.sh")" -ge 6 ]] || { echo "installer storage preflights are incomplete"; failed=1; }
grep -q 'OLLAMA_VERSION="0.32.14"' "$ROOT/install.sh"
grep -q 'CODEX_VERSION="0.149.1"' "$ROOT/install.sh"
grep -q 'OLLAMA_INSTALL_SHA256=' "$ROOT/install.sh"
grep -q '@openai/codex@\$CODEX_VERSION' "$ROOT/install.sh"
grep -q 'QWEN_FAST_ID="359d7dd4bcda"' "$ROOT/install.sh"
grep -q 'QWEN_LITE_ID="8f68893c685c"' "$ROOT/install.sh"
grep -q '06c1097efce0' "$ROOT/bin/academy-models"
grep -q 'Ollama is still unavailable after 20 readiness checks' "$ROOT/install.sh"
grep -q 'HOME does not belong to or match the current user' "$ROOT/install.sh"
if grep -Eq 'curl[^|]*\|[[:space:]]*(sh|bash)|kali-codex-64k|num_ctx 65536|tcpdump -ni eth0' "$ROOT/install.sh" "$ROOT/bin/academy-model" "$ROOT/bin/labctl" "$ROOT/models"/*; then
  echo "an unguarded installer, 64K default, or hardcoded lab interface remains"; failed=1
fi
grep -q 'PARAMETER num_ctx 16384' "$ROOT/models/KaliCodex.Modelfile"
grep -q 'lab_capture_interface' "$ROOT/bin/labctl"

if (( failed )); then exit 1; fi
echo "Self-test passed."
