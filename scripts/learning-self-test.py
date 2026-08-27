#!/usr/bin/env python3
import copy
import io
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "academy"))
import state
from content import COMMAND_BOOK, LAB_QUESTS, LESSONS, QUESTS, SIDE_MISSIONS
from mascot import PIP_IDLE, PIP_STATES
from app import challenge_passed, recommended_quest, skill_confidence

temporary = tempfile.TemporaryDirectory()
root = Path(temporary.name)
state.CONFIG_DIR = root / "config"
state.DATA_DIR = root / "data"
state.PROFILE_PATH = state.CONFIG_DIR / "profile.json"
state.STATE_PATH = state.DATA_DIR / "state.json"

assert PIP_IDLE == "     ( o>\n    ///\\\n    \\V_/_"
assert set(PIP_STATES) == {"idle", "wake", "thinking", "happy", "confused", "warning", "quest_complete", "level_up", "sleeping"}
assert recommended_quest(state.DEFAULT_STATE)["id"] in {quest["id"] for quest in QUESTS}
assert skill_confidence(state.DEFAULT_STATE, ("networking", "dns")) == 0.0
assert [lesson["id"] for lesson in LESSONS] == ["filesystem", "permissions", "pipes", "processes", "systemd", "networking", "dns-routes-sockets", "ssh", "linux-internals", "git", "wifi", "packets", "reconnaissance", "web-security", "rescue"]
assert {mission["concepts"][0] for mission in SIDE_MISSIONS} >= {"linux.proc", "linux.sys", "processes.file_descriptors", "processes.signals", "processes.namespaces", "processes.strace", "shell.tmux", "networking.sockets", "linux.mounts"}
assert all(mission["challenge"].get("answers") or mission["challenge"].get("answer_pattern") for mission in LESSONS + SIDE_MISSIONS)
assert not any("\n" in part["command"] for mission in LESSONS + SIDE_MISSIONS for part in mission["steps"] + [mission["challenge"]])
assert challenge_passed(LESSONS[2]["challenge"], 0, "3", "3")
assert [quest["lab_quest"] for quest in LAB_QUESTS] == list(range(1, 9))

for required in ("ls", "grep", "chmod", "systemctl", "journalctl", "ip", "ss", "dig", "iw", "nmap", "tcpdump", "strace", "lsof", "git", "docker"):
    assert required in COMMAND_BOOK
assert [state.command_status({"practice_count": count}) for count in (0, 1, 3, 6)] == ["new", "learning", "comfortable", "mastered"]
commands = copy.deepcopy(state.DEFAULT_STATE)
state.save_state(commands)
for _ in range(6):
    state.practice_commands(commands, ["grep", "not-allowed"], "Pipes")
assert state.command_status(commands["command_knowledge"]["grep"]) == "mastered"
assert set(commands["command_knowledge"]["grep"]) == {"practice_count", "last_practiced", "related_lesson"}
assert "not-allowed" not in commands["command_knowledge"]

legacy = {"xp": 42, "skills": {"bash": 3}, "completed_lessons": ["filesystem"], "completed_quests": [], "command_knowledge": {"grep": {"practice_count": 2, "arguments": "secret"}, "token=secret": {}}}
assert state.migrate_state(legacy)
assert legacy["xp"] == 42 and legacy["skills"]["shell"] == 3
assert legacy["knowledge"]["linux.filesystem"] == 0.2 and legacy["history"][0]["migrated"]
assert legacy["command_knowledge"] == {"grep": {"practice_count": 2, "last_practiced": None}}

fresh = copy.deepcopy(state.DEFAULT_STATE)
state.save_state(fresh)
quest = next(item for item in QUESTS if item["id"] == "route-detective")
awarded, _ = state.complete_activity(fresh, "quest", quest, verified=True)
assert awarded == quest["xp"] + quest["xp"] // 10
assert state.complete_activity(fresh, "quest", quest) == (0, False)
assert fresh["knowledge"]["networking.routing"] == 0.25
lab = copy.deepcopy(state.DEFAULT_STATE)
state.save_state(lab)
awarded, _ = state.complete_activity(lab, "quest", LAB_QUESTS[0], verified=True)
assert awarded > 0 and lab["history"][-1]["verified"]
assert state.complete_activity(lab, "quest", LAB_QUESTS[0], verified=True) == (0, False)

state.STATE_PATH.write_text("{broken json")
warning = io.StringIO()
with redirect_stderr(warning):
    recovered = state.load_state()
assert recovered["xp"] == 0 and "WARNING" in warning.getvalue()
assert list(state.DATA_DIR.glob("state.json.corrupt-*"))

state.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
state.PROFILE_PATH.write_text("{broken profile")
warning = io.StringIO()
with redirect_stderr(warning):
    profile = state.load_profile({"name": "xs", "animations": True})
assert profile["name"] == "xs" and "WARNING" in warning.getvalue()
assert list(state.CONFIG_DIR.glob("profile.json.corrupt-*"))

state.save_state(copy.deepcopy(state.DEFAULT_STATE))
first = state.load_state()
second = state.load_state()
state.practice_commands(first, ["grep"], "Pipes")
state.practice_commands(second, ["grep"], "Pipes")
assert state.load_state()["command_knowledge"]["grep"]["practice_count"] == 2

state.save_state(copy.deepcopy(state.DEFAULT_STATE))
def concurrent_practice(_):
    local = state.load_state()
    state.practice_commands(local, ["grep"], "Pipes")
with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(concurrent_practice, range(12)))
assert state.load_state()["command_knowledge"]["grep"]["practice_count"] == 12
assert not list(state.DATA_DIR.glob(".state.json.*.tmp"))

state.STATE_PATH.write_text('{"xp": 42, "schema_version": 1}')
migrated = state.load_state()
assert migrated["xp"] == 42 and migrated["schema_version"] == state.STATE_SCHEMA_VERSION
assert list((state.DATA_DIR / "state-snapshots").glob("state-before-schema-*.json"))
