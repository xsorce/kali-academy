import os
import sys
import time

from rich.console import Console
from rich.live import Live
from rich.text import Text

console = Console()

def _frame(head, mark=""):
    return f"     {head}{mark}\n    ///\\\n    \\V_/_"

PIP_IDLE = _frame("( o>")
PIP_STATES = {
    "idle": (PIP_IDLE,),
    "wake": (_frame("( ->"), _frame("( .>"), PIP_IDLE),
    "thinking": (_frame("( o>", " ."), _frame("( o>", " ..")),
    "happy": (_frame("( o>"), _frame("( ^>")),
    "confused": (_frame("( ?>", " ?"),),
    "warning": (_frame("( !>", " !"),),
    "quest_complete": (_frame("( o>", " +"), _frame("( ^>", " +")),
    "level_up": (_frame("( ^>", " *"), _frame("( ^>", " **")),
    "sleeping": (_frame("( .>", " z"), _frame("( ->", " zz")),
}

def animation_mode(profile=None):
    if os.environ.get("ACADEMY_NO_ANIM") == "1" or not sys.stdout.isatty():
        return "off"
    setting = (profile or {}).get("animations", True)
    if setting is False or setting in ("off", "none"):
        return "off"
    if setting == "reduced" or (profile or {}).get("reduced_motion") is True:
        return "reduced"
    return "full"

def react(state="idle", text="", profile=None):
    frames = PIP_STATES[state]
    mode = animation_mode(profile)
    if mode == "off":
        if state == "wake":
            console.print(Text(frames[-1]))
    elif mode == "reduced":
        console.print(Text(frames[-1]))
    else:
        with Live(console=console, transient=True, refresh_per_second=20) as live:
            for frame in frames:
                live.update(Text(frame))
                time.sleep(0.08)
        console.print(Text(frames[-1]))
    if text:
        console.print(f"[bold cyan]{(profile or {}).get('mascot_name', 'Pip')}[/bold cyan] > {text}")

def startup_animation(profile=None):
    learner = (profile or {}).get("display_name", "xs")
    react("wake", f"Hey {learner}. Ready when you are.", profile)
