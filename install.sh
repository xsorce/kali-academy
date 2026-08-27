#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
HOME_DIR="$(getent passwd "$USER_NAME" | cut -d: -f6)"

if [[ "$EUID" -eq 0 ]]; then
  echo "Run as your normal Kali user. The script will request sudo."
  exit 1
fi

echo "== Kali Academy v2 installer =="
sudo -v

echo "[1/9] Packages"
sudo apt update
sudo DEBIAN_FRONTEND=noninteractive apt install -y \
  curl ca-certificates git gh jq fzf ripgrep bat tmux tree zoxide starship \
  htop btop fastfetch less nano vim shellcheck man-db \
  python3 python3-pip python3-rich build-essential rsync unzip p7zip-full \
  file lsof strace procps pciutils usbutils inxi lm-sensors \
  iproute2 net-tools dnsutils traceroute mtr-tiny nmap tcpdump tshark wireshark \
  arp-scan ethtool iw wavemon rfkill aircrack-ng iperf3 network-manager \
  smartmontools nvme-cli gparted testdisk gddrescue ntfs-3g exfatprogs ufw \
  dosfstools btrfs-progs xfsprogs e2fsprogs lvm2 mdadm parted hdparm \
  memtester dislocker chntpw docker.io

sudo systemctl enable --now docker
sudo usermod -aG docker "$USER_NAME" || true
sudo usermod -aG wireshark "$USER_NAME" || true

echo "[2/9] Ollama"
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi
sudo systemctl enable --now ollama
for _ in $(seq 1 20); do ollama list >/dev/null 2>&1 && break; sleep 1; done

echo "[3/9] Qwen"
ollama pull qwen3:4b
ollama pull qwen3:1.7b
ollama create kali-tutor -f "$ROOT/models/KaliTutor.Modelfile"
ollama create kali-tutor-lite -f "$ROOT/models/KaliTutorLite.Modelfile"
ollama create kali-codex-32k -f "$ROOT/models/KaliCodex32.Modelfile"
ollama create kali-codex-64k -f "$ROOT/models/KaliCodex64.Modelfile"

echo "[4/9] Codex CLI"
if ! command -v codex >/dev/null 2>&1; then
  if command -v npm >/dev/null 2>&1; then
    sudo npm install -g @openai/codex
  else
    echo "Node/npm not found; installing nodejs/npm for Codex CLI."
    sudo apt install -y nodejs npm
    sudo npm install -g @openai/codex
  fi
fi

echo "[5/9] Academy files"
"$ROOT/apply.sh"

echo "[6/9] Offline documentation"
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
sudo docker pull debian:bookworm-slim
sudo docker pull bkimminich/juice-shop:latest
sudo docker build -t kali-academy-target "$ROOT/labs/linux-target"
sudo docker build -t kali-academy-tools "$ROOT/labs/net-tools"

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
