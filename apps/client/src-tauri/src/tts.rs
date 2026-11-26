//! The device's own voice for words without a recorded pronunciation.
//!
//! Windows: the webview has `speechSynthesis` with the voices installed in Windows, so these
//! commands are not used there ("unsupported"). Android: the webview has none, so the phone's
//! text-to-speech engine is reached through plugins/tilsim-tts.
//!
//! Result: "ready", "no_engine", "no_russian" or "unsupported".

#[cfg(target_os = "android")]
mod imp {
    use tauri::AppHandle;
    use tauri_plugin_tilsim_tts::AndroidTtsExt;

    pub async fn status(app: &AppHandle) -> Result<String, String> {
        Ok(app.android_tts().status().await?.state)
    }

    pub async fn speak(app: &AppHandle, text: &str, rate: f32) -> Result<String, String> {
        Ok(app.android_tts().speak(text, rate).await?.state)
    }
}

#[cfg(not(target_os = "android"))]
mod imp {
    use tauri::AppHandle;

    pub async fn status(_app: &AppHandle) -> Result<String, String> {
        Ok("unsupported".into())
    }

    pub async fn speak(_app: &AppHandle, _text: &str, _rate: f32) -> Result<String, String> {
        Err("unsupported".into())
    }
}

/// At most a short phrase: this reads single words.
fn checked(text: &str) -> Result<&str, String> {
    let text = text.trim();
    if text.is_empty() || text.chars().count() > 100 {
        return Err("bad_text".into());
    }
    Ok(text)
}

#[tauri::command]
pub async fn tts_status(app: tauri::AppHandle) -> Result<String, String> {
    imp::status(&app).await
}

/// Speech rate: 1.0 is the engine's normal speed; the app goes down to a quarter of it.
fn checked_rate(rate: Option<f32>) -> Result<f32, String> {
    let rate = rate.unwrap_or(0.85);
    if !rate.is_finite() || !(0.25..=1.0).contains(&rate) {
        return Err("bad_rate".into());
    }
    Ok(rate)
}

#[tauri::command]
pub async fn tts_speak(app: tauri::AppHandle, text: String, rate: Option<f32>) -> Result<String, String> {
    imp::speak(&app, checked(&text)?, checked_rate(rate)?).await
}

#[cfg(test)]
mod tests {
    use super::{checked, checked_rate};

    #[test]
    fn text_must_be_a_short_word() {
        assert_eq!(checked(" книга "), Ok("книга"));
        assert!(checked("").is_err());
        assert!(checked(&"а".repeat(101)).is_err());
    }

    #[test]
    fn rate_stays_in_range() {
        assert_eq!(checked_rate(None), Ok(0.85));
        assert_eq!(checked_rate(Some(0.425)), Ok(0.425));
        assert!(checked_rate(Some(0.1)).is_err());
        assert!(checked_rate(Some(2.0)).is_err());
        assert!(checked_rate(Some(f32::NAN)).is_err());
    }
}
