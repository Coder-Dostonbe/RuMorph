// The device's SQLite database. Its schema is created by the migrations in
// db/sqlite/migrations, which the Rust shell runs when the database is opened.
import Database from "@tauri-apps/plugin-sql";
import { inTauri } from "../app/platform";

export const DB_URL = "sqlite:tilsim.db";

let opened: Promise<Database> | null = null;

/** The database, or null when running in a plain browser during development. */
export function database(): Promise<Database> | null {
  if (!inTauri) return null;
  opened ??= Database.load(DB_URL);
  return opened;
}
