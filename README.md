# Kali Academy

**Kali Academy** turns a portable Kali Linux SSD into an interactive Linux and cybersecurity
learning workstation.

It is intentionally not "Kali with every package." The system stays small enough to be practical,
fast enough to use on different PCs, and structured so you understand what it is doing.

Default learner name: **xs**  
Mascot: **Pip the penguin**

```text
     ( o>
    ///\
    \V_/_
      Pip
```

## What you get

- Kali Linux on a full external-SSD installation
- local Qwen through Ollama
- Codex CLI using local Qwen when desired
- Kali Academy terminal UI
- XP, levels, skills, quests and achievements
- a small private learner profile/knowledge base
- notes that persist locally
- resettable isolated Docker cyber range
- Panda PAU0E Wi-Fi diagnostics and passive learning workflow
- Git/GitHub tools
- PC rescue and recovery utilities
- fun but lightweight Zsh/terminal enhancements

## Important architecture

The Git repo contains **the Academy software and defaults**.

Your personal state stays outside the repo:

```text
~/.config/kali-academy/profile.json        learner profile
~/.local/share/kali-academy/state.json     XP/progress
~/Academy/notes/                            your notes
~/Projects/                                 your Git repos
```

Updating the project therefore does not overwrite your notes, XP, wallpaper choices, or profile.

## Recommended build workflow

### On your normal Windows machine

Use Codex to maintain and improve this repository. This is the easiest place to make substantial
changes because you already use that machine every day.

### On the Kali SSD

Clone/pull the repo and run:

```bash
./install.sh
```

For later user-level updates:

```bash
./apply.sh
```

Use:

```bash
academy-dev
```

to open Codex directly in the Academy source repo.

## Start here

1. Read [`docs/01-INSTALL-SSD.md`](docs/01-INSTALL-SSD.md)
2. Read [`docs/02-WINDOWS-CODEX-WORKFLOW.md`](docs/02-WINDOWS-CODEX-WORKFLOW.md)
3. Install Kali onto the SSD and choose your own password.
4. Clone this repo onto Kali.
5. Run `./install.sh`.
6. Reboot.
7. Run `academy`.

## Main commands

| Command | What it does |
|---|---|
| `academy` | Main interactive Academy UI |
| `ai` | Local Pip/Qwen tutor |
| `explain` | Explain a command or piped output |
| `cdx` | Local Codex + Qwen in current directory |
| `cdx-ro` | Read-only local Codex |
| `academy-dev` | Open Codex in Academy source |
| `academy update` | Review, back up, test, and transactionally fast-forward from GitHub |
| `academy rollback` | Restore the newest automatic Academy app backup |
| `academy version` | Show the installed Academy version |
| `academy-passwd` | Change your Kali password safely |
| `labctl` | Start/reset/enter isolated cyber range |
| `wifi-lab` | Wi-Fi/Panda learning and diagnostics |
| `rescue` | PC rescue/diagnostic menu |
| `usb-health` | Inspect current hardware and Academy health |
| `academy-models` | Manage optional local models |
| `academy model install smart` | Preflight and install the optional 27B smart model |
| `academy model set smart [tutor\|codex]` | Prefer smart independently for tutoring or Codex |
| `academy model status` | Show preferences, detected models, and active fallbacks |
| `academy storage` | Show space usage and confirmed cleanup options |
| `academy privacy [status|on|off]` | Inspect or reduce local-network exposure with recorded rollback |
| `academy knowledge` | Show concept confidence from weakest to strongest |
| `academy history` | Show lesson/quest completion and verified-XP history |
| `academy commands` | Open the optional Academy-only Command Book |
| `note "text"` | Save a small validated local note |
| `notes` | List recent local notes |
| `notes search QUERY` | Search the local notes knowledge base |
| `academy-docs` | Inspect, search, or refresh selected offline documentation |

## Storage target

A practical installation fits on a **128 GB SSD** when optional large models and recovery images
stay elsewhere.

Typical target:

```text
Kali + packages             30-50 GB
Default AI models             ~4 GB
Docker/labs                  5-15 GB
docs/repo/config             <5 GB
projects/rescue working     variable
-------------------------------------
normal working install       ~45-75 GB
```

The optional smart model is exactly
`hf.co/OBLITERATUS/Qwen3.8-27B-OBLITERATED:Q4_K_M` through Ollama's direct Hugging Face support.
It is never downloaded by `install.sh`; `academy model install smart` checks for at least 20 GB free
disk and 24 GB RAM before offering the approximately 16.8 GB download. When absent or unsuitable,
Academy uses Qwen3 4B normally and Qwen3 1.7B on low-resource systems. Tutor and Codex preferences
can be set separately.

Kali Academy warns below 20 GB free and treats below 10 GB as critical. Store recovery disk images
on another external disk, not on the 128 GB Academy SSD.

Offline Pip retrieval indexes only Academy docs, a shallow Markdown-only clone of the official Kali
docs, selected installed Bash/Git/systemd/networking references, and man-page names/descriptions.
The knowledge directory has a 3 GB safety ceiling; Wikipedia and general datasets are excluded.
