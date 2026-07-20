import fs from "node:fs";

const catalogPath = new URL("../v1.json", import.meta.url);
const write = process.argv.includes("--write");
const catalog = JSON.parse(fs.readFileSync(catalogPath, "utf8"));

if (!Array.isArray(catalog.themes)) {
  throw new Error("v1.json must contain a themes array");
}

const compareShort = (left, right) => {
  const a = String(left.short).toUpperCase();
  const b = String(right.short).toUpperCase();
  if (a < b) return -1;
  if (a > b) return 1;
  return String(left.short).localeCompare(String(right.short));
};

const seen = new Set();
for (const theme of catalog.themes) {
  if (typeof theme.short !== "string" || !theme.short) {
    throw new Error("Every theme must have a non-empty short field");
  }
  const key = theme.short.toUpperCase();
  if (seen.has(key)) {
    throw new Error(`Duplicate theme short: ${theme.short}`);
  }
  seen.add(key);
}

const sorted = [...catalog.themes].sort(compareShort);
const outOfOrder = catalog.themes.findIndex((theme, index) => theme !== sorted[index]);

if (write) {
  catalog.themes = sorted;
  fs.writeFileSync(catalogPath, `${JSON.stringify(catalog, null, 2)}\n`);
  console.log("Sorted v1.json by themes[].short");
  process.exit(0);
}

if (outOfOrder !== -1) {
  throw new Error(
    `themes is not sorted by short at index ${outOfOrder}: expected ${sorted[outOfOrder].short}, found ${catalog.themes[outOfOrder].short}. Run: node scripts/check-catalog-order.mjs --write`,
  );
}

console.log(`v1.json is sorted by short (${catalog.themes.length} themes)`);
