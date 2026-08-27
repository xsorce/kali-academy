# Install Kali Academy on an external SSD

Use a full Kali installation on the external SSD rather than Live persistence.

During the Kali graphical installer:

1. Before starting, record every disk's **model, serial, capacity, and transport**. Device names such
   as `/dev/sda` can change between boots and must never be the only identifier.
2. If practical, disconnect or disable internal drives during installation. This is the simplest way
   to prevent the installer from placing EFI or GRUB files on an internal disk.
3. Select the **external SSD by matching model, serial, capacity, and USB transport**.
4. Partition only that external SSD. It needs its own GPT EFI System Partition (FAT32, `esp`/`boot`
   flags, mounted at `/boot/efi`) and its own Kali root filesystem. Do not reuse an internal disk's
   existing EFI partition.
5. When asked for the GRUB/bootloader target, select the whole external SSD identified above—not an
   internal disk and not merely a numbered partition. GRUB's EFI files and `/boot/efi` must remain on
   the external SSD.
6. Choose Xfce and the default Kali tool set. Do not select "everything."
7. For a portable system containing credentials, encrypted LVM is recommended.
8. Create your own Kali user/password when prompted.

Before partitioning, inspect from the live environment:

```bash
lsblk -d -o PATH,MODEL,SERIAL,SIZE,TRAN
lsblk -o PATH,MODEL,SERIAL,SIZE,TRAN,TYPE,FSTYPE,MOUNTPOINTS
```

Stop if the external SSD cannot be identified unambiguously. Never infer the destination from drive
order alone.

## Your password

Kali Academy intentionally does not hardcode or save your login password.

After installation you can change it at any time:

```bash
academy-passwd
```

That simply launches Linux's normal:

```bash
passwd
```

Your password is typed directly into the system password utility and never placed in the Academy
profile or Git repository.

## Verify before the first reboot

While still in the installed system/chroot, or before allowing the installer to reboot, verify:

```bash
findmnt -T / -no SOURCE,TARGET
findmnt -T /boot -no SOURCE,TARGET
findmnt -T /boot/efi -no SOURCE,TARGET
lsblk -o PATH,PKNAME,MODEL,SERIAL,SIZE,TRAN,TYPE,FSTYPE,MOUNTPOINTS
sudo find /boot/efi/EFI -maxdepth 3 -type f -print
sudo efibootmgr -v
```

The sources for `/`, `/boot` when separate, and `/boot/efi` must trace back to the external SSD's
recorded model and serial. No internal partition may provide those mounts. Confirm that the external
EFI partition contains Kali/GRUB EFI files. For portable firmware fallback, confirm
`/boot/efi/EFI/BOOT/BOOTX64.EFI` exists; if it does not, stop and correct the external bootloader
installation before rebooting. Do not "fix" this by writing GRUB to an internal disk.

## Verify after booting the external SSD

```bash
lsblk -o NAME,MODEL,SERIAL,SIZE,TRAN,FSTYPE,MOUNTPOINTS
findmnt /
findmnt /boot/efi
df -h /
```

Repeat the model/serial comparison. If `/` or `/boot/efi` resolves to an internal disk, shut down and
correct the installation before using or updating Academy.

Ask Pip to explain anything unfamiliar:

```bash
lsblk -o NAME,MODEL,SERIAL,SIZE,TRAN,FSTYPE,MOUNTPOINTS | explain
```
