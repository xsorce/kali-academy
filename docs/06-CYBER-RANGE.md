# Safe cyber range

Start:

```bash
labctl start
```

The Academy creates an internal Docker network with:
- `academy-tools`
- `academy-target`

Enter the tools machine:

```bash
labctl enter tools
```

Begin with:

```bash
ip addr
ip route
ping academy-target
nmap academy-target
curl http://academy-target:8080
```

Reset everything:

```bash
labctl reset
```

This removes and recreates the disposable targets.

Start the local web-security lab:

```bash
labctl web
```

Then visit:

```text
http://127.0.0.1:3000
```

The intention is to learn aggressive security tooling here first, while keeping normal Wi-Fi work
diagnostic/passive.
