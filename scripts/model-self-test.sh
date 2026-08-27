#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP="$(mktemp -d)"
trap 'rm -rf -- "$TEMP"' EXIT
mkdir -p "$TEMP/bin" "$TEMP/config"
cat > "$TEMP/bin/ollama" <<'EOF'
#!/usr/bin/env bash
case "$1" in
  show) grep -Fxq "$2" "$ACADEMY_TEST_MODELS" ;;
  pull) printf '%s\n' "$2" > "$ACADEMY_TEST_PULL" ;;
esac
EOF
chmod +x "$TEMP/bin/ollama"
export PATH="$TEMP/bin:$PATH" ACADEMY_MODEL_CONFIG_DIR="$TEMP/config"
export ACADEMY_TEST_MODELS="$TEMP/models" ACADEMY_TEST_PULL="$TEMP/pull"
SMART='hf.co/OBLITERATUS/Qwen3.8-27B-OBLITERATED:Q4_K_M'

printf '%s\n' kali-tutor kali-tutor-lite kali-codex-32k kali-codex-64k qwen3:1.7b > "$ACADEMY_TEST_MODELS"
[[ "$(ACADEMY_MEM_KB=16000000 bash "$ROOT/bin/academy-model" resolve tutor)" == kali-tutor ]]
printf '%s\n' "$SMART" >> "$ACADEMY_TEST_MODELS"
[[ "$(ACADEMY_MEM_KB=32000000 bash "$ROOT/bin/academy-model" resolve tutor)" == "$SMART" ]]
[[ "$(ACADEMY_MEM_KB=32000000 bash "$ROOT/bin/academy-model" resolve codex)" == "$SMART" ]]
bash "$ROOT/bin/academy-model" set smart >/dev/null
[[ "$(ACADEMY_MEM_KB=4000000 bash "$ROOT/bin/academy-model" resolve tutor)" == kali-tutor-lite ]]
[[ "$(ACADEMY_MEM_KB=4000000 bash "$ROOT/bin/academy-model" resolve codex)" == qwen3:1.7b ]]
bash "$ROOT/bin/academy-model" set fast codex >/dev/null
[[ "$(ACADEMY_MEM_KB=32000000 bash "$ROOT/bin/academy-model" resolve tutor)" == "$SMART" ]]
[[ "$(ACADEMY_MEM_KB=32000000 bash "$ROOT/bin/academy-model" resolve codex)" == kali-codex-64k ]]
grep -vF "$SMART" "$ACADEMY_TEST_MODELS" > "$TEMP/models.new" && mv "$TEMP/models.new" "$ACADEMY_TEST_MODELS"
printf 'y\n' | ACADEMY_MEM_KB=32000000 ACADEMY_FREE_KB=30000000 bash "$ROOT/bin/academy-model" install smart >/dev/null
[[ "$(cat "$ACADEMY_TEST_PULL")" == "$SMART" ]]
status="$(KALI_ACADEMY_ROOT="$ROOT" ACADEMY_MEM_KB=32000000 bash "$ROOT/bin/academy" model status)"
grep -Fq "$SMART" <<< "$status"
! grep -Fq "$SMART" "$ROOT/install.sh"
echo "Model self-test passed."
