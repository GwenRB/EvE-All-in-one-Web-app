#!/bin/sh
# Syntax check of every inline <script> in the app (no browser needed). Exit status 1 on a syntax error.
cd "$(dirname "$0")/.."
python3 - <<'PY'
import re, subprocess, sys, tempfile
s = open("EVE Industry Management.html", encoding="utf-8").read()
js = "\n".join(re.findall(r"<script>(.*?)</script>", s, re.S))
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f: f.write(js); p = f.name
r = subprocess.run(["node", "--check", p], capture_output=True, text=True)
print(r.stderr or "OK: inline scripts parse"); sys.exit(r.returncode)
PY
