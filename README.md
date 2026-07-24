# Komari Theme Market

Komari Theme Market 是 Komari 内置主题市场使用的默认主题目录。主题包仍由主题作者托管，市场目录保存主题元数据、下载地址和 SHA-256 校验值。

Komari Theme Market is the default catalog used by Komari's built-in theme market. Theme packages remain hosted by their authors; this repository stores theme metadata, download URLs and SHA-256 checksums.

## 目录 / Catalog

生产目录为 [`v1.json`](./v1.json)。每个可安装主题包含以下字段：

The production catalog is [`v1.json`](./v1.json). Each installable theme contains these fields:

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

`name`、`description` 和 `author` 可以是普通字符串，也可以是多语言对象，例如 `{"zh-CN":"...","en":"..."}`。市场会依次尝试精确语言、基础语言和对象中的第一个值。

`name`, `description` and `author` may be strings or i18n objects such as `{"zh-CN":"...","en":"..."}`. The market tries the exact locale, the base language and then the first available value in that order.

`preview` 和 `download` 必须是绝对 HTTP(S) URL。`download` 必须指向包含根目录 `komari-theme.json` 的 Komari 主题 ZIP，`sha256` 必须是该 ZIP 的小写 SHA-256。没有安装包的来源条目可以同时省略 `download` 和 `sha256`。

`preview` and `download` must be absolute HTTP(S) URLs. `download` must point to a Komari theme ZIP containing a root-level `komari-theme.json`, and `sha256` must be the lowercase SHA-256 digest of that exact ZIP. A source-only entry may omit both `download` and `sha256`.

目录中的主题必须按 `short` 不区分大小写排序，且不能出现重复的 `short`。

Themes must be sorted by `short` case-insensitively, and duplicate `short` values are not allowed.

```text
node scripts/check-catalog-order.mjs
```

## 提交主题 / Submit a Theme

请在 [Issue 页面](../../issues/new/choose) 选择对应模板。不要手动拼接字段名称，Action 会按 Issue Form 的固定字段读取内容。

Choose the appropriate bilingual template on the [new issue page](../../issues/new/choose). Do not rename or manually rearrange field headings; the Action reads the fixed Issue Form fields.

### 在 GitHub 中开源的主题 / Open-source GitHub Theme

模板位置 / Template: [`submit-github-theme.yml`](./.github/ISSUE_TEMPLATE/submit-github-theme.yml)

只需要填写 GitHub 仓库地址和预览图链接，并确认仓库公开且最新 Release 提供主题包。

Only the GitHub repository URL and a preview image URL are required, together with confirmation that the repository is public and its latest Release provides a theme package.

### 非 GitHub 托管的主题 / Theme Hosted Outside GitHub

模板位置 / Template: [`submit-external-theme.yml`](./.github/ISSUE_TEMPLATE/submit-external-theme.yml)

需要填写项目地址、主题包下载地址、预览图、主题名称、主题唯一短名称、版本、描述和作者。项目地址和主题包地址不能是 GitHub 托管地址。

Provide the project URL, package download URL, preview image URL, theme name, unique theme short name, version, description and author. The project and package URLs must not be GitHub-hosted URLs.

## Release Updates / Release 自动更新

现有 Release 更新工作流每六小时运行一次。它只处理目录中由 GitHub 仓库支持、已有安装包和 SHA-256 的主题，使用仓库地址、最新 Release 标签和当前资源名构造下载地址，并以 GitHub API 资源地址作为后备。下载包通过根 manifest、`short`、版本和 SHA-256 校验后，Action 才会创建 PR。

The existing Release update workflow runs every six hours. It only processes catalog themes backed by GitHub repositories with an installable package and SHA-256. It constructs a download URL from the repository URL, latest Release tag and current asset name, with the GitHub API asset URL as a fallback. A PR is created only after the package passes root-manifest, `short`, version and SHA-256 checks.
