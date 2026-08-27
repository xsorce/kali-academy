#!/usr/bin/env python3
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "academy"))
import notes

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp) / "notes"
    notes.NOTES_DIR = root
    notes.STORE = root / "notes.jsonl"
    notes.PRIVACY_NOTE = root / "ABOUT-PIP.txt"

    saved = notes.add_note("ip route shows the default gateway", "commands worth remembering", "Networking")
    assert saved["text"] == "ip route shows the default gateway"
    assert notes.search_notes("gateway")[0]["lesson"] == "Networking"
    assert notes.relevant_notes("route")
    assert notes.PRIVACY_NOTE.exists() and "local Ollama" in notes.PRIVACY_NOTE.read_text()
    try:
        notes.add_note("password is hunter2")
        raise AssertionError("secret note was accepted")
    except notes.UnsafeNote:
        pass
