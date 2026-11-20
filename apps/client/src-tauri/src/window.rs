//! Creates the main window at a size that fits the screen (desktop only).
//!
//! The configured size (tauri.conf.json) is a preference: on a small screen or
//! with high Windows display scaling it can be larger than the monitor. The
//! window must not be resized after creation to fix that: on Windows the
//! WebView2 then keeps its old, larger bounds and the page spills past the
//! window on every side. So the window is not created from the config
//! automatically ("create": false); it is built here with a size that already
//! fits the monitor's work area (the screen without the taskbar), in logical
//! pixels, and centred.

use tauri::{AppHandle, WebviewWindowBuilder};

/// Largest share of the work area the window may take.
const MAX_SHARE: f64 = 0.9;
/// Room for the title bar and window borders, which inner_size does not include.
const FRAME_HEIGHT: f64 = 40.0;
const FRAME_WIDTH: f64 = 16.0;

/// Inner size (logical px) for a `wanted` size on a work area of `area` (logical px).
pub fn fitted_size(wanted: (f64, f64), area: (f64, f64)) -> (f64, f64) {
    let max_w = (area.0 * MAX_SHARE - FRAME_WIDTH).max(320.0);
    let max_h = (area.1 * MAX_SHARE - FRAME_HEIGHT).max(400.0);
    (wanted.0.min(max_w).round(), wanted.1.min(max_h).round())
}

/// Work area of the primary monitor in logical pixels, if the platform reports one.
fn work_area(app: &AppHandle) -> Option<(f64, f64)> {
    let monitor = app.primary_monitor().ok().flatten()?;
    let scale = monitor.scale_factor();
    let area = monitor.work_area();
    if scale <= 0.0 || area.size.width == 0 || area.size.height == 0 {
        return None;
    }
    Some((area.size.width as f64 / scale, area.size.height as f64 / scale))
}

pub fn create_main(app: &AppHandle) -> tauri::Result<()> {
    let config = app
        .config()
        .app
        .windows
        .iter()
        .find(|w| w.label == "main")
        .cloned()
        .expect("tauri.conf.json must define the main window");
    let mut builder = WebviewWindowBuilder::from_config(app, &config)?;
    if let Some(area) = work_area(app) {
        let (width, height) = fitted_size((config.width, config.height), area);
        builder = builder.inner_size(width, height);
    }
    builder.center().build()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::fitted_size;

    #[test]
    fn a_window_larger_than_the_screen_is_shrunk() {
        // 1366×768 at 150 % scaling: about 911×480 logical, minus the taskbar.
        assert_eq!(fitted_size((1100.0, 740.0), (911.0, 480.0)), (804.0, 400.0));
    }

    #[test]
    fn a_window_that_fits_keeps_its_size() {
        assert_eq!(fitted_size((1100.0, 740.0), (1920.0, 1040.0)), (1100.0, 740.0));
    }

    #[test]
    fn never_smaller_than_the_minimum() {
        assert_eq!(fitted_size((1100.0, 740.0), (300.0, 300.0)), (320.0, 400.0));
    }
}
