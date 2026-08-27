# Build Kali Academy from your Windows daily machine

For major development, use Codex on the Windows machine you use every day.

Why:
- faster iteration;
- easier GitHub access;
- you do not have to reboot into Kali just to change documentation/UI code;
- Git gives you a clean history before the changes reach your boot SSD.

## Suggested flow

```text
Windows
  ↓
edit repo with Codex
  ↓
git diff
  ↓
commit + push GitHub
  ↓
boot Kali SSD
  ↓
academy update
```

## First Codex task

Open Codex in the repo and give it:

```text
Read README.md and AGENTS.md first.

This is Kali Academy, a portable Kali Linux learning OS.
Learner name: xs.
Mascot: Pip.

Preserve personal state outside the repo.
Keep the terminal UI lightweight.
Before changing anything, inspect only the files relevant to the task.
After edits run ./scripts/self-test.sh and show me git diff --stat.

Do not install packages or modify my actual Windows/Kali system unless I explicitly ask.
```

## Updating Kali after a GitHub change

From any terminal on Kali:

```bash
academy update
```

The updater refuses a dirty or diverged source tree, fetches and shows incoming changes, asks before
continuing, backs up the installed app, performs a fast-forward-only pull, runs tests, applies
transactionally, and checks the active app. A failed activation restores the previous app; a failed
post-apply health check automatically rolls back to the exact pre-update backup. Each new app backup
contains a paired snapshot of profile, XP state, and notes, which manual or automatic rollback
restores with the matching code.

Use `academy rollback` for a manual app rollback and `academy version` to show the installed version.
Profile, XP, notes, and user settings live outside the app deployment and are not overwritten by a
normal apply.

Package-level changes should still go through a reviewed update to `install.sh`.
