//! Small secrets (the refresh token) kept outside the webview and the database.
//!
//! Windows: Windows Credential Manager, one entry per name under the service
//! "Tilsim". Other platforms (Android, and Linux used for development and CI):
//! a file per name in the app's private data folder, which other apps cannot
//! read on Android. Names are restricted to `[a-z_]{1,40}` so they can never
//! form a path.

use tauri::AppHandle;

fn valid_name(name: &str) -> Result<(), String> {
    if !name.is_empty() && name.len() <= 40 && name.bytes().all(|b| b.is_ascii_lowercase() || b == b'_') {
        Ok(())
    } else {
        Err("invalid secret name".into())
    }
}

#[cfg(windows)]
mod backend {
    use tauri::AppHandle;

    const SERVICE: &str = "Tilsim";

    fn entry(name: &str) -> Result<keyring::Entry, String> {
        keyring::Entry::new(SERVICE, name).map_err(|e| format!("credential store: {e}"))
    }

    pub fn get(_app: &AppHandle, name: &str) -> Result<Option<String>, String> {
        match entry(name)?.get_password() {
            Ok(value) => Ok(Some(value)),
            Err(keyring::Error::NoEntry) => Ok(None),
            Err(e) => Err(format!("credential store: {e}")),
        }
    }

    pub fn set(_app: &AppHandle, name: &str, value: &str) -> Result<(), String> {
        entry(name)?.set_password(value).map_err(|e| format!("credential store: {e}"))
    }

    pub fn delete(_app: &AppHandle, name: &str) -> Result<(), String> {
        match entry(name)?.delete_credential() {
            Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
            Err(e) => Err(format!("credential store: {e}")),
        }
    }
}

#[cfg(not(windows))]
mod backend {
    use std::fs;
    use std::io::Write;
    use std::path::PathBuf;
    use tauri::{AppHandle, Manager};

    fn path(app: &AppHandle, name: &str) -> Result<PathBuf, String> {
        let dir = app
            .path()
            .app_local_data_dir()
            .map_err(|e| format!("cannot locate app data: {e}"))?
            .join("secrets");
        fs::create_dir_all(&dir).map_err(|e| format!("cannot create secrets folder: {e}"))?;
        Ok(dir.join(name))
    }

    pub fn get(app: &AppHandle, name: &str) -> Result<Option<String>, String> {
        match fs::read_to_string(path(app, name)?) {
            Ok(value) => Ok(Some(value)),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
            Err(e) => Err(format!("cannot read secret: {e}")),
        }
    }

    pub fn set(app: &AppHandle, name: &str, value: &str) -> Result<(), String> {
        let target = path(app, name)?;
        let temp = target.with_extension("tmp");
        let mut options = fs::OpenOptions::new();
        options.write(true).create(true).truncate(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.mode(0o600);
        }
        let mut file = options.open(&temp).map_err(|e| format!("cannot write secret: {e}"))?;
        file.write_all(value.as_bytes())
            .and_then(|_| file.sync_all())
            .map_err(|e| format!("cannot write secret: {e}"))?;
        fs::rename(&temp, &target).map_err(|e| format!("cannot write secret: {e}"))
    }

    pub fn delete(app: &AppHandle, name: &str) -> Result<(), String> {
        match fs::remove_file(path(app, name)?) {
            Ok(()) => Ok(()),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
            Err(e) => Err(format!("cannot delete secret: {e}")),
        }
    }
}

#[tauri::command]
pub fn secret_get(app: AppHandle, name: String) -> Result<Option<String>, String> {
    valid_name(&name)?;
    backend::get(&app, &name)
}

#[tauri::command]
pub fn secret_set(app: AppHandle, name: String, value: String) -> Result<(), String> {
    valid_name(&name)?;
    if value.len() > 4096 {
        return Err("secret is too long".into());
    }
    backend::set(&app, &name, &value)
}

#[tauri::command]
pub fn secret_delete(app: AppHandle, name: String) -> Result<(), String> {
    valid_name(&name)?;
    backend::delete(&app, &name)
}

#[cfg(test)]
mod tests {
    use super::valid_name;

    #[test]
    fn names_cannot_form_paths() {
        assert!(valid_name("refresh_token").is_ok());
        for bad in ["", "../x", "a/b", "A", "x.y", "token1", &"a".repeat(41)] {
            assert!(valid_name(bad).is_err(), "{bad:?} should be refused");
        }
    }
}
