#!/usr/bin/env python3
import argparse
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
except ImportError:
    print("Kali Academy needs python3-rich. Run ./install.sh again.")
    raise SystemExit(1)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from mascot import PIP_IDLE, react, startup_animation
from notes import UnsafeNote, add_note
from state import command_status, load_profile, save_profile, load_state, complete_activity, practice_commands, record_hint, record_practice, level_for_xp
from content import COMMAND_BOOK, LESSONS, QUESTS, SIDE_MISSIONS, SKILLS
from wifi import detect_adapters

console = Console()
DEFAULT_PROFILE = json.loads((ROOT / "config" / "default-profile.json").read_text())

def pip(text, profile, state=None):
    if state:
        react(state, text, profile)
    else:
        console.print(f"[bold cyan]{profile.get('mascot_name','Pip')}[/bold cyan] > {text}")

SKILL_GROUPS = {
    "Linux": ("linux", "shell", "processes", "systemd"),
    "Networking": ("networking", "dns"),
    "Wi-Fi": ("wifi",),
    "Security": ("packets", "web"),
    "Git": ("git",),
    "Rescue": ("rescue",),
}

def skill_confidence(state, prefixes):
    values = [value for concept, value in state.get("knowledge", {}).items() if concept.split(".", 1)[0] in prefixes]
    return sum(values) / len(values) if values else 0.0

def recommended_quest(state):
    incomplete = [quest for quest in QUESTS if quest["id"] not in state.get("completed_quests", [])]
    choices = incomplete or QUESTS
    return min(choices, key=lambda quest: min((state.get("knowledge", {}).get(c, 0.0) for c in quest.get("concepts", [])), default=0.0))

def recent_learning(state):
    if state.get("achievements"):
        return str(state["achievements"][-1])
    if not state.get("history"):
        return "No completions yet"
    event = state["history"][-1]
    item = next((item for item in LESSONS + SIDE_MISSIONS + QUESTS if item["id"] == event["id"]), None)
    return item["title"] if item else event["id"]

def skill_meter(name, confidence):
    filled = round(confidence * 8)
    return f"{name:<10} {'#' * filled}{'-' * (8 - filled)} {confidence:>4.0%}"

def home_screen(profile, state, show_pip=True):
    level, within, threshold = level_for_xp(state.get("xp", 0))
    next_level_xp = state.get("xp", 0) + threshold - within
    quest = recommended_quest(state)
    strengths = {name: skill_confidence(state, prefixes) for name, prefixes in SKILL_GROUPS.items()}
    weak = min(strengths, key=strengths.get)

    if show_pip:
        console.print(Text(f"{PIP_IDLE}\n      PIP"))
    body = Table.grid(expand=True)
    body.add_column()
    body.add_column(justify="right")
    body.add_row(f"[bold]{profile.get('display_name', 'xs')}[/bold]", f"[bold cyan]LEVEL {level:02d}[/bold cyan]")
    xp_filled = round(within / threshold * 18)
    body.add_row(f"XP [{'#' * xp_filled}{'-' * (18 - xp_filled)}] {state.get('xp', 0)} / {next_level_xp}", "")
    body.add_row("[dim]TODAY[/dim]", "")
    body.add_row(f"-> {quest['title']}", f"[green]+{quest['xp']} XP[/green]")
    body.add_row("[dim]PRACTICE[/dim]", "")
    body.add_row(f"-> {weak}", f"{strengths[weak]:.0%}")
    body.add_row("[dim]SKILLS[/dim]", "")
    pairs = list(strengths.items())
    for left, right in zip(pairs[:3], pairs[3:]):
        body.add_row(skill_meter(*left), skill_meter(*right))
    body.add_row("[dim]RECENT[/dim]", "")
    body.add_row(recent_learning(state), "")
    console.print(Panel(body, title="KALI ACADEMY", border_style="cyan", width=62))
    console.print("[L] Learn  [Q] Quests  [A] Ask Pip  [C] Codex")
    console.print("[W] Wi-Fi  [B] Range   [R] Rescue   [N] Notes")
    console.print("[K] Knowledge  [G] GitHub  [H] Health  [S] Settings  [X] Exit")

def show_lessons(state):
    table = Table(title="Learning map")
    table.add_column("#", justify="right")
    table.add_column("Lesson")
    table.add_column("Skill")
    table.add_column("XP", justify="right")
    table.add_column("Status")
    completed = set(state.get("completed_lessons", []))
    for i, lesson in enumerate(LESSONS, 1):
        table.add_row(
            str(i), lesson["title"], lesson["skill"], str(lesson["xp"]),
            "done" if lesson["id"] in completed else ""
        )
    console.print(table)

