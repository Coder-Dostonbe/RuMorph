// Bundles core/src/tilsim_core (*.py and the lexicon data/*.json) into public/py/tilsim_core.json:
// { "version": "<core version>", "files": { "tilsim_core/bridge.py": "<source>", ... } }.
// The Pyodide worker writes these files into its virtual file system and imports
// the package from there, so the app needs no network to load its Python code.
import { createHash } from "node:crypto";
import { mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..", "..", "core", "src");
const pkg = join(root, "tilsim_core");
const out = join(here, "..", "public", "py");

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return name === "__pycache__" ? [] : walk(path);
    return name.endsWith(".py") || (name.endsWith(".json") && dir.endsWith(`${sep}data`)) ? [path] : [];
  });
}

const files = {};
for (const path of walk(pkg).sort()) {
  files[relative(root, path).split(sep).join("/")] = readFileSync(path, "utf8");
}
const init = files["tilsim_core/__init__.py"] ?? "";
const version = /__version__\s*=\s*"([^"]+)"/.exec(init)?.[1];
if (!version) {
  console.error("pack-core: __version__ not found in tilsim_core/__init__.py");
  process.exit(1);
}
const body = JSON.stringify({ version, files });
const hash = createHash("sha256").update(body).digest("hex").slice(0, 16);
mkdirSync(out, { recursive: true });
writeFileSync(join(out, "tilsim_core.json"), JSON.stringify({ version, hash, files }));
console.log(`pack-core: ${Object.keys(files).length} files, tilsim_core ${version} (${hash})`);
