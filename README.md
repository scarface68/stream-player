# Stream Player

Lightweight HLS (.m3u8) player with TV-style channels. Needs only Python 3 (built into macOS) and a browser.

```
cd ~/Desktop/stream-player
python3 play.py
```

The player opens in your browser. Everything else happens there. Ctrl+C in the terminal stops it.

## Channels

- **Add:** click **+ Add** and paste one or more links, one per line. To name one, write `Name | link`.
- **Manage:** click **☰ Channels** (or press `C`) to rename, reorder (↑ ↓), play (▶), or remove (✕) channels, or to remove them all.
- Channels are saved in `channels.json` in this folder, so they're still there next time.

## Switching

- Click a channel in the top bar, or use the remote keys:
  - `↑` / `↓` (or `N` / `P`): next / previous channel
  - `1`–`9`: jump to a channel
  - `L`: back to the last channel
- The player reopens on the channel you watched last.
- If a link has expired, the status line says so. Paste a fresh one and remove the old one.

## Files

- `play.py`: local server. It serves the page, stores channels, and proxies streams (avoids browser CORS blocks and keeps auth tokens on each request).
- `player.html`: the app (hls.js player and channel manager).
