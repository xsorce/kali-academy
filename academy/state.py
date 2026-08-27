import json
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl

from content import COMMAND_BOOK, LESSONS, QUESTS, SIDE_MISSIONS, SKILLS

CONFIG_DIR = Path.home() / ".config" / "kali-academy"
DATA_DIR = Path.home() / ".local" / "share" / "kali-academy"
PROFILE_PATH = CONFIG_DIR / "profile.json"
STATE_PATH = DATA_DIR / "state.json"
STATE_SCHEMA_VERSION = 3
ALL_CONCEPTS = sorted({concept for item in LESSONS + SIDE_MISSIONS + QUESTS for concept in item.get("concepts", [])})

DEFAULT_STATE = {
    "schema_version": STATE_SCHEMA_VERSION,
    "xp": 0,
    "level": 1,
    "completed_lessons": [],
    "completed_quests": [],
    "achievements": [],
    "skills": {skill: int(skill in ("linux", "shell")) for skill in SKILLS},
    "knowledge": {concept: 0.0 for concept in ALL_CONCEPTS},
    "hints": {},
    "history": [],
    "command_knowledge": {},
}

def ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def clone(value):
    return json.loads(json.dumps(value))

@contextmanager
def file_lock(path):
    ensure_dirs()
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+b") as handle:
        if os.name == "nt":
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

def corrupt_backup(path):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup = path.with_name(f"{path.name}.corrupt-{stamp}-{os.getpid()}")
    os.replace(path, backup)
    print(f"WARNING: invalid {path.name} preserved as {backup}; safe defaults loaded.", file=sys.stderr)
    return backup

def load_json_unlocked(path, default):
    if not path.exists():
        return clone(default), False
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, type(default)):
            raise ValueError("unexpected JSON type")
        return value, False
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        backup = corrupt_backup(path)
        print(f"WARNING: recovery reason: {error}; original data remains at {backup}.", file=sys.stderr)
        return clone(default), True

def save_json_unlocked(path, data):
    ensure_dirs()
    fd, stage_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(stage_name, path)
        try:
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError:
            pass
    finally:
        try:
            os.unlink(stage_name)
        except FileNotFoundError:
            pass

def load_json(path, default):
    with file_lock(path):
        return load_json_unlocked(path, default)[0]

def save_json(path, data):
    with file_lock(path):
        save_json_unlocked(path, data)

def load_profile(default_profile):
    with file_lock(PROFILE_PATH):
        profile, recovered = load_json_unlocked(PROFILE_PATH, default_profile)
        if recovered or not PROFILE_PATH.exists():
            save_json_unlocked(PROFILE_PATH, profile)
        return profile

def save_profile(profile):
    save_json(PROFILE_PATH, profile)

def load_state():
    with file_lock(STATE_PATH):
        state, recovered = load_json_unlocked(STATE_PATH, DEFAULT_STATE)
        original = clone(state)
        if migrate_state(state):
            if not recovered and STATE_PATH.exists():
                snapshot_dir = DATA_DIR / "state-snapshots"
                snapshot_dir.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
                save_json_unlocked(snapshot_dir / f"state-before-schema-{STATE_SCHEMA_VERSION}-{stamp}.json", original)
            save_json_unlocked(STATE_PATH, state)
        elif recovered:
            save_json_unlocked(STATE_PATH, state)
        return state

def migrate_state(state):
    changed = False
    skills = state.setdefault("skills", {})
    for skill in SKILLS:
        old = skills.get("bash" if skill == "shell" else "security" if skill == "packets" else skill, 0)
        if skill not in skills:
            skills[skill] = old
            changed = True

    knowledge = state.setdefault("knowledge", {})
    for concept in ALL_CONCEPTS:
        try:
            value = max(0.0, min(1.0, float(knowledge.get(concept, 0.0))))
        except (TypeError, ValueError):
            value = 0.0
        if knowledge.get(concept) != value:
            knowledge[concept] = value
            changed = True

    history = state.setdefault("history", [])
    state.setdefault("hints", {})
    try:
        version = int(state.get("schema_version", 0))
    except (TypeError, ValueError):
        version = 0
        changed = True
    if version < 2:
        for kind, items in (("lesson", LESSONS), ("quest", QUESTS)):
            completed = set(state.get(f"completed_{kind}s", []))
            for item in items:
                if item["id"] in completed:
                    for concept in item.get("concepts", []):
                        knowledge[concept] = max(knowledge[concept], 0.2)
                    history.append({"type": kind, "id": item["id"], "at": None, "xp": None, "verified": False, "hints": 0, "migrated": True})
        changed = True
    command_knowledge = state.setdefault("command_knowledge", {})
    for command, value in list(command_knowledge.items()):
        if command not in COMMAND_BOOK:
            del command_knowledge[command]
            changed = True
            continue
        try:
            count = max(0, int(value.get("practice_count", 0) if isinstance(value, dict) else value))
        except (TypeError, ValueError):
            count = 0
        normalized = {
            "practice_count": count,
            "last_practiced": value.get("last_practiced") if isinstance(value, dict) else None,
        }
        if isinstance(value, dict) and value.get("related_lesson"):
            normalized["related_lesson"] = value["related_lesson"]
        if value != normalized:
            command_knowledge[command] = normalized
            changed = True
    if version < 3:
        changed = True
    if version < STATE_SCHEMA_VERSION:
        state["schema_version"] = STATE_SCHEMA_VERSION
        changed = True
    return changed

