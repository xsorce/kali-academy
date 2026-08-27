# Install Kali Academy on an external SSD

Use a full Kali installation on the external SSD rather than Live persistence.

During the Kali graphical installer:

1. Select the **external SSD by model and capacity**.
2. Choose Xfce and the default Kali tool set.
3. Do not select "everything."
4. For a portable system containing credentials, encrypted LVM is recommended.
5. Create your own Kali user/password when prompted.

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

## Verify you booted from the right disk

```bash
lsblk -o NAME,MODEL,SERIAL,SIZE,TRAN,FSTYPE,MOUNTPOINTS
findmnt /
df -h /
```

Ask Pip to explain anything unfamiliar:

```bash
lsblk -o NAME,MODEL,SERIAL,SIZE,TRAN,FSTYPE,MOUNTPOINTS | explain
```
