# What persists?

Because Kali is a normal full installation on the SSD, normal Linux settings persist automatically.

Examples:
- wallpaper;
- Xfce panels;
- terminal settings;
- browser settings;
- Wi-Fi profiles;
- Git repos;
- downloaded Ollama models;
- notes.

Academy personal state is deliberately separate from the repo.

```text
~/.config/kali-academy/profile.json
~/.local/share/kali-academy/state.json
~/Academy/notes/
```

## Profile

The default profile uses:

```json
"display_name": "xs",
"mascot_name": "Pip"
```

You can edit the local profile later without changing the GitHub project.

Do not add passwords or private credentials to it.

## Disable animation

For one launch:

```bash
ACADEMY_NO_ANIM=1 academy
```

or edit the local profile and set:

```json
"animations": false
```
