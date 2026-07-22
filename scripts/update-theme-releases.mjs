import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const catalogPath = new URL("../v1.json", import.meta.url);
const dryRun = process.argv.includes("--dry-run");
const prBodyArgument = process.argv.find((argument) => argument.startsWith("--pr-body="));
const prBodyPath = prBodyArgument?.slice("--pr-body=".length);
const catalog = JSON.parse(fs.readFileSync(catalogPath, "utf8"));
const githubToken = process.env.GITHUB_TOKEN;

const compareShort = (left, right) => {
  const a = String(left.short).toUpperCase();
  const b = String(right.short).toUpperCase();
  if (a < b) return -1;
  if (a > b) return 1;
  return String(left.short).localeCompare(String(right.short));
};

function githubRepository(theme) {
  try {
    const url = new URL(theme.url);
    if (!["github.com", "www.github.com"].includes(url.hostname.toLowerCase())) return null;
    const [owner, repo] = url.pathname.split("/").filter(Boolean);
    return owner && repo ? { owner, repo: repo.replace(/\.git$/i, ""), url: `https://github.com/${owner}/${repo.replace(/\.git$/i, "")}` } : null;
  } catch {
    return null;
  }
}

function currentAssetName(theme) {
  try {
    return decodeURIComponent(new URL(theme.download).pathname.split("/").at(-1));
  } catch {
    return null;
  }
}

function currentReleaseTag(theme) {
  try {
    const parts = new URL(theme.download).pathname.split("/").filter(Boolean);
    const downloadIndex = parts.indexOf("download");
    return downloadIndex >= 0 && parts.length > downloadIndex + 1
      ? decodeURIComponent(parts[downloadIndex + 1])
      : null;
  } catch {
    return null;
  }
}

async function githubJSON(pathname) {
  const response = await fetch(`https://api.github.com${pathname}`, {
    headers: {
      Accept: "application/vnd.github+json",
      "User-Agent": "komari-theme-market-release-monitor",
      ...(githubToken ? { Authorization: `Bearer ${githubToken}` } : {}),
    },
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`GitHub API returned HTTP ${response.status}`);
  return response.json();
}

async function fetchPackage(url) {
  const response = await fetch(url, { headers: { "User-Agent": "komari-theme-market-release-monitor" } });
  if (!response.ok) throw new Error(`download returned HTTP ${response.status}`);
  return Buffer.from(await response.arrayBuffer());
}

function readManifest(packageData) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "komari-theme-market-"));
  const packagePath = path.join(directory, "theme.zip");
  try {
    fs.writeFileSync(packagePath, packageData);
    const manifest = execFileSync("unzip", ["-p", packagePath, "komari-theme.json"], {
      encoding: "utf8",
      maxBuffer: 1024 * 1024,
    });
    return JSON.parse(manifest);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}

