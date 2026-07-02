#!/bin/bash
# Example statusline integration for the session-health plugin.
#
# Shows: [model] current dir | git branch | session health
# e.g.   [Fable 5] 📁 ~/myapp main | 📜🔥req231·246x ⚠️/compact
#
# To use: copy this file somewhere (e.g. ~/.claude/statusline.sh), adjust
# SESSION_HEALTH below to where the plugin is installed, then set in
# ~/.claude/settings.json:
#   "statusLine": { "type": "command", "command": "\"$HOME/.claude/statusline.sh\"" }
SESSION_HEALTH="$HOME/.claude/plugins/session-health/scripts/session_health.py"

input=$(cat)
health=$(printf '%s' "$input" | python3 "$SESSION_HEALTH" statusline 2>/dev/null)
python3 - "$input" "$health" <<'PY'
import json, os, subprocess, sys

d = json.loads(sys.argv[1])
health = sys.argv[2] if len(sys.argv) > 2 else ""
cwd = d.get("workspace", {}).get("current_dir") or d.get("cwd", "")
model = d.get("model", {}).get("display_name", "")

home = os.path.expanduser("~")
short = cwd.replace(home, "~", 1) if cwd.startswith(home) else cwd

branch = ""
try:
    r = subprocess.run(
        ["git", "-C", cwd, "branch", "--show-current"],
        capture_output=True, text=True, timeout=1,
    )
    if r.returncode == 0 and r.stdout.strip():
        branch = f"  {r.stdout.strip()}"
except Exception:
    pass

seg = f" | 📜{health}" if health else ""
print(f"[{model}] 📁 {short}{branch}{seg}")
PY
