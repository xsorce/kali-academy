#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failed=0

while IFS= read -r -d '' file; do
  if ! bash -n "$file"; then
    echo "bash syntax failed: $file"
    failed=1
  fi
done < <(find "$ROOT/bin" "$ROOT/scripts" -type f ! -name '*.py' -print0; printf '%s\0' "$ROOT/install.sh" "$ROOT/apply.sh")

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

if (( failed )); then exit 1; fi
echo "Self-test passed."
