#!/usr/bin/env python3
"""Local HTTP server that serves a valid Google access token to the browser.
Helps the golf handicap HTML app authenticate with Google Sheets when opened as file://.
Run this server in one terminal, then open the HTML in your browser."""

import json, time, http.server, urllib.request, urllib.parse, socketserver, threading, os

TOKEN_PATH = os.path.expanduser("~/.hermes/google_token.json")
PORT = 18765

def refresh_token():
    with open(TOKEN_PATH) as f:
        t = json.load(f)

    refresh_data = urllib.parse.urlencode({
        "client_id": t["client_id"],
        "client_secret": t["client_secret"],
        "refresh_token": t["refresh_token"],
        "grant_type": "refresh_token"
    }).encode()

    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=refresh_data, method="POST")
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        return result["access_token"], result.get("expires_in", 3600)

# Pre-fetch and cache a token
_token = None
_token_expiry = 0
_token_lock = threading.Lock()

def get_token():
    global _token, _token_expiry
    with _token_lock:
        if time.time() >= _token_expiry - 60:
            _token, expires_in = refresh_token()
            _token_expiry = time.time() + expires_in
            print(f"[token_server] Token refreshed, expires in {expires_in}s")
        return _token

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/token":
            token = get_token()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(token.encode())
        elif self.path == "/" or self.path.endswith(".html"):
            # Serve HTML from the directory where token_server.py is running
            if self.path == "/":
                path = os.path.join(os.path.dirname(__file__), "index.html")
            else:
                path = os.path.join(os.path.dirname(__file__), self.path.lstrip("/"))
            if os.path.exists(path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Not found: " + self.path.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

if __name__ == "__main__":
    # Warm up token
    get_token()
    print(f"[token_server] Running at http://localhost:{PORT}")
    print(f"[token_server] Serving HTML at http://localhost:{PORT}/")
    print(f"[token_server] Token endpoint at http://localhost:{PORT}/token")
    print("Open http://localhost:{}/ in your browser".format(PORT))

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()
