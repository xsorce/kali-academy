#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OLLAMA_VERSION="0.33.1"
OLLAMA_INSTALL_SHA256="25f64b810b947145095956533e1bdf56eacea2673c55a7e586be4515fc882c9f"
CODEX_VERSION="0.150.1"
QWEN_FAST_MODEL="qwen3:4b"
QWEN_FAST_ID="359d7dd4bcda"
QWEN_LITE_MODEL="qwen3:1.7b"
QWEN_LITE_ID="8f68893c685c"
OLLAMA_INSTALLER=""

cleanup() { [[ -z "$OLLAMA_INSTALLER" ]] || rm -f -- "$OLLAMA_INSTALLER"; }
trap cleanup EXIT

if [[ "$EUID" -eq 0 ]]; then
  echo "Run as your normal Kali user. The script will request sudo."
  exit 1
fi

USER_NAME="$(id -un)"
[[ "$USER_NAME" =~ ^[a-z_][a-z0-9_.-]*[$]?$ && "$(id -u "$USER_NAME")" -eq "$EUID" ]] || {
  echo "Unable to validate the current non-root user." >&2; exit 1;
}
passwd_entry="$(getent passwd "$USER_NAME")"
[[ -n "$passwd_entry" && "$(grep -c '^' <<< "$passwd_entry")" -eq 1 ]] || {
  echo "Unable to resolve one passwd entry for $USER_NAME." >&2; exit 1;
}
HOME_DIR="$(cut -d: -f6 <<< "$passwd_entry")"
[[ "$HOME_DIR" == /* && "$HOME_DIR" != / && "$HOME_DIR" != /root && -d "$HOME_DIR" ]] || {
  echo "Unsafe home directory for $USER_NAME: $HOME_DIR" >&2; exit 1;
}
[[ "$(stat -c %u "$HOME_DIR")" -eq "$EUID" && "$(readlink -f "$HOME")" == "$(readlink -f "$HOME_DIR")" ]] || {
  echo "HOME does not belong to or match the current user." >&2; exit 1;
}

storage_preflight() {
  local label="$1" minimum_gb="$2" available_kb
  available_kb="$(df -Pk -- "$HOME_DIR" | awk 'NR == 2 {print $4}')"
  [[ "$available_kb" =~ ^[0-9]+$ ]] || { echo "Cannot determine free space before $label." >&2; exit 1; }
  printf 'Storage preflight (%s): %.1f GB free; %.0f GB required.\n' "$label" "$((available_kb / 1024))e-3" "$minimum_gb"
  if (( available_kb < 10 * 1024 * 1024 )); then
    echo "CRITICAL: less than 10 GB free. Installation stopped before $label." >&2
    exit 1
  fi
  (( available_kb >= minimum_gb * 1024 * 1024 )) || {
    echo "Insufficient free space before $label; keep at least ${minimum_gb} GB free." >&2; exit 1;
  }
}

verify_model() {
  local model="$1" expected="$2" actual
  actual="$(ollama list | awk -v model="$model" '$1 == model {print $2; exit}')"
  [[ "$actual" == "$expected"* ]] || {
    echo "Model verification failed for $model: expected ID $expected, got ${actual:-missing}." >&2; exit 1;
  }
}

echo "== Kali Academy v2 installer =="
sudo -v

echo "[1/9] Packages"
storage_preflight "APT packages" 20
sudo apt update
sudo DEBIAN_FRONTEND=noninteractive apt install -y \
  curl ca-certificates git gh jq fzf ripgrep bat tmux tree zoxide \
  htop btop fastfetch less nano vim shellcheck man-db \
  python3 python3-pip python3-rich build-essential rsync unzip p7zip-full \
  file lsof strace procps pciutils usbutils inxi lm-sensors \
  iproute2 net-tools dnsutils traceroute mtr-tiny nmap tcpdump tshark wireshark \
  arp-scan ethtool iw wavemon rfkill aircrack-ng iperf3 network-manager \
  smartmontools nvme-cli gparted testdisk gddrescue ntfs-3g exfatprogs ufw \
  dosfstools btrfs-progs xfsprogs e2fsprogs lvm2 mdadm parted hdparm \
  memtester dislocker chntpw docker.io

if apt-cache show starship >/dev/null 2>&1; then
  sudo DEBIAN_FRONTEND=noninteractive apt install -y starship || echo "Optional starship prompt was not installed."
else
  echo "Optional starship prompt is unavailable in this Kali release; continuing without it."
fi

sudo systemctl enable --now docker
sudo usermod -aG docker "$USER_NAME" || true
sudo usermod -aG wireshark "$USER_NAME" || true

echo "[2/9] Ollama"
storage_preflight "Ollama download" 12
if ! command -v ollama >/dev/null 2>&1; then
  OLLAMA_INSTALLER="$(mktemp)"
  curl -fL "https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/install.sh" -o "$OLLAMA_INSTALLER"
  printf '%s  %s\n' "$OLLAMA_INSTALL_SHA256" "$OLLAMA_INSTALLER" | sha256sum -c -
  echo "Installing reviewed Ollama release v$OLLAMA_VERSION from its verified installer."
  OLLAMA_VERSION="$OLLAMA_VERSION" sh "$OLLAMA_INSTALLER"
fi
sudo systemctl enable --now ollama
ollama_ready=0
for _ in $(seq 1 20); do
  if ollama list >/dev/null 2>&1; then ollama_ready=1; break; fi
  sleep 1
done
(( ollama_ready )) || { echo "Ollama is still unavailable after 20 readiness checks; installation stopped." >&2; exit 1; }

echo "[3/9] Qwen"
storage_preflight "default Qwen models" 15
ollama pull "$QWEN_FAST_MODEL"
verify_model "$QWEN_FAST_MODEL" "$QWEN_FAST_ID"
ollama pull "$QWEN_LITE_MODEL"
verify_model "$QWEN_LITE_MODEL" "$QWEN_LITE_ID"
ollama create kali-tutor -f "$ROOT/models/KaliTutor.Modelfile"
ollama create kali-tutor-lite -f "$ROOT/models/KaliTutorLite.Modelfile"
ollama create kali-codex -f "$ROOT/models/KaliCodex.Modelfile"

echo "[4/9] Codex CLI"
storage_preflight "Codex CLI/npm" 11
if ! command -v codex >/dev/null 2>&1 || [[ "$(codex --version 2>/dev/null || true)" != "codex-cli $CODEX_VERSION" ]]; then
  if command -v npm >/dev/null 2>&1; then
    sudo npm install -g "@openai/codex@$CODEX_VERSION"
  else
    echo "Node/npm not found; installing nodejs/npm for Codex CLI."
    sudo apt install -y nodejs npm
    sudo npm install -g "@openai/codex@$CODEX_VERSION"
  fi
fi

echo "[5/9] Academy files"
"$ROOT/apply.sh"

echo "[6/9] Offline documentation"
storage_preflight "offline documentation" 13
if ! python3 "$ROOT/academy/docs.py" update; then
  echo "Kali docs download unavailable; indexing installed local docs only."
  python3 "$ROOT/academy/docs.py" build
fi

echo "[7/9] Personal state"
mkdir -p "$HOME_DIR/.config/kali-academy" "$HOME_DIR/.local/share/kali-academy" \
  "$HOME_DIR/Academy/notes" "$HOME_DIR/Academy/backups" "$HOME_DIR/Academy/workspace" \
  "$HOME_DIR/Projects"

if [[ ! -f "$HOME_DIR/.config/kali-academy/profile.json" ]]; then
  cp "$ROOT/config/default-profile.json" "$HOME_DIR/.config/kali-academy/profile.json"
fi

echo "[8/9] Shell defaults"
touch "$HOME_DIR/.zshrc" "$HOME_DIR/.bashrc"

if ! grep -q '# KALI_ACADEMY_V2' "$HOME_DIR/.zshrc"; then
  cat >> "$HOME_DIR/.zshrc" <<'EOF'

# KALI_ACADEMY_V2
export PATH="$HOME/.local/bin:$PATH"
command -v zoxide >/dev/null 2>&1 && eval "$(zoxide init zsh)"
command -v starship >/dev/null 2>&1 && eval "$(starship init zsh)"
alias ll='ls -lah'
EOF
fi

if ! grep -q '# KALI_ACADEMY_V2' "$HOME_DIR/.bashrc"; then
  cat >> "$HOME_DIR/.bashrc" <<'EOF'

# KALI_ACADEMY_V2
export PATH="$HOME/.local/bin:$PATH"
command -v zoxide >/dev/null 2>&1 && eval "$(zoxide init bash)"
command -v starship >/dev/null 2>&1 && eval "$(starship init bash)"
alias ll='ls -lah'
EOF
fi

mkdir -p "$HOME_DIR/.config/autostart"
if command -v xfce4-terminal >/dev/null 2>&1 && [[ ! -e "$HOME_DIR/.config/autostart/kali-academy.desktop" ]]; then
  cat > "$HOME_DIR/.config/autostart/kali-academy.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Kali Academy
Comment=Pip's learning dashboard
Exec=xfce4-terminal --title=Kali-Academy --command=$HOME_DIR/.local/bin/academy
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
fi

echo "[9/9] Cyber range images"
storage_preflight "Docker lab images" 20
LAB_VERSION="$(cat "$ROOT/VERSION")"
sudo docker pull 'debian:bookworm-slim@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171'
sudo docker pull 'bkimminich/juice-shop:v20.2.0@sha256:8739101ade29358abb5469ee66ae78e582c97ed0a5543a4ad102e5fa5193526b'
sudo docker build -t "kali-academy-target:$LAB_VERSION" "$ROOT/labs/linux-target"
sudo docker build -t "kali-academy-tools:$LAB_VERSION" "$ROOT/labs/net-tools"

sudo chown -R "$USER_NAME":"$USER_NAME" \
  "$HOME_DIR/.config/kali-academy" "$HOME_DIR/.local/share/kali-academy" "$HOME_DIR/Academy" "$HOME_DIR/Projects"

echo
echo "Kali Academy installed."
echo "Your learner name is xs. Pip is your mascot."
echo
echo "IMPORTANT: your Kali login password is NOT stored here."
echo "Choose it during the Kali installer, or change it later with:"
echo "  academy-passwd"
echo
echo "Reboot once for Docker/Wireshark group membership, then run:"
echo "  academy"