async function updateTheme(theme) {
  if (!theme.download || !theme.sha256) return false;
  const repository = githubRepository(theme);
  const assetName = currentAssetName(theme);
  const releaseTag = currentReleaseTag(theme);
  if (!repository || !assetName || !releaseTag) return false;

  const release = await githubJSON(`/repos/${repository.owner}/${repository.repo}/releases/latest`);
  if (!release?.tag_name) return false;
  if (release.tag_name === releaseTag) return false;

  const matchingAsset = release.assets?.find((asset) => asset.name === assetName);
  const zipAssets = release.assets?.filter((asset) => asset.name.toLowerCase().endsWith(".zip")) ?? [];
  const candidates = [
    // Keep the catalog URL scheme as the primary path; this also works when GitHub's API asset link changes.
    `${repository.url}/releases/download/${encodeURIComponent(release.tag_name)}/${encodeURIComponent(assetName)}`,
    matchingAsset?.browser_download_url,
    !matchingAsset && zipAssets.length === 1 ? zipAssets[0].browser_download_url : undefined,
  ].filter((url, index, list) => url && list.indexOf(url) === index);

  if (candidates.length === 0) {
    console.warn(`${theme.short}: latest release ${release.tag_name} has no unambiguous ZIP asset`);
    return false;
  }

  let packageData;
  let downloadURL;
  for (const candidate of candidates) {
    try {
      packageData = await fetchPackage(candidate);
      downloadURL = candidate;
      break;
    } catch (error) {
      console.warn(`${theme.short}: could not download ${candidate} (${error.message})`);
    }
  }
  if (!packageData || !downloadURL) return false;

  let manifest;
  try {
    manifest = readManifest(packageData);
  } catch (error) {
    console.warn(`${theme.short}: package does not contain a valid root komari-theme.json (${error.message})`);
    return false;
  }
  if (manifest.short !== theme.short || !manifest.version) {
    console.warn(`${theme.short}: manifest short/version does not match the catalog`);
    return false;
  }

  const sha256 = createHash("sha256").update(packageData).digest("hex");
  if (theme.version === manifest.version && theme.download === downloadURL && theme.sha256 === sha256) {
    return null;
  }

  const previous = {
    version: theme.version,
    releaseTag,
    assetName,
  };
  theme.version = manifest.version;
  theme.download = downloadURL;
  theme.sha256 = sha256;
  console.log(`${theme.short}: updated from release ${release.tag_name}`);
  return {
    short: theme.short,
    repository: repository.url,
    previous,
    releaseTag: release.tag_name,
    assetName: currentAssetName({ download: downloadURL }) ?? assetName,
    version: manifest.version,
    sha256,
  };
}

const updates = [];
for (const theme of catalog.themes) {
  try {
    const update = await updateTheme(theme);
    if (update) updates.push(update);
  } catch (error) {
    console.warn(`${theme.short}: release check failed (${error.message})`);
  }
}

function escapeTableCell(value) {
  return String(value).replaceAll("|", "\\|");
}

function formatPRBody(themeUpdates) {
  if (themeUpdates.length === 0) {
    return "## Verified Komari theme release packages\n\nNo catalog changes were detected.";
  }

  const inlineCode = (value) => `\`${escapeTableCell(value)}\``;
  const rows = themeUpdates.map((update) => [
    `[${escapeTableCell(update.short)}](${update.repository})`,
    `${inlineCode(update.previous.version)} -> ${inlineCode(update.version)}`,
    `${inlineCode(update.previous.releaseTag)} -> ${inlineCode(update.releaseTag)}`,
    inlineCode(update.assetName),
  ].join(" | "));
  const checksums = themeUpdates.map((update) => `- ${inlineCode(update.short)}: ${inlineCode(update.sha256)}`);

  return [
    "## Verified Komari theme release packages",
    "",
    "The scheduled release monitor found the following verified package updates:",
    "",
    "| Theme | Catalog version | GitHub Release | Package asset |",
    "| --- | --- | --- | --- |",
    ...rows,
    "",
    "Each package was downloaded from its latest GitHub Release and verified against its root `komari-theme.json`: the manifest `short` matches the catalog entry, the manifest contains a version, and the catalog SHA-256 below was recalculated from that exact ZIP.",
    "",
    "<details>",
    "<summary>Verified SHA-256 checksums</summary>",
    "",
    ...checksums,
    "",
    "</details>",
  ].join("\n");
}

if (updates.length > 0) {
  catalog.themes.sort(compareShort);
  catalog.updated_at = new Date().toISOString();
  if (!dryRun) fs.writeFileSync(catalogPath, `${JSON.stringify(catalog, null, 2)}\n`);
  console.log(dryRun ? "Theme updates found (dry run)" : "Updated v1.json");
} else {
  console.log("No theme release updates found");
}

if (prBodyPath) {
  fs.writeFileSync(prBodyPath, `${formatPRBody(updates)}\n`);
}
