import json
from datetime import datetime, timezone
from pathlib import Path

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

def load_json(path, default):
    ensure_dirs()
    if not path.exists():
        return json.loads(json.dumps(default))
    try:
        return json.loads(path.read_text())
    except Exception:
        return json.loads(json.dumps(default))

def save_json(path, data):
    ensure_dirs()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)

def load_profile(default_profile):
    ensure_dirs()
    if not PROFILE_PATH.exists():
        save_json(PROFILE_PATH, default_profile)
    return load_json(PROFILE_PATH, default_profile)

def save_profile(profile):
    save_json(PROFILE_PATH, profile)

def load_state():
    state = load_json(STATE_PATH, DEFAULT_STATE)
    if migrate_state(state):
        save_state(state)
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
    version = int(state.get("schema_version", 0))
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
    before = state.get("level", 1)
    state["xp"] = max(0, int(state.get("xp", 0)) + int(amount))
    level, _, _ = level_for_xp(state["xp"])
    state["level"] = level
    save_state(state)
    return level > before

def record_hint(state, kind, item_id):
    key = f"{kind}:{item_id}"
    state.setdefault("hints", {})[key] = state.setdefault("hints", {}).get(key, 0) + 1
    save_state(state)

def record_practice(state, item, gain=0.05):
    for concept in item.get("concepts", []):
        state.setdefault("knowledge", {})[concept] = max(0.0, min(1.0, state["knowledge"].get(concept, 0.0) + gain))
    save_state(state)

def practice_commands(state, commands, related_lesson):
    commands = [command for command in commands if command in COMMAND_BOOK]
    if not commands:
        return
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    book = state.setdefault("command_knowledge", {})
    for command in commands:
        entry = book.setdefault(command, {"practice_count": 0, "last_practiced": None})
        entry["practice_count"] = max(0, int(entry.get("practice_count", 0))) + 1
        entry["last_practiced"] = now
        entry["related_lesson"] = related_lesson
    save_state(state)

def command_status(entry):
    count = max(0, int((entry or {}).get("practice_count", 0)))
    return "new" if count == 0 else "learning" if count < 3 else "comfortable" if count < 6 else "mastered"

def complete_activity(state, kind, item, verified=False):
    completed = state.setdefault(f"completed_{kind}s", [])
    if item["id"] in completed:
        return 0, False
    hint_count = state.setdefault("hints", {}).get(f"{kind}:{item['id']}", 0)
    bonus = item["xp"] // 10 if kind == "quest" and hint_count == 0 else 0
    awarded = item["xp"] + bonus
    completed.append(item["id"])
    for skill in {item["skill"], *(concept.split(".", 1)[0] for concept in item.get("concepts", []))}:
        state.setdefault("skills", {}).setdefault(skill, 0)
        state["skills"][skill] += 1
    gain = 0.25 if verified else 0.15
    for concept in item.get("concepts", []):
        state.setdefault("knowledge", {})[concept] = min(1.0, state["knowledge"].get(concept, 0.0) + gain)
    state.setdefault("history", []).append({
        "type": kind, "id": item["id"], "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "xp": awarded, "verified": verified, "hints": hint_count,
    })
    return awarded, add_xp(state, awarded)
