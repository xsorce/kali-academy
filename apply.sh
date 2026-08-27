#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.local/share/kali-academy/app"
APP_DIR="$(dirname "$DEST")"
BIN="$HOME/.local/bin"
BACKUP_DIR="$HOME/Academy/backups"
STAGE=""
MODE=apply
CREATE_BACKUP=1
umask 077

for argument in "$@"; do
  case "$argument" in
    --rollback) MODE=rollback ;;
    --backup-only) MODE=backup ;;
    --no-backup) CREATE_BACKUP=0 ;;
    *) echo "Usage: apply.sh [--backup-only|--rollback] [--no-backup]" >&2; exit 1 ;;
  esac
done

cleanup() { [[ -z "$STAGE" || ! -d "$STAGE" ]] || rm -rf -- "$STAGE"; }
trap cleanup EXIT

health_check() {
  if [[ -f "$1/scripts/health-check.sh" ]]; then bash "$1/scripts/health-check.sh"; else bash "$1/scripts/self-test.sh"; fi
}

refresh_docs() {
  [[ ! -f "$HOME/.local/share/kali-academy/knowledge/docs.sqlite3" ]] ||
    python3 "$DEST/academy/docs.py" build || echo "Warning: offline documentation index was not refreshed." >&2
}

sync_app() {
  rsync -a --delete \
    --exclude '.git' \
    --exclude '.env' --exclude '.env.*' \
    --exclude '*.key' --exclude '*.pem' --exclude '*.kdbx' \
    --exclude 'learner-snapshot' \
    "$1"/ "$2"/
}

snapshot_learner() {
  local snapshot="$1/learner-snapshot"
  mkdir -p "$snapshot"
  : > "$snapshot/manifest"
  if [[ -f "$HOME/.config/kali-academy/profile.json" ]]; then
    mkdir -p "$snapshot/config"; cp -a "$HOME/.config/kali-academy/profile.json" "$snapshot/config/"
    echo profile >> "$snapshot/manifest"
  fi
  if [[ -f "$HOME/.local/share/kali-academy/state.json" ]]; then
    mkdir -p "$snapshot/data"; cp -a "$HOME/.local/share/kali-academy/state.json" "$snapshot/data/"
    echo state >> "$snapshot/manifest"
  fi
  if [[ -d "$HOME/Academy/notes" ]]; then
    cp -a "$HOME/Academy/notes" "$snapshot/notes"
    echo notes >> "$snapshot/manifest"
  fi
}

restore_file() {
  local source="$1" target="$2" stage
  mkdir -p "$(dirname "$target")"
  stage="$(mktemp "$(dirname "$target")/.restore.XXXXXX")"
  cp -a "$source" "$stage"
  mv -f "$stage" "$target"
}

