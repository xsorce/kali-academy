# Kali Academy Privacy Mode

Privacy Mode inspects local-network exposure and can make a small set of reversible system changes:

```bash
academy privacy
academy privacy status
academy privacy on
academy privacy off
```

Status shows MAC-randomization policy, firewall policy, listening services, Avahi, Samba, SSH LAN
listeners, Tailscale, hostname, active interface/SSID, default route, DNS, and a simple conservative
score. Detailed UFW status is shown when sudo is already authorized (`sudo -v`); status itself does
not prompt or change the firewall.

`privacy on` explains and separately confirms each offered change. It can add an Academy-owned
NetworkManager Wi-Fi MAC policy for future reconnects, enable UFW with unsolicited inbound traffic
denied, stop local discovery/file-sharing services, stop unnecessary SSH, and use the generic
hostname `kali-academy`. It does not restart NetworkManager. Firewall and SSH changes are skipped
during an active SSH session; Tailscale traffic is allowed on `tailscale0`, and SSH is retained when
Tailscale is installed.

Rollback metadata is stored with user-only permissions under:

```text
~/.local/share/kali-academy/privacy/
```

It contains only prior setting/service states and hashes—never passwords, Wi-Fi keys, tokens, or
private keys. `privacy off` restores only recorded Privacy Mode changes and leaves settings alone if
they were changed again later.

Privacy Mode reduces LAN exposure. It does not make the device invisible, anonymous, or resistant
to traffic analysis, websites, providers, or a compromised endpoint.
