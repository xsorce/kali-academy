#!/usr/bin/env python3
import gzip
import html
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from itertools import chain
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = Path.home() / ".local" / "share" / "kali-academy" / "knowledge"
KALI_DOCS = KNOWLEDGE_DIR / "kali-docs"
INDEX = KNOWLEDGE_DIR / "docs.sqlite3"
KALI_DOCS_URL = "https://gitlab.com/kalilinux/documentation/kali-docs.git"
MAX_FILE_BYTES = 1_000_000
MAX_TEXT_BYTES = 256 * 1024 * 1024
MAX_CLONE_BYTES = 1_500_000_000
MAX_TOTAL_BYTES = 3_000_000_000
MIN_DOWNLOAD_FREE_BYTES = 10 * 1024 * 1024 * 1024
TEXT_SUFFIXES = {".md", ".txt", ".rst", ".html", ".htm", ".info", ".gz"}
STOP_WORDS = {"what", "when", "where", "which", "with", "from", "that", "this", "does", "have", "into", "your", "about", "how", "why"}

LOCAL_SOURCES = (
    ("Kali Academy docs", APP_ROOT / "docs", None),
    ("Kali official docs", KALI_DOCS, None),
    ("Bash documentation", Path("/usr/share/doc/bash"), None),
    ("Bash documentation", Path("/usr/share/info"), "bash"),
    ("Git documentation", Path("/usr/share/doc/git"), None),
    ("Git documentation", Path("/usr/share/doc/git-man"), None),
    ("systemd documentation", Path("/usr/share/doc/systemd"), None),
    ("Linux networking reference", Path("/usr/share/doc/iproute2"), None),
    ("Linux networking reference", Path("/usr/share/doc/network-manager"), None),
    ("Linux networking reference", Path("/usr/share/doc/iw"), None),
)

GENERATED_SOURCES = (
    ("Bash documentation", "bash built-in help", ["bash", "-c", "help"]),
    ("Git documentation", "git command list", ["git", "help", "-a"]),
    ("systemd documentation", "systemctl help", ["systemctl", "--help"]),
    ("systemd documentation", "journalctl help", ["journalctl", "--help"]),
    ("Linux networking reference", "ip help", ["ip", "help"]),
    ("Linux networking reference", "ss help", ["ss", "--help"]),
    ("Linux networking reference", "dig help", ["dig", "-h"]),
    ("Linux networking reference", "iw help", ["iw", "help"]),
)

def directory_size(path):
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file()) if path.exists() else 0

def require_download_space(path=KNOWLEDGE_DIR, free_bytes=None):
    path.mkdir(parents=True, exist_ok=True)
    available = shutil.disk_usage(path).free if free_bytes is None else free_bytes
    if available < MIN_DOWNLOAD_FREE_BYTES:
        raise RuntimeError("Offline documentation update stopped: less than 10 GB free.")

def sync_kali_docs():
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    require_download_space()
    if KALI_DOCS.exists():
        subprocess.run(["git", "-C", str(KALI_DOCS), "pull", "--ff-only"], check=True)
    else:
        stage = KNOWLEDGE_DIR / ".kali-docs.new"
        if stage.exists():
            shutil.rmtree(stage)
        try:
            subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--no-checkout", KALI_DOCS_URL, str(stage)], check=True)
            subprocess.run(["git", "-C", str(stage), "sparse-checkout", "init", "--no-cone"], check=True)
            subprocess.run(["git", "-C", str(stage), "sparse-checkout", "set", "*.md"], check=True)
            subprocess.run(["git", "-C", str(stage), "checkout"], check=True)
            if directory_size(stage) > MAX_CLONE_BYTES:
                raise RuntimeError("Kali docs checkout exceeded the 1.5 GB safety limit.")
            stage.replace(KALI_DOCS)
        except Exception:
            if stage.exists():
                shutil.rmtree(stage)
            raise
    if directory_size(KNOWLEDGE_DIR) > MAX_TOTAL_BYTES:
        raise RuntimeError("Offline knowledge exceeds the 3 GB safety limit.")

def read_text(path):
    if path.stat().st_size > MAX_FILE_BYTES:
        return ""
    try:
        data = gzip.open(path, "rt", encoding="utf-8", errors="ignore").read() if path.suffix == ".gz" else path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, EOFError):
        return ""
    if path.suffix in (".html", ".htm") or path.name.endswith((".html.gz", ".htm.gz")):
        data = html.unescape(re.sub(r"<[^>]+>", " ", data))
    return re.sub(r"\s+", " ", data).strip()

