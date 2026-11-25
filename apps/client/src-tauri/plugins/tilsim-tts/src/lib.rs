//! Android text-to-speech for Zabon.
//!
//! Android's webview has no `speechSynthesis`, so words without a recorded pronunciation are
//! read by the phone's own TTS engine through this plugin (android/.../TtsPlugin.kt). The
//! commands are called from Rust (src/tts.rs), not from the webview, so the plugin grants the
//! webview nothing.

use serde::{Deserialize, Serialize};
use tauri::{
    plugin::{Builder, TauriPlugin},
    Manager, Runtime,
};

#[cfg(target_os = "android")]
const PLUGIN_IDENTIFIER: &str = "uz.tilsim.tts";

/// The plugin's handle, kept in the app state on Android.
pub struct AndroidTts<R: Runtime>(#[allow(dead_code)] tauri::plugin::PluginHandle<R>);

#[derive(Serialize)]
struct NoArgs {}

#[derive(Serialize)]
struct SpeakArgs<'a> {
    text: &'a str,
}

/// "ready", "no_engine" or "no_russian".
#[derive(Deserialize)]
pub struct TtsState {
    pub state: String,
}

impl<R: Runtime> AndroidTts<R> {
    pub async fn status(&self) -> Result<TtsState, String> {
        self.0
            .run_mobile_plugin_async::<TtsState>("status", NoArgs {})
            .await
            .map_err(|e| e.to_string())
    }

    pub async fn speak(&self, text: &str) -> Result<TtsState, String> {
        self.0
            .run_mobile_plugin_async::<TtsState>("speak", SpeakArgs { text })
            .await
            .map_err(|e| e.to_string())
    }
}

pub trait AndroidTtsExt<R: Runtime> {
    fn android_tts(&self) -> &AndroidTts<R>;
}

impl<R: Runtime, T: Manager<R>> AndroidTtsExt<R> for T {
    fn android_tts(&self) -> &AndroidTts<R> {
        self.state::<AndroidTts<R>>().inner()
    }
}

pub fn init<R: Runtime>() -> TauriPlugin<R> {
    Builder::new("tilsim-tts")
        .setup(|app, api| {
            #[cfg(target_os = "android")]
            {
                let handle = api.register_android_plugin(PLUGIN_IDENTIFIER, "TtsPlugin")?;
                app.manage(AndroidTts(handle));
            }
            #[cfg(not(target_os = "android"))]
            let _ = (app, api);
            Ok(())
        })
        .build()
}
