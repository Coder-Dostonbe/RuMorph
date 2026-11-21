// Sets the app version for a release build: `node scripts/set-version.mjs 0.1.42`.
// CI calls it with 0.1.<run number>, so every build is newer than the previous one; the updater
// (src-tauri/src/update.rs) and Android's versionCode (major*1000000 + minor*1000 + patch) rely
// on that. It edits package.json (shown in the app) and src-tauri/tauri.conf.json (the bundle).
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const version = process.argv[2] ?? "";
const match = /^(\d+)\.(\d+)\.(\d+)$/.exec(version);
if (!match || Number(match[3]) > 999 || Number(match[2]) > 999) {
  console.error(`usage: set-version.mjs <major.minor.patch> (minor and patch at most 999), got "${version}"`);
  process.exit(1);
}

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
for (const file of ["package.json", "src-tauri/tauri.conf.json"]) {
  const path = join(root, file);
  const data = JSON.parse(readFileSync(path, "utf8"));
  data.version = version;
  writeFileSync(path, `${JSON.stringify(data, null, 2)}\n`);
}
console.log(`version ${version}`);
