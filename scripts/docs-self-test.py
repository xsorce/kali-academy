#!/usr/bin/env python3
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "academy"))
import docs

with tempfile.TemporaryDirectory() as temp:
    index = Path(temp) / "docs.sqlite3"
    docs.create_index([
        ("Kali Academy docs", "local/networking.md", "Routes", "A default route selects the next hop for destinations without a more specific route."),
        ("Bash documentation", "local/bash.txt", "Pipelines", "A pipeline connects standard output to standard input."),
    ], index)
    results = docs.search("default route", path=index)
    assert results and results[0][0] == "Kali Academy docs"
    docs.INDEX = index
    context = docs.relevant_context("pipeline standard output")
    assert "[DOCUMENTED FACT | Bash documentation | Pipelines]" in context
    assert "Local source: local/bash.txt" in context
