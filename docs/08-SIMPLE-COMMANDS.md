# Commands worth understanding

## `ip route`

Shows how Linux decides where packets go.

A line such as:

```text
default via 192.168.1.1 dev wlan0
```

means traffic with no more-specific route goes to gateway `192.168.1.1` through `wlan0`.

## `ss -tulpn`

Shows listening sockets.

- `-t` TCP
- `-u` UDP
- `-l` listening
- `-p` process
- `-n` numeric addresses/ports

## `systemctl status NAME`

Shows the current state of a systemd unit/service.

`start` means start now.
`enable` means configure it to start automatically at boot.

## `journalctl -u NAME -b`

Shows logs for a service from the current boot.

## `rg TEXT PATH`

Fast recursive text search. Codex often uses it because it is cheaper and faster than reading an
entire repository.

Whenever one is unclear:

```bash
explain "ss -tulpn"
```