def save_state(state):
    save_json(STATE_PATH, state)

def update_state(current, mutation):
    with file_lock(STATE_PATH):
        if STATE_PATH.exists():
            latest, _ = load_json_unlocked(STATE_PATH, DEFAULT_STATE)
            migrate_state(latest)
        else:
            latest = clone(current)
        result = mutation(latest)
        save_json_unlocked(STATE_PATH, latest)
    current.clear()
    current.update(clone(latest))
    return result

def level_for_xp(xp):
    # Gentle early progression; increasingly expensive levels.
    level = 1
    threshold = 250
    remaining = xp
    while remaining >= threshold:
        remaining -= threshold
        level += 1
        threshold = int(threshold * 1.28)
    return level, remaining, threshold

def add_xp(state, amount):
    def mutation(latest):
        before = latest.get("level", 1)
        latest["xp"] = max(0, int(latest.get("xp", 0)) + int(amount))
        level, _, _ = level_for_xp(latest["xp"])
        latest["level"] = level
        return level > before
    return update_state(state, mutation)

def record_hint(state, kind, item_id):
    def mutation(latest):
        key = f"{kind}:{item_id}"
        latest.setdefault("hints", {})[key] = latest.setdefault("hints", {}).get(key, 0) + 1
    update_state(state, mutation)

def record_practice(state, item, gain=0.05):
    def mutation(latest):
        for concept in item.get("concepts", []):
            knowledge = latest.setdefault("knowledge", {})
            knowledge[concept] = max(0.0, min(1.0, knowledge.get(concept, 0.0) + gain))
    update_state(state, mutation)

def practice_commands(state, commands, related_lesson):
    commands = [command for command in commands if command in COMMAND_BOOK]
    if not commands:
        return
    def mutation(latest):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        book = latest.setdefault("command_knowledge", {})
        for command in commands:
            entry = book.setdefault(command, {"practice_count": 0, "last_practiced": None})
            entry["practice_count"] = max(0, int(entry.get("practice_count", 0))) + 1
            entry["last_practiced"] = now
            entry["related_lesson"] = related_lesson
    update_state(state, mutation)

def command_status(entry):
    count = max(0, int((entry or {}).get("practice_count", 0)))
    return "new" if count == 0 else "learning" if count < 3 else "comfortable" if count < 6 else "mastered"

def complete_activity(state, kind, item, verified=False):
    def mutation(latest):
        completed = latest.setdefault(f"completed_{kind}s", [])
        if item["id"] in completed:
            return 0, False
        hint_count = latest.setdefault("hints", {}).get(f"{kind}:{item['id']}", 0)
        bonus = item["xp"] // 10 if kind == "quest" and hint_count == 0 else 0
        awarded = item["xp"] + bonus
        completed.append(item["id"])
        for skill in {item["skill"], *(concept.split(".", 1)[0] for concept in item.get("concepts", []))}:
            latest.setdefault("skills", {}).setdefault(skill, 0)
            latest["skills"][skill] += 1
        gain = 0.25 if verified else 0.15
        for concept in item.get("concepts", []):
            knowledge = latest.setdefault("knowledge", {})
            knowledge[concept] = min(1.0, knowledge.get(concept, 0.0) + gain)
        latest.setdefault("history", []).append({
            "type": kind, "id": item["id"], "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "xp": awarded, "verified": verified, "hints": hint_count,
        })
        before = latest.get("level", 1)
        latest["xp"] = max(0, int(latest.get("xp", 0)) + awarded)
        latest["level"], _, _ = level_for_xp(latest["xp"])
        return awarded, latest["level"] > before
    return update_state(state, mutation)
