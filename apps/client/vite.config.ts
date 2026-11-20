import { readFileSync } from "node:fs";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

const pkg = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf8")) as { version: string };

// Tauri expects a fixed port and must see Rust-side errors in the terminal.
export default defineConfig({
  plugins: [vue()],
  clearScreen: false,
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
  server: {
    port: 1420,
    strictPort: true,
    host: process.env.TAURI_DEV_HOST || false,
    watch: { ignored: ["**/src-tauri/**"] },
  },
  worker: { format: "es" },
  build: {
    target: "es2022",
    chunkSizeWarningLimit: 1000,
  },
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
    testTimeout: 60_000,
  },
});
