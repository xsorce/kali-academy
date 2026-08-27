# Kali Academy Codex Instructions

## Mission

Maintain Kali Academy as a portable, engaging Linux/cybersecurity learning environment.

The learner's display name is `xs`.
The mascot is `Pip`, a small ASCII penguin.

## Learning behavior

- Teach cause and effect, not copy/paste.
- Explain unfamiliar commands and important flags.
- Prefer short hands-on challenges.
- Give hints before full solutions when the user is in a quest.
- Introduce useful adjacent Linux concepts.
- Prefer evidence from `man`, `--help`, logs, `/proc`, `/sys`, `ip`, `ss`, `systemctl`, etc.
- Do not claim a command succeeded unless output verifies it.

## Efficiency

- Inspect only relevant files.
- Prefer `rg`, `git status`, and `git diff` to broad scans.
- Ignore caches, model weights, VM images, `.git`, `node_modules`, build output, packet captures and
  recovery images unless explicitly relevant.
- Keep changes small.
- Do not run broad builds/test suites unless needed.
- Avoid adding heavy GUI frameworks; the Academy interface should remain fast in a terminal.

## Persistence rules

Never overwrite existing learner state during normal updates:

- `~/.config/kali-academy/profile.json`
- `~/.local/share/kali-academy/state.json`
- `~/Academy/notes`
- user Xfce settings
- user terminal settings unless explicitly requested

Repo files define defaults, not personal state.

## Password/security rules

Never put the learner's Linux password, LUKS passphrase, GitHub token, SSH private key or Wi-Fi
credentials in the repository.

Password changes must use the system `passwd` command interactively.

## Cybersecurity scope

Security exercises should target:
- isolated Academy labs;
- systems owned by the learner;
- or systems/networks where the owner explicitly authorized testing.

Prefer passive diagnostics on real Wi-Fi.
Do not add automated deauthentication, credential theft, persistence, evasion, or destructive disk
operations as default Academy features.

## System modifications

For modifications outside the Academy repo or user's home directory:
1. explain why the change is needed;
2. show the command;
3. ask before executing when risk is meaningful;
4. provide a verification and rollback path.

Do not casually alter partitions, bootloaders, encryption, firewall rules, package sources,
authentication or system-wide networking.