def iter_source_files():
    for source, root, prefix in LOCAL_SOURCES:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            name = path.name.casefold()
            if prefix and not name.startswith(prefix) or "changelog" in name or name == "copyright":
                continue
            text = read_text(path)
            if text:
                yield source, str(path), path.stem, text

def generated_documents():
    for source, title, command in GENERATED_SOURCES:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=15)
            text = (result.stdout + result.stderr).strip()
            if text:
                yield source, "command:" + " ".join(command), title, text
        except (OSError, subprocess.TimeoutExpired):
            continue
    try:
        result = subprocess.run(["apropos", "."], capture_output=True, text=True, timeout=30)
        if result.stdout:
            yield "man page names and descriptions", "command:apropos .", "Installed man pages", result.stdout[:5_000_000]
    except (OSError, subprocess.TimeoutExpired):
        pass

def chunks(text, size=1800, overlap=200):
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            end = boundary if boundary > start + size // 2 else end
        yield text[start:end]
        if end == len(text):
            break
        start = end - overlap

def create_index(documents, path=None):
    path = INDEX if path is None else path
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = path.with_suffix(path.suffix + ".tmp")
    if stage.exists():
        stage.unlink()
    connection = sqlite3.connect(stage)
    try:
        connection.execute("CREATE VIRTUAL TABLE docs USING fts5(source UNINDEXED, path UNINDEXED, title, body)")
        total = 0
        for source, source_path, title, text in documents:
            total += len(text.encode("utf-8", errors="ignore"))
            if total > MAX_TEXT_BYTES:
                break
            connection.executemany("INSERT INTO docs VALUES (?, ?, ?, ?)", ((source, source_path, title, chunk) for chunk in chunks(text)))
        connection.commit()
    finally:
        connection.close()
    projected_size = directory_size(path.parent) - (path.stat().st_size if path.exists() else 0)
    if projected_size > MAX_TOTAL_BYTES:
        stage.unlink()
        raise RuntimeError("Offline knowledge exceeds the 3 GB safety limit.")
    os.replace(stage, path)

def build_index():
    create_index(chain(iter_source_files(), generated_documents()))
    if directory_size(KNOWLEDGE_DIR) > MAX_TOTAL_BYTES:
        raise RuntimeError("Offline knowledge exceeds the 3 GB safety limit.")

def search(query, limit=4, path=None):
    path = INDEX if path is None else path
    if not path.exists():
        build_index()
    words = [word for word in re.findall(r"[a-z0-9_-]+", query.casefold()) if len(word) > 2 and word not in STOP_WORDS][:10]
    if not words:
        return []
    expression = " OR ".join(f'"{word}"*' for word in words)
    connection = sqlite3.connect(path)
    try:
        rows = connection.execute(
            "SELECT source, path, title, snippet(docs, 3, '', '', ' ... ', 45) FROM docs WHERE docs MATCH ? ORDER BY bm25(docs) LIMIT ?",
            (expression, limit),
        ).fetchall()
    finally:
        connection.close()
    return rows

def relevant_context(query):
    blocks = []
    for source, path, title, excerpt in search(query, 3):
        blocks.append(f"[DOCUMENTED FACT | {source} | {title}]\n{excerpt.strip()}\nLocal source: {path}")
    return "\n\n".join(blocks)[:3500]

def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    action = args.pop(0) if args else "status"
    try:
        if action == "update":
            sync_kali_docs()
            build_index()
            print("Offline documentation updated.")
        elif action == "build":
            build_index()
            print("Offline documentation indexed.")
        elif action in ("search", "relevant"):
            print(relevant_context(" ".join(args)))
        elif action == "status":
            print(f"Knowledge storage: {directory_size(KNOWLEDGE_DIR) / 1024 / 1024:.1f} MB")
            print(f"Index: {INDEX}")
            print(f"Kali docs: {'installed' if KALI_DOCS.exists() else 'not cloned'}")
        else:
            raise ValueError("Usage: academy-docs [update|build|search QUERY|status]")
    except (OSError, RuntimeError, sqlite3.Error, subprocess.CalledProcessError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
