//! Keeps the main window on screen (desktop only).
//!
//! The configured size (tauri.conf.json) is a preference, not a guarantee: on a
//! small screen or with high Windows display scaling it can be larger than the
//! monitor, and the window then opens partly off screen. Before the window is
//! shown, it is shrunk to at most 92 % of the monitor's work area (the screen
//! without the taskbar) and centred in it.

use tauri::{AppHandle, Manager, PhysicalPosition, PhysicalSize, WebviewWindow};

const MAX_SHARE: f64 = 0.92;

/// Size and position that fit `wanted` into the work area `(x, y, width, height)`.
pub fn fit(wanted: (u32, u32), area: (i32, i32, u32, u32)) -> ((u32, u32), (i32, i32)) {
    let (ax, ay, aw, ah) = area;
    let width = wanted.0.min((aw as f64 * MAX_SHARE) as u32).max(1);
    let height = wanted.1.min((ah as f64 * MAX_SHARE) as u32).max(1);
    let x = ax + ((aw.saturating_sub(width)) / 2) as i32;
    let y = ay + ((ah.saturating_sub(height)) / 2) as i32;
    ((width, height), (x, y))
}

fn place(window: &WebviewWindow) -> tauri::Result<()> {
    let monitor = match window.current_monitor()? {
        Some(m) => Some(m),
        None => window.primary_monitor()?,
    };
    let Some(monitor) = monitor else { return Ok(()) };
    let area = monitor.work_area();
    let outer = window.outer_size()?;
    let ((width, height), (x, y)) = fit(
        (outer.width, outer.height),
        (area.position.x, area.position.y, area.size.width, area.size.height),
    );
    if (width, height) != (outer.width, outer.height) {
        window.set_size(PhysicalSize::new(width, height))?;
    }
    window.set_position(PhysicalPosition::new(x, y))
}

pub fn fit_and_show(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        if let Err(error) = place(&window) {
            eprintln!("could not fit the window to the screen: {error}");
        }
        // Shown even if fitting failed, so the app never stays invisible.
        let _ = window.show();
        let _ = window.set_focus();
    }
}

#[cfg(test)]
mod tests {
    use super::fit;

    #[test]
    fn a_window_larger_than_the_screen_is_shrunk_and_centred() {
        // 1200×800 logical at 150 % scaling on a 1366×768 screen with a 48 px taskbar.
        let ((w, h), (x, y)) = fit((1800, 1200), (0, 0, 1366, 720));
        assert_eq!((w, h), (1256, 662));
        assert_eq!((x, y), (55, 29));
    }

    #[test]
    fn a_window_that_fits_is_only_centred() {
        let ((w, h), (x, y)) = fit((1200, 800), (0, 0, 1920, 1040));
        assert_eq!((w, h), (1200, 800));
        assert_eq!((x, y), (360, 120));
    }

    #[test]
    fn a_second_monitor_offset_is_respected() {
        let (_, (x, y)) = fit((800, 600), (1920, -200, 1080, 1880));
        assert_eq!((x, y), (1920 + 140, -200 + 640));
    }
}
