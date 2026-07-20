# Komari Theme Market

This repository contains the default catalog used by Komari's built-in theme market.
Theme packages remain hosted by their authors, usually as GitHub Release assets.

## Catalog

The production catalog is [`v1.json`](./v1.json). Each entry uses this shape:

```json
{
  "name": {
    "zh-CN": "Komari 测试主题",
    "en": "Komari Test Theme"
  },
  "short": "TestTheme",
  "description": {
    "zh-CN": "一个用于 Komari 的测试主题",
    "en": "A test theme for Komari"
  },
  "version": "1.0.0",
  "author": "Akizon77",
  "url": "https://github.com/komari-monitor/komari",
  "preview": "https://example.com/preview.png",
  "download": "https://example.com/theme.zip",
  "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
}
```

`name`, `description`, and `author` accept either a string or an i18n object such
as `{"zh-CN":"...","en":"..."}`. The market selects an exact locale, then a
base-language match, then the first available value.

`preview` and `download` must be absolute HTTP(S) URLs; HTTPS is strongly recommended.
`download` must point to a Komari theme ZIP containing `komari-theme.json`, and
`sha256` is the lowercase SHA-256 digest of that exact ZIP file. Omit both
`download` and `sha256` for a source-only entry; it will be listed without an
install action.

Submit additions and updates through pull requests. Keep `short`, `version`, and
the package manifest in sync; the Komari server verifies them before installation.
Keep entries sorted by `short` (case-insensitive A-Z); CI enforces this. Run
`node scripts/check-catalog-order.mjs --write` to apply the canonical order.

Every six hours, GitHub Actions checks installable themes backed by GitHub Release
assets. It combines a URL built from the repository URL, latest release tag, and
current asset name with the Release API asset URL as a fallback. A package is only
proposed in a pull request after its root `komari-theme.json`, `short`, `version`,
and SHA-256 have been verified.
