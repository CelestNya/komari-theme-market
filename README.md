# Komari Theme Market

This repository contains the default catalog used by Komari's built-in theme market.
Theme packages remain hosted by their authors, usually as GitHub Release assets.

## Catalog

The production catalog is [`v1.json`](./v1.json). Each entry uses this shape:

```json
{
  "name": "Komari Test Theme",
  "short": "TestTheme",
  "description": "A test theme for Komari",
  "version": "1.0.0",
  "author": "Akizon77",
  "url": "https://github.com/komari-monitor/komari",
  "preview": "https://example.com/preview.png",
  "download": "https://example.com/theme.zip",
  "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
}
```

`preview` and `download` must be absolute HTTP(S) URLs; HTTPS is strongly recommended. `download` must point to a
Komari theme ZIP containing `komari-theme.json`. `sha256` is the lowercase SHA-256
digest of that exact ZIP file.

Submit additions and updates through pull requests. Keep `short`, `version`, and
the package manifest in sync; the Komari server verifies them before installation.
