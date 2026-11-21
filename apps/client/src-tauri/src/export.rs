//! Writes the admin panel's translation export to a file the admin can find and send.
//!
//! Desktop: "Tilsim-tarjimalar.json" on the Desktop, replaced by each export (an export always
//! holds every translation). The name is fixed here, so the webview cannot choose a path.
//! Android has no such folder the app may write to: the webview copies the text instead.

const FILE_NAME: &str = "Tilsim-tarjimalar.json";
const MAX_BYTES: usize = 20 * 1024 * 1024;

#[cfg(desktop)]
#[tauri::command]
pub fn export_translations(app: tauri::AppHandle, contents: String) -> Result<String, String> {
    use tauri::Manager;
    if contents.len() > MAX_BYTES {
        return Err("export too large".into());
    }
    let dir = app.path().desktop_dir().map_err(|e| format!("cannot locate the Desktop: {e}"))?;
    let target = dir.join(FILE_NAME);
    let temp = target.with_extension("tmp");
    std::fs::write(&temp, contents.as_bytes()).map_err(|e| format!("cannot write {}: {e}", temp.display()))?;
    std::fs::rename(&temp, &target).map_err(|e| format!("cannot write {}: {e}", target.display()))?;
    Ok(target.display().to_string())
}

#[cfg(mobile)]
#[tauri::command]
pub fn export_translations(_app: tauri::AppHandle, contents: String) -> Result<String, String> {
    let _ = (contents, FILE_NAME, MAX_BYTES);
    Err("unsupported".into())
}
