# Panda PAU0E workflow

Do not guess the chipset from the product name.

Run:

```bash
wifi-lab interfaces
```

That shows:
- USB vendor/product IDs;
- USB driver tree;
- wireless interfaces.

Then for a discovered interface:

```bash
ethtool -i wlan1
```

(replace `wlan1` with the actual name).

This shows the kernel driver and firmware information.

## Normal diagnostics

```bash
wifi-lab scan
wifi-lab doctor
```

Learn:
- channel;
- 2.4 vs 5 GHz;
- signal/RSSI;
- driver;
- IP address;
- route/default gateway;
- DNS.

Monitor mode is separated behind an explicit authorized workflow because it can interrupt your
normal connection. Real-network testing should stay on your network or a network whose owner has
explicitly authorized the work.
