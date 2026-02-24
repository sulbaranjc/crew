import subprocess

ALLOWLIST = {
    "uptime": ["uptime"],
    "disk": ["df", "-h"],
    "mem": ["free", "-h"],
    "ip": ["ip", "a"],
    "failed_services": ["systemctl", "--failed", "--no-pager"],
}

def run_ssh(host: str, user: str, key_path: str, cmd_key: str) -> str:
    if cmd_key not in ALLOWLIST:
        raise ValueError("Comando no permitido por policy (allowlist).")
    base = ["ssh", "-i", key_path, "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", f"{user}@{host}"]
    cmd = base + ALLOWLIST[cmd_key]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        return f"[ERROR] {out.stderr.strip()}"
    return out.stdout.strip()
