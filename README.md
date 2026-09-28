# ChatWrapped

I saw this on Instagram and wanted to reimplement. It’s essentially Spotify Wrapped, but for your IMessage group chat. Measures laugh, heart, skull, or sob reactions with various metrics.

Runs entirely on your Mac. Nothing is uploaded.

## Use

```bash
pipx install git+https://github.com/dhruvraajeev/chatwrapped
chatwrapped
```

Pick a chat and your dashboard opens in the browser. On first run, give your terminal
**Full Disk Access** (System Settings → Privacy & Security) so it can read Messages.

Sharing it with the group? `chatwrapped --hide-text` leaves message text out.
