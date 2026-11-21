//! Tilsim app shell (Windows and Android).
//!
//! The shell stays small: the UI and its data layer are in the webview, the
//! domain logic runs in Pyodide inside the webview. Rust owns only what the
//! webview must not do itself: the SQLite database (through tauri-plugin-sql,
//! with the migrations in db/sqlite/migrations), the refresh token and the admin
//! password hash (secret.rs), and writing the admin's translation export (export.rs).

mod export;
mod secret;
#[cfg(desktop)]
mod window;

use tauri_plugin_sql::{Migration, MigrationKind};

/// Must match DB_URL in src/data/db.ts.
const DB_URL: &str = "sqlite:tilsim.db";

fn migrations() -> Vec<Migration> {
    vec![
        Migration {
            version: 1,
            description: "init",
            sql: include_str!("../../../../db/sqlite/migrations/0001_init.sql"),
            kind: MigrationKind::Up,
        },
        Migration {
            version: 2,
            description: "learning",
            sql: include_str!("../../../../db/sqlite/migrations/0002_learning.sql"),
            kind: MigrationKind::Up,
        },
        Migration {
            version: 3,
            description: "admin_translations",
            sql: include_str!("../../../../db/sqlite/migrations/0003_admin_translations.sql"),
            kind: MigrationKind::Up,
        },
    ]
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(
            tauri_plugin_sql::Builder::default()
                .add_migrations(DB_URL, migrations())
                .build(),
        )
        .setup(|app| {
            // The main window has "create": false in tauri.conf.json and is built here,
            // so it is created at its final size (see window.rs).
            #[cfg(desktop)]
            window::create_main(app.handle())?;
            #[cfg(mobile)]
            {
                let config = app.config().app.windows.iter().find(|w| w.label == "main").cloned();
                if let Some(config) = config {
                    tauri::WebviewWindowBuilder::from_config(app.handle(), &config)?.build()?;
                }
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            secret::secret_get,
            secret::secret_set,
            secret::secret_delete,
            export::export_translations
        ])
        .run(tauri::generate_context!())
        .expect("error while running Tilsim");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn migrations_are_numbered_from_one_without_gaps() {
        for (index, migration) in migrations().iter().enumerate() {
            assert_eq!(migration.version, index as i64 + 1);
            assert!(!migration.sql.trim().is_empty());
        }
    }
}
