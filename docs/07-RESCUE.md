# Pip's Rescue Bay

Start:

```bash
rescue
```

Choose a guided workflow for a slow PC, boot failure, suspected disk failure, Windows filesystem,
network, or unknown-hardware problem. Rescue Bay inventories first, explains the evidence, uses
read-only checks, summarizes findings, and recommends the next diagnostic step.

Useful read-only diagnostics:

```bash
lsblk
```
Identify disks/partitions.

```bash
smartctl -x /dev/sdX
```
Inspect SATA/SAS/USB-attached drive SMART data.

```bash
nvme smart-log /dev/nvme0
```
Inspect an NVMe controller.

```bash
journalctl -b -p warning
```
See warning/error logs from the current boot.

```bash
dmesg -T
```
See kernel messages, especially useful for disks, USB and drivers.

## Recovery rule

If a disk may be physically failing, reduce writes to it.
Often the safest workflow is to image/clone it to healthy storage before attempting logical repair.
The 128 GB Academy SSD usually cannot hold an image of a larger drive; use a separate healthy
external recovery disk. Rescue Bay never chooses ddrescue source/destination paths and never
automates destructive repair. TestDisk, PhotoRec, GParted, memtester, and ddrescue planning remain
behind explicit choices and warnings.
