#!/usr/bin/env python3
"""Passive Wi-Fi hardware and network diagnostics for Kali Academy."""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
SYS_NET = Path("/sys/class/net")
SYS_USB = Path("/sys/bus/usb/devices")
STATE_FILE = Path.home() / ".local/share/kali-academy/wifi-device.json"


def run(*command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def read(path):
    try:
        return path.read_text(errors="replace").strip()
    except OSError:
        return ""


def usb_parent(device):
    try:
        device = device.resolve()
    except OSError:
        return None
    for parent in (device, *device.parents):
        if (parent / "idVendor").is_file() and (parent / "idProduct").is_file():
            return parent
    return None


def parse_fields(text):
    fields = {}
    for line in text.splitlines():
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip().lower()] = value.strip()
    return fields


def supported_modes(text):
    modes = []
    active = False
    for line in text.splitlines():
        if "Supported interface modes:" in line:
            active = True
        elif active and re.match(r"\s*\*\s+", line):
            modes.append(re.sub(r"^\s*\*\s+", "", line).strip())
        elif active and line.strip():
            break
    return ", ".join(modes) or "unavailable"


def band_for(frequency):
    if not frequency:
        return "unavailable"
    mhz = int(frequency)
    if mhz < 2500:
        return "2.4 GHz"
    if mhz < 5925:
        return "5 GHz"
    return "6 GHz"


def wireless_paths():
    if not SYS_NET.is_dir():
        return []
    paths = []
    for path in SYS_NET.iterdir():
        if (path / "wireless").is_dir() or "DEVTYPE=wlan" in read(path / "uevent"):
            paths.append(path)
    return paths


def inspect_interface(path, detailed=True):
    name = path.name
    usb = usb_parent(path / "device")
    driver_info = parse_fields(run("ethtool", "-i", name)) if detailed else {}
    if not driver_info and (path / "device/driver").exists():
        try:
            driver_info["driver"] = (path / "device/driver").resolve().name
        except OSError:
            pass
    item = {
        "interface": name,
        "usb_id": f"{read(usb / 'idVendor')}:{read(usb / 'idProduct')}" if usb else "unavailable",
        "hardware": " ".join(filter(None, (read(usb / "manufacturer"), read(usb / "product")))) if usb else "unavailable",
        "driver": driver_info.get("driver", "unavailable"),
        "firmware": driver_info.get("firmware-version", "unavailable"),
    }
    if not detailed:
        return item

    info = run("iw", "dev", name, "info")
    link = run("iw", "dev", name, "link")
    phy_match = re.search(r"wiphy\s+(\d+)", info)
    channel = re.search(r"channel\s+(\d+)\s+\((\d+)\s+MHz\)(?:,\s*width:\s*([^,\n]+))?", info)
    signal = re.search(r"signal:\s*([-.\d]+\s*dBm)", link)
    bitrate = re.search(r"tx bitrate:\s*(.+)", link)
    route = run("ip", "route", "show", "default", "dev", name)
    gateway = re.search(r"default via\s+(\S+)", route)
    dns = run("resolvectl", "dns", name)
    if dns and ":" in dns:
        dns = dns.split(":", 1)[1].strip()
    if not dns:
        dns = " ".join(filter(None, run("nmcli", "-g", "IP4.DNS,IP6.DNS", "device", "show", name).splitlines()))
    item.update({
        "modes": supported_modes(run("iw", "phy", f"phy{phy_match.group(1)}", "info")) if phy_match else "unavailable",
        "band": band_for(channel.group(2) if channel else None),
        "channel": channel.group(1) if channel else "not connected",
        "width": channel.group(3) if channel and channel.group(3) else "unavailable",
        "signal": signal.group(1) if signal else "not connected",
        "bitrate": bitrate.group(1) if bitrate else "not connected",
        "gateway": gateway.group(1) if gateway else "unavailable",
        "dns": dns or "unavailable",
    })
    return item


def unbound_panda_devices(adapters):
    """Find a descriptor match when USB exists but no wireless interface does."""
    if not SYS_USB.is_dir():
        return []
    bound_ids = {item["usb_id"] for item in adapters}
    matches = []
    for device in SYS_USB.iterdir():
        usb_id = f"{read(device / 'idVendor')}:{read(device / 'idProduct')}"
        hardware = " ".join(filter(None, (read(device / "manufacturer"), read(device / "product"))))
        if usb_id in bound_ids or not re.search(r"panda|pau0e|ac1200", hardware, re.IGNORECASE):
            continue
        matches.append({
            "interface": "", "usb_id": usb_id, "hardware": hardware,
            "driver": "not bound", "firmware": "unavailable", "modes": "unavailable",
            "band": "unavailable", "channel": "not connected", "width": "unavailable",
            "signal": "not connected", "bitrate": "not connected",
            "gateway": "unavailable", "dns": "unavailable",
        })
    return matches


