#!/usr/bin/env node
// 从上游 v1.json 生成镜像目录 v1-mirror.json：
// 把每个主题的 download / preview 套上镜像前缀（ghproxy 类透传代理），
// SHA-256 保持原样（透传代理不改变文件字节），url 保留原始项目地址。
//
// 用法：
//   node scripts/build-mirror-catalog.mjs [输入v1.json] [--output=输出文件名]
// 镜像前缀通过环境变量 MIRROR_PREFIX 提供，未设置时使用默认值。

import fs from "node:fs";
import path from "node:path";

const DEFAULT_MIRROR_PREFIX = "https://gh-proxy.com/";
const args = process.argv.slice(2);
const inputPath = args.find((argument) => !argument.startsWith("--")) ?? "v1.json";
const outputPath =
  args.find((argument) => argument.startsWith("--output="))?.slice("--output=".length) ?? "v1-mirror.json";
const mirrorPrefix = (process.env.MIRROR_PREFIX || DEFAULT_MIRROR_PREFIX).replace(/\/+$/, "") + "/";

const catalog = JSON.parse(fs.readFileSync(path.resolve(inputPath), "utf8"));
if (!Array.isArray(catalog.themes)) {
  throw new Error("input catalog must contain a themes array");
}

// 只为非空、绝对的 HTTP(S) URL 加前缀；保留原样不动其它字段。
function mirror(url) {
  if (typeof url !== "string" || !url) return url;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return url;
  } catch {
    return url;
  }
  return mirrorPrefix + url;
}

const changed = [];
for (const theme of catalog.themes) {
  const download = theme.download;
  const preview = theme.preview;
  theme.download = mirror(theme.download);
  theme.preview = mirror(theme.preview);
  if (theme.download !== download || theme.preview !== preview) {
    changed.push(theme.short);
  }
}

fs.writeFileSync(path.resolve(outputPath), `${JSON.stringify(catalog, null, 2)}\n`);
console.log(`Mirrored ${changed.length}/${catalog.themes.length} themes into ${outputPath} via ${mirrorPrefix}`);
if (changed.length) {
  console.log(`Changed: ${changed.join(", ")}`);
}