restore_learner() {
  local snapshot="$1/learner-snapshot" notes_stage="" notes_previous=""
  [[ "$HOME" == /* && "$HOME" != / ]] || { echo "Unsafe HOME; learner state was not changed." >&2; return 1; }
  [[ -f "$snapshot/manifest" ]] || { echo "Older backup has no learner snapshot; current learner state is unchanged." >&2; return 0; }
  if grep -qx profile "$snapshot/manifest"; then
    restore_file "$snapshot/config/profile.json" "$HOME/.config/kali-academy/profile.json"
  else
    rm -f -- "$HOME/.config/kali-academy/profile.json"
  fi
  if grep -qx state "$snapshot/manifest"; then
    restore_file "$snapshot/data/state.json" "$HOME/.local/share/kali-academy/state.json"
  else
    rm -f -- "$HOME/.local/share/kali-academy/state.json"
  fi
  if grep -qx notes "$snapshot/manifest"; then
    mkdir -p "$HOME/Academy"
    notes_stage="$(mktemp -d "$HOME/Academy/.notes.restore.XXXXXX")"
    cp -a "$snapshot/notes"/. "$notes_stage"/
    if [[ -d "$HOME/Academy/notes" ]]; then
      notes_previous="$(mktemp -d "$HOME/Academy/.notes.previous.XXXXXX")"; rmdir "$notes_previous"
      mv "$HOME/Academy/notes" "$notes_previous"
    fi
    mv "$notes_stage" "$HOME/Academy/notes"
    [[ -z "$notes_previous" ]] || rm -rf -- "$notes_previous"
  else
    rm -rf -- "$HOME/Academy/notes"
  fi
  echo "Learner profile, XP state, and notes restored from the paired snapshot."
}

backup_current() {
  [[ -d "$DEST" ]] || return 0
  local backup old=()
  mapfile -t old < <(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -name 'app-*' -printf '%T@ %p\n' | sort -nr | tail -n +5 | cut -d' ' -f2-)
  if ((${#old[@]})); then
    echo "Academy keeps at most five automatic backups."
    read -r -p "Remove ${#old[@]} oldest backup(s) before updating? [y/N] " answer
    [[ "$answer" =~ ^[Yy]$ ]] || { echo "Update cancelled; no backups deleted." >&2; return 1; }
    rm -rf -- "${old[@]}"
  fi
  backup="$(mktemp -d "$BACKUP_DIR/app-$(date +%Y%m%d-%H%M%S).XXXXXX")"
  sync_app "$DEST" "$backup"
  snapshot_learner "$backup"
  echo "Backup: $backup"
}

activate() {
  local previous=""
  if [[ -d "$DEST" ]]; then
    previous="$(mktemp -d "$APP_DIR/.app.previous.XXXXXX")"
    rmdir "$previous"
    mv "$DEST" "$previous"
  fi
  if ! mv "$STAGE" "$DEST" || ! health_check "$DEST"; then
    rm -rf -- "$DEST"
    [[ -z "$previous" ]] || mv "$previous" "$DEST"
    echo "Health check failed; previous app restored." >&2
    return 1
  fi
  STAGE=""
  [[ -z "$previous" ]] || rm -rf -- "$previous"
}

mkdir -p "$APP_DIR" "$BACKUP_DIR" "$BIN"

if [[ "$MODE" == backup ]]; then
  backup_current
  exit 0
fi

if [[ "$MODE" == rollback ]]; then
  BACKUP="${ACADEMY_ROLLBACK_BACKUP:-$(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -name 'app-*' -printf '%p\n' | sort | tail -n 1)}"
  [[ -d "$BACKUP" && "$BACKUP" == "$BACKUP_DIR"/app-* ]] || { echo "No valid Academy backup found." >&2; exit 1; }
  STAGE="$(mktemp -d "$APP_DIR/.app.new.XXXXXX")"
  sync_app "$BACKUP" "$STAGE"
  if ! health_check "$STAGE"; then
    restore_learner "$BACKUP"
    echo "Backup app health failed; code was unchanged and paired learner state was restored." >&2
    exit 1
  fi
  if (( CREATE_BACKUP )); then backup_current; fi
  if ! activate; then
    restore_learner "$BACKUP"
    echo "Code rollback failed; paired learner state was restored." >&2
    exit 1
  fi
  restore_learner "$BACKUP"
  health_check "$DEST"
  chmod +x "$DEST/apply.sh" "$DEST/bin/academy-rollback"
  refresh_docs
  echo "Rolled back Academy to: $BACKUP"
  exit 0
fi

bash "$ROOT/scripts/self-test.sh"
STAGE="$(mktemp -d "$APP_DIR/.app.new.XXXXXX")"

sync_app "$ROOT" "$STAGE"

health_check "$STAGE"
if (( CREATE_BACKUP )); then backup_current; fi
activate
chmod +x "$DEST"/*.sh "$DEST"/bin/* "$DEST"/scripts/*.sh

refresh_docs

for f in "$ROOT"/bin/*; do
  ln -sf "$DEST/bin/$(basename "$f")" "$BIN/$(basename "$f")"
done

echo "Applied Academy user-level update."
echo "Personal profile/XP/notes were not overwritten."
