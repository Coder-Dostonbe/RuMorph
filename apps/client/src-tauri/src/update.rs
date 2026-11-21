//! App updates from the GitHub "dev" release (built by CI on every push to main).
//!
//! Windows: Tauri's updater reads `latest.json`, downloads the installer and installs it only
//! if its signature matches the public key in tauri.conf.json (plugins.updater.pubkey); the
//! private key is a CI secret. With no public key configured, updates are off.
//!
//! Android: `android.json` names the newer APK and its SHA-256; plugins/tilsim-update
//! downloads it, checks the hash and opens the system installer, which accepts it only if it
//! is signed with the same key as the installed app.

use serde::Serialize;
use tauri::AppHandle;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateInfo {
    pub version: String,
    pub current: String,
    pub notes: Option<String>,
}

/// "installer": Android's installer is open; "permission": the user must first allow Tilsim to
/// install apps (the settings page is open). On Windows the app restarts instead of returning.
#[derive(Serialize)]
pub struct InstallOutcome {
    pub status: String,
}

/// `a.b.c` → (a, b, c); anything else is not a version.
#[cfg_attr(not(target_os = "android"), allow(dead_code))]
pub fn parse_version(text: &str) -> Option<(u64, u64, u64)> {
    let core = text.trim().split(['-', '+']).next()?;
    let mut parts = core.split('.').map(|p| p.parse::<u64>().ok());
    let version = (parts.next()??, parts.next()??, parts.next()??);
    if parts.next().is_some() {
        return None;
    }
    Some(version)
}

#[cfg(desktop)]
mod imp {
    use super::{InstallOutcome, UpdateInfo};
    use tauri::AppHandle;
    use tauri_plugin_updater::UpdaterExt;

    fn configured(app: &AppHandle) -> bool {
        app.config()
            .plugins
            .0
            .get("updater")
            .and_then(|c| c.get("pubkey"))
            .and_then(|k| k.as_str())
            .is_some_and(|k| !k.trim().is_empty())
    }

    pub async fn check(app: &AppHandle) -> Result<Option<UpdateInfo>, String> {
        if !configured(app) {
            return Err("not_configured".into());
        }
        let update = app.updater().map_err(|e| e.to_string())?.check().await.map_err(|e| e.to_string())?;
        Ok(update.map(|u| UpdateInfo { version: u.version.clone(), current: u.current_version.clone(), notes: u.body.clone() }))
    }

    pub async fn install(app: &AppHandle) -> Result<InstallOutcome, String> {
        if !configured(app) {
            return Err("not_configured".into());
        }
        let update = app
            .updater()
            .map_err(|e| e.to_string())?
            .check()
            .await
            .map_err(|e| e.to_string())?
            .ok_or_else(|| "no_update".to_string())?;
        update.download_and_install(|_, _| {}, || {}).await.map_err(|e| e.to_string())?;
        // On Windows the installer closes and reopens the app itself; elsewhere restart here.
        app.restart();
    }
}

#[cfg(target_os = "android")]
mod imp {
    use super::{parse_version, InstallOutcome, UpdateInfo};
    use serde::Deserialize;
    use tauri::AppHandle;
    use tauri_plugin_tilsim_update::AndroidUpdateExt;

    const MANIFEST_URL: &str = "https://github.com/Coder-Dostonbe/RuMorph/releases/download/dev/android.json";

    #[derive(Deserialize)]
    struct Manifest {
        version: String,
        url: String,
        sha256: String,
        notes: Option<String>,
    }

    async fn newer(app: &AppHandle) -> Result<Option<Manifest>, String> {
        let text = app.android_update().fetch_text(MANIFEST_URL).await?;
        let manifest: Manifest = serde_json::from_str(&text).map_err(|e| format!("bad update description: {e}"))?;
        let remote = parse_version(&manifest.version).ok_or("bad version in update description")?;
        let current = &app.package_info().version;
        Ok((remote > (current.major, current.minor, current.patch)).then_some(manifest))
    }

    pub async fn check(app: &AppHandle) -> Result<Option<UpdateInfo>, String> {
        let current = app.package_info().version.to_string();
        Ok(newer(app).await?.map(|m| UpdateInfo { version: m.version, current, notes: m.notes }))
    }

    pub async fn install(app: &AppHandle) -> Result<InstallOutcome, String> {
        let manifest = newer(app).await?.ok_or_else(|| "no_update".to_string())?;
        let result = app.android_update().install(&manifest.url, &manifest.sha256).await?;
        Ok(InstallOutcome { status: result.status })
    }
}

#[cfg(all(mobile, not(target_os = "android")))]
mod imp {
    use super::{InstallOutcome, UpdateInfo};
    use tauri::AppHandle;

    pub async fn check(_app: &AppHandle) -> Result<Option<UpdateInfo>, String> {
        Err("not_configured".into())
    }

    pub async fn install(_app: &AppHandle) -> Result<InstallOutcome, String> {
        Err("not_configured".into())
    }
}

/// A newer version, if there is one. Error "not_configured" when updates are off in this build.
#[tauri::command]
pub async fn update_check(app: AppHandle) -> Result<Option<UpdateInfo>, String> {
    imp::check(&app).await
}

/// Downloads and installs the newer version (Windows restarts into it; Android opens its installer).
#[tauri::command]
pub async fn update_install(app: AppHandle) -> Result<InstallOutcome, String> {
    imp::install(&app).await
}

#[cfg(test)]
mod tests {
    use super::parse_version;

    #[test]
    fn versions_compare_numerically() {
        assert_eq!(parse_version("0.1.28"), Some((0, 1, 28)));
        assert_eq!(parse_version(" 1.2.3-beta "), Some((1, 2, 3)));
        assert!(parse_version("0.1.10") > parse_version("0.1.9"));
        assert_eq!(parse_version("0.1"), None);
        assert_eq!(parse_version("0.1.2.3"), None);
        assert_eq!(parse_version("x.1.2"), None);
    }
}