def save_detection(adapters):
    # Store hardware facts only: never SSIDs, addresses, command arguments, or credentials.
    if not adapters:
        return
    safe_keys = ("interface", "usb_id", "hardware", "driver", "firmware")
    payload = {
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "adapters": [{key: item[key] for key in safe_keys} for item in adapters],
    }
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    os.chmod(temporary, 0o600)
    temporary.replace(STATE_FILE)


def detect_adapters(detailed=True, save=False):
    adapters = [inspect_interface(path, detailed) for path in wireless_paths()]
    if detailed:
        adapters.extend(unbound_panda_devices(adapters))
    if save:
        try:
            save_detection(adapters)
        except OSError:
            pass
    return adapters


def show_status(adapters=None):
    adapters = detect_adapters(save=True) if adapters is None else adapters
    if not adapters:
        console.print("[yellow]No wireless interface was found.[/yellow]")
        console.print("Reconnect the Panda adapter, then run [bold]wifi-lab doctor[/bold]. No chipset or interface name was assumed.")
        return False
    for item in adapters:
        table = Table.grid(padding=(0, 1))
        table.add_column(style="cyan", no_wrap=True)
        table.add_column()
        for label, key in (
            ("Hardware", "hardware"), ("USB vendor:product", "usb_id"), ("Kernel driver", "driver"),
            ("Firmware", "firmware"), ("Supported modes", "modes"),
            ("Band / channel", "channel"), ("Width", "width"), ("Signal", "signal"), ("Bitrate", "bitrate"),
            ("Gateway", "gateway"), ("DNS", "dns"),
        ):
            value = item[key]
            if key == "channel":
                value = f"{item['band']} / {value}"
            table.add_row(label, value)
        title = f"Wi-Fi: {item['interface']}" if item["interface"] else "Panda USB: interface not created"
        console.print(Panel(table, title=title, border_style="cyan"))
    return True


def scan():
    console.print("[bold cyan]Pip[/bold cyan] > Cached NetworkManager results only; this does not force a radio scan.")
    subprocess.run([
        "nmcli", "--wait", "10", "-f", "IN-USE,SSID,CHAN,FREQ,RATE,SIGNAL,BARS,SECURITY",
        "device", "wifi", "list", "--rescan", "no",
    ], check=False)


def doctor():
    show_status()
    for title, command in (
        ("Radio blocks", ("rfkill", "list")),
        ("Addresses", ("ip", "-brief", "address")),
        ("Routes", ("ip", "route")),
    ):
        console.rule(title)
        output = run(*command)
        console.print(output or "unavailable")


def learn():
    adapters = detect_adapters(save=True)
    item = adapters[0] if adapters else {}
    steps = (
        ("Hardware", item.get("hardware", "The Panda PAU0E is the physical radio; reconnect it if no adapter appears.")),
        ("USB device", f"Linux identifies this attachment by vendor:product ID {item.get('usb_id', 'not detected')}, not by a guessed chipset."),
        ("Driver", f"The kernel driver {item.get('driver', 'is not attached yet')} translates Linux requests for the hardware."),
        ("Interface", f"The driver exposes {item.get('interface', 'a wireless interface')} for tools such as iw and NetworkManager."),
        ("Radio", f"The radio reports modes and, when connected, a band/channel. Current signal: {item.get('signal', 'not detected')}."),
        ("Network", f"IP routing reaches gateway {item.get('gateway', 'not detected')}; DNS servers turn names into addresses."),
    )
    console.print("[bold cyan]Pip[/bold cyan] > Follow the chain; each layer depends on the one before it.")
    for number, (title, text) in enumerate(steps, 1):
        console.print(f"[bold]{number}. {title}[/bold] — {text}")


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    if command == "status":
        show_status()
    elif command == "scan":
        scan()
    elif command == "doctor":
        doctor()
    elif command == "learn":
        learn()
    elif command == "detect":
        detect_adapters(save=True)
    else:
        raise SystemExit("Usage: wifi.py [status|scan|doctor|learn|detect]")


if __name__ == "__main__":
    main()
