#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

NOTES_DIR = Path.home() / "Academy" / "notes"
STORE = NOTES_DIR / "notes.jsonl"
PRIVACY_NOTE = NOTES_DIR / "ABOUT-PIP.txt"
MAX_NOTES = 500
MAX_LENGTH = 500
SECRET_PATTERNS = (
    r"(?i)\b(password|passwd|passphrase|token|api[_ -]?key|secret|wifi[_ -]?key|psk|authorization|bearer)\b\s*(?:is|[:=])\s*\S+",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"\bgh[pousr]_[A-Za-z0-9]{20,}\b",
    r"\bsk-[A-Za-z0-9_-]{20,}\b",
    r"://[^\s/:]+:[^\s/@]+@",
)
PRIVACY_TEXT = """WHAT PIP CAN ACCESS

Kali Academy reads your local learner profile, progress, knowledge confidence, Command Book, and notes.
When you use Ask Pip or ai with a question, up to three relevant notes may be included in the prompt sent to local Ollama.
Pip does not automatically read browser data, global shell history, passwords, tokens, Wi-Fi keys, or unrelated files.
Mission command output stays local and is not sent to Qwen unless you explicitly include it in a question.
Notes stay under ~/Academy/notes/. They are not uploaded or committed to Git.
Do not put passwords, tokens, private keys, Wi-Fi credentials, or other secrets in notes.
"""

class UnsafeNote(ValueError):
    pass

def ensure_store():
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.chmod(0o700)
    if not PRIVACY_NOTE.exists():
        PRIVACY_NOTE.write_text(PRIVACY_TEXT, encoding="utf-8")
        PRIVACY_NOTE.chmod(0o600)

def load_notes():
    ensure_store()
    if not STORE.exists():
        return []
    notes = []
    for line in STORE.read_text().splitlines():
        try:
            item = json.loads(line)
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                notes.append(item)
        except json.JSONDecodeError:
            continue
    return notes

def validate_note(text):
    text = " ".join(text.split()).strip()
    if not text:
        raise ValueError("Note text is empty.")
    if len(text) > MAX_LENGTH:
        raise ValueError(f"Notes are limited to {MAX_LENGTH} characters.")
    if any(re.search(pattern, text) for pattern in SECRET_PATTERNS):
        raise UnsafeNote("This looks like a password, token, key, or other secret; it was not saved.")
    return text

def add_note(text, category="personal observation", lesson=""):
    text = validate_note(text)
    notes = load_notes()
    if len(notes) >= MAX_NOTES:
        raise ValueError(f"The local notebook is capped at {MAX_NOTES} notes; archive old notes before adding more.")
    item = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "category": category,
        "lesson": lesson,
        "text": text,
    }
    with STORE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=True) + "\n")
    STORE.chmod(0o600)
    return item

def search_notes(query):
    words = {word for word in re.findall(r"[a-z0-9-]+", query.casefold()) if len(word) > 2}
    matches = []
    for note in load_notes():
        haystack = f"{note.get('category', '')} {note.get('lesson', '')} {note['text']}".casefold()
        score = sum(word in haystack for word in words)
        if not words or score:
            matches.append((score, note))
    return [note for _, note in sorted(matches, key=lambda pair: (pair[0], pair[1].get("at", "")), reverse=True)]

def relevant_notes(query):
    return search_notes(query)[:3]

def format_note(note):
    date = note.get("at", "unknown")[:10]
    context = f" - {note['lesson']}" if note.get("lesson") else ""
    return f"[{date}] [{note.get('category', 'note')}]{context}: {note['text']}"

def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    action = args.pop(0) if args else "list"
    try:
        if action == "add":
            print(f"Saved: {format_note(add_note(' '.join(args)))}")
        elif action == "list":
            notes = load_notes()[-20:]
            print("\n".join(format_note(note) for note in notes) if notes else "No notes yet.")
            print(f"\nPrivacy: {PRIVACY_NOTE}")
        elif action in ("search", "relevant"):
            notes = relevant_notes(" ".join(args)) if action == "relevant" else search_notes(" ".join(args))
            print("\n".join(format_note(note) for note in notes))
        else:
            raise ValueError("Usage: notes [search QUERY]")
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
