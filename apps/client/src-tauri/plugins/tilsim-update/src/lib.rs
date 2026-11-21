//! Android self-update for Tilsim.
//!
//! Android does not let an app replace itself silently outside an app store. This plugin
//! downloads the newer APK into the app's private cache, checks its SHA-256, and opens the
//! system installer, where the user confirms. The installer accepts it only when it is signed
//! with the same key as the installed app. The commands are called from Rust (src/update.rs),
//! not from the webview, so the plugin grants the webview nothing.

use serde::{Deserialize, Serialize};
use tauri::{
    plugin::{Builder, TauriPlugin},
    Manager, Runtime,
};

#[cfg(target_os = "android")]
const PLUGIN_IDENTIFIER: &str = "uz.tilsim.update";

/// The plugin's handle, kept in the app state on Android.
pub struct AndroidUpdate<R: Runtime>(#[allow(dead_code)] tauri::plugin::PluginHandle<R>);

#[derive(Serialize)]
struct UrlArgs<'a> {
    url: &'a str,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct InstallArgs<'a> {
    url: &'a str,
    sha256: &'a str,
}

#[derive(Deserialize)]
struct TextResponse {
    text: String,
}

/// What `install` did: "installer" (the system installer is open) or "permission" (the user must
/// first allow this app to install apps; the settings page is open).
#[derive(Deserialize)]
pub struct InstallResponse {
    pub status: String,
}

impl<R: Runtime> AndroidUpdate<R> {
    /// GET a small text file over HTTPS (the update description).
    pub async fn fetch_text(&self, url: &str) -> Result<String, String> {
        self.0
            .run_mobile_plugin_async::<TextResponse>("fetchText", UrlArgs { url })
            .await
            .map(|r| r.text)
            .map_err(|e| e.to_string())
    }

    /// Download the APK, check its SHA-256 and open the installer.
    pub async fn install(&self, url: &str, sha256: &str) -> Result<InstallResponse, String> {
        self.0
            .run_mobile_plugin_async::<InstallResponse>("install", InstallArgs { url, sha256 })
            .await
            .map_err(|e| e.to_string())
    }
}

pub trait AndroidUpdateExt<R: Runtime> {
    fn android_update(&self) -> &AndroidUpdate<R>;
}

impl<R: Runtime, T: Manager<R>> AndroidUpdateExt<R> for T {
    fn android_update(&self) -> &AndroidUpdate<R> {
        self.state::<AndroidUpdate<R>>().inner()
    }
}

pub fn init<R: Runtime>() -> TauriPlugin<R> {
    Builder::new("tilsim-update")
        .setup(|app, api| {
            #[cfg(target_os = "android")]
            {
                let handle = api.register_android_plugin(PLUGIN_IDENTIFIER, "UpdatePlugin")?;
                app.manage(AndroidUpdate(handle));
            }
            #[cfg(not(target_os = "android"))]
            let _ = (app, api);
            Ok(())
        })
        .build()
}
