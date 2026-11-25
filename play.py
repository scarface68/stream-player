#!/usr/bin/env python3
"""Light HLS (.m3u8) stream player. Stdlib only.

Run:  python3 play.py

Opens the player in your browser. Add, rename, remove and switch channels there.
Channels are saved in channels.json next to this file.

A local proxy fetches the streams (avoids CORS / keeps auth tokens on segment
requests) and the page plays them with hls.js.
"""
import http.cookiejar
import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

CHANNELS_FILE = os.path.join(HERE, "channels.json")


def load_channels():
    try:
        with open(CHANNELS_FILE) as f:
            return [c for c in json.load(f) if c.get("url")]
    except (OSError, ValueError):
        return []


def save_channels(chs):
    with open(CHANNELS_FILE, "w") as f:
        json.dump(chs, f, indent=2)


STATE = {"channels": []}
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return opener.open(req, timeout=20)


def proxied(child, parent):
    """Absolute-ize a playlist URI and route it through the proxy.
    If the child has no query string, inherit the parent's (e.g. Akamai hdnea token)."""
    absu = urllib.parse.urljoin(parent, child)
    p = urllib.parse.urlsplit(absu)
    if not p.query:
        q = urllib.parse.urlsplit(parent).query
        if q:
            absu = urllib.parse.urlunsplit(p._replace(query=q))
    return "/proxy?url=" + urllib.parse.quote(absu, safe="")


def rewrite_playlist(text, base):
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            out.append(line)
        elif s.startswith("#"):
            # rewrite URI="..." attributes (keys, alt audio, subtitles, maps)
            if 'URI="' in s:
                pre, rest = s.split('URI="', 1)
                uri, post = rest.split('"', 1)
                s = pre + 'URI="' + proxied(uri, base) + '"' + post
            out.append(s)
        else:
            out.append(proxied(s, base))
    return "\n".join(out) + "\n"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path, _, qs = self.path.partition("?")
        params = urllib.parse.parse_qs(qs)
        if path == "/":
            with open(os.path.join(HERE, "player.html"), "rb") as f:
                return self.send(200, f.read(), "text/html; charset=utf-8")
        if path == "/channels":
            return self.send(200, json.dumps(STATE["channels"]).encode(), "application/json")
        if path == "/proxy" and "url" in params:
            url = params["url"][0]
            try:
                with fetch(url) as r:
                    data = r.read()
                    ctype = r.headers.get("Content-Type", "application/octet-stream")
                    final = r.geturl()
            except urllib.error.HTTPError as e:
                print(f"  ! HTTP {e.code} from {url[:90]}...")
                return self.send(e.code, str(e).encode(), "text/plain")
            except Exception as e:
                print(f"  ! fetch failed: {e}  ({url[:90]}...)")
                return self.send(502, str(e).encode(), "text/plain")
            if b"#EXTM3U" in data[:64]:
                text = rewrite_playlist(data.decode("utf-8", "replace"), final)
                return self.send(200, text.encode(), "application/vnd.apple.mpegurl")
            return self.send(200, data, ctype)
        self.send(404, b"not found", "text/plain")

    def do_POST(self):
        if self.path != "/channels":
            return self.send(404, b"not found", "text/plain")
        try:
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            chs = [{"name": str(c.get("name") or ""), "url": str(c["url"])}
                   for c in json.loads(body) if c.get("url")]
        except (ValueError, KeyError, TypeError, AttributeError):
            return self.send(400, b"bad channel list", "text/plain")
        STATE["channels"] = chs
        save_channels(chs)
        self.send(200, b"ok", "text/plain")


def main():
    STATE["channels"] = load_channels()

    # Fixed port keeps the page's origin stable, so it remembers your last channel.
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    except OSError:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    addr = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Player running at {addr}  (Ctrl+C to quit)")
    threading.Timer(0.5, lambda: webbrowser.open(addr)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBye.")


if __name__ == "__main__":
    main()
