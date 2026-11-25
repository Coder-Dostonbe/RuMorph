// The Kotlin code in android/ is added to the app's Gradle project by tauri-build.
fn main() {
    tauri_plugin::Builder::new(&[]).android_path("android").build();
}
