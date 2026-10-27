#!/bin/sh
# Starts EVE Industry Management at http://localhost:8642/ so EVE logins complete by themselves.
# Keep this file next to "EVE Industry Management.html". Press Ctrl+C to stop.
# It also reads web pages for the tool (supplier stock lists), which a browser page can't do by itself.
cd "$(dirname "$0")"
( sleep 1; open "http://localhost:8642/" 2>/dev/null || xdg-open "http://localhost:8642/" ) &
exec python3 -c '
import http.server, urllib.request, urllib.parse
F = "EVE Industry Management.html"
class H(http.server.BaseHTTPRequestHandler):
    def send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/proxy":
            # Only the tool itself may use it: not other websites (Sec-Fetch-Site), nor a site whose name was pointed at this computer (Host)
            if self.headers.get("Host") not in ("localhost:8642", "127.0.0.1:8642") or self.headers.get("Sec-Fetch-Site", "same-origin") != "same-origin":
                return self.send(403, b"Only the tool can use this", "text/plain; charset=utf-8")
            target = urllib.parse.parse_qs(u.query).get("url", [""])[0]
            if not target.startswith(("https://", "http://")):
                return self.send(400, b"Only web links can be read", "text/plain; charset=utf-8")
            try:
                req = urllib.request.Request(target, headers={"User-Agent": "Mozilla/5.0 (EVE Industry Management, local tool)"})
                resp = urllib.request.urlopen(req, timeout=40)
                return self.send(200, resp.read(), "application/octet-stream")   # never the type the page gives: an SVG or HTML page would run as the tool
            except Exception as e:
                return self.send(502, str(e).encode(), "text/plain; charset=utf-8")
        self.send(200, open(F, "rb").read(), "text/html; charset=utf-8")
    def log_message(self, *a): pass
print("EVE Industry Management is running at http://localhost:8642/ (Ctrl+C to stop)")
http.server.ThreadingHTTPServer(("127.0.0.1", 8642), H).serve_forever()
'
