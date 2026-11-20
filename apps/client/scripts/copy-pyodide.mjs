// Copies the Pyodide runtime from node_modules into public/pyodide so the app
// ships it and works offline. Only the files the runtime needs at start-up are
// copied; Pyodide's optional package wheels are not used (tilsim_core is
// standard-library only).
import { copyFileSync, existsSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const source = dirname(require.resolve("pyodide/package.json"));
const target = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "pyodide");

const NEEDED = ["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"];

mkdirSync(target, { recursive: true });
let bytes = 0;
for (const name of NEEDED) {
  const from = join(source, name);
  if (!existsSync(from)) {
    console.error(`copy-pyodide: ${name} is missing from ${source}`);
    process.exit(1);
  }
  const to = join(target, name);
  const size = statSync(from).size;
  if (!existsSync(to) || statSync(to).size !== size) copyFileSync(from, to);
  bytes += size;
}
const extra = readdirSync(target).filter((f) => !NEEDED.includes(f));
if (extra.length) console.warn(`copy-pyodide: unexpected files in public/pyodide: ${extra.join(", ")}`);
console.log(`copy-pyodide: ${NEEDED.length} files, ${(bytes / 1024 / 1024).toFixed(1)} MB`);