def mission_command(part, profile, state, related_lesson):
    command = part["command"]
    console.print(f"[bold green]$ {command}[/bold green]")
    while True:
        typed = Prompt.ask("Type the command (or back)").strip()
        if typed == "back":
            return None
        if typed == command:
            break
        pip("Type the shown command exactly so the check stays safe.", profile, "confused")
    practice_commands(state, part.get("commands", []), related_lesson)
    try:
        result = subprocess.run(["bash", "-lc", command], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as error:
        console.print(f"[red]{error}[/red]")
        return None
    output = (result.stdout + result.stderr).strip()
    console.print(Text(output[:3000] or "(no output)"))
    return result, output

def challenge_passed(challenge, returncode, output, answer):
    accepted = {value.casefold() for value in challenge.get("answers", [])}
    if challenge.get("answer_pattern"):
        accepted.update(value.casefold() for value in re.findall(challenge["answer_pattern"], output, re.MULTILINE))
    passed = returncode == 0 and answer.strip().casefold() in accepted
    return passed and (not challenge.get("output_pattern") or bool(re.search(challenge["output_pattern"], output, re.MULTILINE)))

def run_mission(lesson, profile, state):
    pip(lesson["intro"], profile, "thinking")
    console.print(Panel(lesson["mental_model"], title="Mental model", border_style="cyan"))
    for step in lesson["steps"]:
        result = mission_command(step, profile, state, lesson["title"])
        if result is None:
            return False
        Prompt.ask(step["observe"])
        console.print(f"[dim]{step['explanation']}[/dim]")

    challenge = lesson["challenge"]
    console.print("[bold]Challenge[/bold]")
    if Confirm.ask("Need a hint?", default=False):
        record_hint(state, "lesson", lesson["id"])
        pip(challenge["hint"], profile)
    result = mission_command(challenge, profile, state, lesson["title"])
    if result is None:
        return False
    process, output = result
    answer = Prompt.ask(challenge["question"])
    console.print(f"[dim]{challenge['explanation']}[/dim]")
    passed = challenge_passed(challenge, process.returncode, output, answer)
    if not passed:
        record_practice(state, lesson, -0.02)
        pip("Good attempt. Recheck the evidence, then retry the challenge.", profile, "confused")
        return False
    if lesson["id"] in state.get("completed_lessons", []):
        record_practice(state, lesson, 0.03)
        pip("Review complete. XP is awarded only once.", profile, "happy")
        return True
    awarded, leveled = complete_activity(state, "lesson", lesson, verified=True)
    console.print(f"[green]+{awarded} XP[/green]")
    pip("Level up. Your evidence is turning into skill." if leveled else "Mission complete. Evidence beats guessing.", profile, "level_up" if leveled else "happy")
    save_mission_notes(lesson, profile)
    return True

def lesson_menu(profile, state):
    weakest = weakest_lesson(state)
    pip(f"Try {weakest['title']} next; {weakest_concept(weakest, state)} needs practice.", profile, "thinking")
    show_lessons(state)
    raw = Prompt.ask("Lesson number (blank to return)", default="")
    if not raw:
        return
    try:
        lesson = LESSONS[int(raw) - 1]
    except Exception:
        pip("That lesson number doesn't exist.", profile, "confused")
        return
    was_complete = lesson["id"] in state.get("completed_lessons", [])
    if run_mission(lesson, profile, state):
        completed_core = sum(item["id"] in state.get("completed_lessons", []) for item in LESSONS)
        side = next((item for item in SIDE_MISSIONS if item["id"] not in state.get("completed_lessons", [])), None)
        if not was_complete and side and completed_core % 3 == 0 and Confirm.ask(f"Try side mission: {side['title']}?", default=False):
            run_mission(side, profile, state)

def quest_menu(profile, state):
    table = Table(title="Quests")
    table.add_column("#")
    table.add_column("Quest")
    table.add_column("XP")
    table.add_column("Status")
    done = set(state.get("completed_quests", []))
    for i, q in enumerate(QUESTS, 1):
        table.add_row(str(i), q["title"], str(q["xp"]), "✓" if q["id"] in done else "")
    console.print(table)
    raw = Prompt.ask("Quest number (blank to return)", default="")
    if not raw:
        return
    try:
        q = QUESTS[int(raw)-1]
    except Exception:
        pip("Unknown quest.", profile, "confused")
        return
    console.print(Panel(q["objective"], title=q["title"]))
    if q.get("lab_quest"):
        subprocess.run(["labctl", "quest", str(q["lab_quest"])])
        return
    while True:
        action = Prompt.ask("quest", choices=["hint", "done", "back"], default="back")
        if action == "hint":
            record_hint(state, "quest", q["id"])
            pip(q["hint"], profile)
        elif action == "done":
            if q["id"] in done:
                pip("That quest is already complete.", profile)
                return
            verified = verify_quest(q, state)
            if verified is False:
                pip("That answer doesn't match the system evidence yet. Recheck the output.", profile, "confused")
                continue
            if verified is True or Confirm.ask("Automatic verification was unavailable. Did you complete and understand it?", default=False):
                awarded, leveled = complete_activity(state, "quest", q, verified is True)
                bonus = awarded - q["xp"]
                console.print(f"[green]+{awarded} XP[/green]" + (f" [cyan](+{bonus} no-hint bonus)[/cyan]" if bonus else ""))
                if leveled:
                    pip("Quest complete and level up. Nice work, xs.", profile, "level_up")
                else:
                    pip("Quest complete. Evidence beats guessing.", profile, "quest_complete")
                return
        else:
            return

def profile_view(profile):
    table = Table(title="Local learner profile")
    table.add_column("Field")
    table.add_column("Value")
    for key in ["display_name", "experience", "learning_style", "tutor_mode"]:
        table.add_row(key, str(profile.get(key, "")))
    table.add_row("interests", ", ".join(profile.get("interests", [])))
    table.add_row("goals", "\n".join(profile.get("learning_goals", [])))
    console.print(table)
    console.print("[dim]This profile is stored locally and is not automatically committed to GitHub.[/dim]")

def save_mission_notes(lesson, profile):
    categories = {
        "concept": "concepts I learned",
        "command": "commands worth remembering",
        "observation": "personal observations",
    }
    while Confirm.ask("Save a local lesson note?", default=False):
        category = Prompt.ask("Note type", choices=list(categories))
        text = Prompt.ask("Note")
        try:
            add_note(text, categories[category], lesson["title"])
            pip("Saved locally. Pip can retrieve it for relevant questions.", profile, "happy")
        except (OSError, ValueError, UnsafeNote) as error:
            pip(str(error), profile, "warning")

def settings_menu(profile):
    current = profile.get("animations", True)
    console.print(f"Animation setting: {current}")
    choice = Prompt.ask("Animation", choices=["full", "reduced", "off", "back"], default="back")
    if choice != "back":
        profile["animations"] = {"full": True, "reduced": "reduced", "off": False}[choice]
        save_profile(profile)
        pip(f"Animations set to {choice}.", profile, "happy")

def weakest_concept(item, state):
    return min(item.get("concepts", [item["skill"]]), key=lambda concept: state.get("knowledge", {}).get(concept, 0.0))

def weakest_lesson(state):
    return min(LESSONS, key=lambda item: state.get("knowledge", {}).get(weakest_concept(item, state), 0.0))

def verify_quest(quest, state):
    check = quest.get("verify")
    if not check:
        return None
    try:
        practice_commands(state, [check["command"][0]], quest["title"])
        result = subprocess.run(check["command"], capture_output=True, text=True, timeout=5)
        answers = re.findall(check["pattern"], result.stdout, re.MULTILINE) if result.returncode == 0 else []
        if not answers:
            return None
        answer = Prompt.ask(check["prompt"]).strip().casefold()
        return answer in {value.casefold() for value in answers}
    except (OSError, subprocess.TimeoutExpired):
        return None

def wireless_interfaces(record=False):
    return {item["interface"] for item in detect_adapters(detailed=record, save=record) if item["interface"]}

def knowledge_view(state):
    table = Table(title="Concept knowledge")
    table.add_column("Concept")
    table.add_column("Confidence", justify="right")
    for concept, confidence in sorted(state.get("knowledge", {}).items(), key=lambda pair: (pair[1], pair[0])):
        table.add_row(concept, f"{confidence:.2f}")
    console.print(table)

def history_view(state):
    table = Table(title="Lesson and quest history")
    for column in ("When", "Type", "Activity", "XP", "Hints", "Verified"):
        table.add_column(column)
    for event in state.get("history", []):
        table.add_row(event.get("at") or "legacy", event["type"], event["id"], str(event.get("xp") or "—"), str(event.get("hints", 0)), "yes" if event.get("verified") else "no")
    console.print(table)

def commands_view(state):
    table = Table(title="Kali Academy Command Book")
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("What it does")
    table.add_column("Last practiced", no_wrap=True)
    table.add_column("Related lesson")
    practiced = state.get("command_knowledge", {})
    for command, (description, lesson) in COMMAND_BOOK.items():
        entry = practiced.get(command, {})
        last = entry.get("last_practiced") or "never"
        table.add_row(command, command_status(entry), description, last[:10] if last != "never" else last, entry.get("related_lesson", lesson))
    console.print(table)

def surprise(profile, state):
    weak = weakest_concept(weakest_lesson(state), state)
    prompt = f"""Teach xs one useful or surprising Linux/Kali concept a basic Linux user often does not know.
Prefer the learner's weaker concept: {weak}.
Choose something hands-on such as file descriptors, namespaces, process trees, signals, /proc, /sys,
sockets, DNS, routing, strace, lsof, tmux, SSH, systemd, filesystems, packet capture, Git or containers.
Make it a safe 5-minute mini lesson with one command to investigate."""
    subprocess.run(["ai", prompt], check=False)

def menu():
    profile = load_profile(DEFAULT_PROFILE)
    state = load_state()
    known_wifi = wireless_interfaces(record=True)
    console.clear()
    startup_animation(profile)
    first_screen = True

    while True:
        state = load_state()
        current_wifi = wireless_interfaces()
        attached = current_wifi - known_wifi
        if attached:
            wireless_interfaces(record=True)
            pip(f"New wireless interface: {', '.join(sorted(attached))}. Try the Wi-Fi lesson.", profile, "wake")
        known_wifi = current_wifi
        home_screen(profile, state, show_pip=not first_screen)
        first_screen = False
        choice = Prompt.ask("academy").strip().lower()
        if choice in ("l", "1"):
            lesson_menu(profile, state)
        elif choice in ("q", "2"):
            quest_menu(profile, state)
        elif choice in ("a", "3"):
            question = Prompt.ask("Ask Pip (blank to cancel)", default="").strip()
            if question:
                subprocess.run(["ai", question])
        elif choice in ("c", "4"):
            subprocess.run(["cdx-learn"])
        elif choice in ("b", "5"):
            subprocess.run(["labctl"])
        elif choice in ("w", "6"):
            pip("Passive checks are safe. Monitor mode can disconnect Wi-Fi and requires authorization.", profile, "warning")
            subprocess.run(["wifi-lab"])
        elif choice in ("r", "7"):
            pip("Check device names twice before any rescue tool writes to disk.", profile, "warning")
            subprocess.run(["rescue"])
        elif choice == "n":
            subprocess.run(["notes"])
        elif choice == "k":
            knowledge_view(state)
        elif choice == "g":
            subprocess.run(["gh", "auth", "status"], check=False)
        elif choice in ("h",):
            subprocess.run(["usb-health"])
        elif choice == "s":
            settings_menu(profile)
        elif choice == "8":
            surprise(profile, state)
        elif choice == "9":
            profile_view(profile)
        elif choice == "x":
            pip("See you next boot, xs.", profile, "sleeping")
            return
        console.print()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", choices=["knowledge", "history", "commands", "_record-commands", "_complete-lab"])
    parser.add_argument("details", nargs="*")
    parser.add_argument("--no-animation", action="store_true")
    args = parser.parse_args()
    if args.command:
        state = load_state()
        if args.command == "_record-commands":
            if len(args.details) >= 2:
                practice_commands(state, args.details[1:], args.details[0])
        elif args.command == "_complete-lab":
            quest = next((item for item in QUESTS if item["id"] in args.details and item.get("lab_quest")), None)
            if not quest:
                raise SystemExit("Unknown lab objective")
            awarded, leveled = complete_activity(state, "quest", quest, verified=True)
            console.print(f"[green]+{awarded} verified XP[/green]" if awarded else "Objective already rewarded; no duplicate XP.")
            if leveled:
                console.print("[bold cyan]Pip[/bold cyan] > Level up, xs.")
        elif args.command == "knowledge":
            knowledge_view(state)
        elif args.command == "history":
            history_view(state)
        else:
            commands_view(state)
        return
    if args.no_animation:
        os.environ["ACADEMY_NO_ANIM"] = "1"
    menu()

if __name__ == "__main__":
    main()
