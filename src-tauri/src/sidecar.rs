// src-tauri/src/sidecar.rs
// Launches the bundled Python backend in release mode using std::process::Command.
// The sidecar binary sits next to the main executable inside the .app bundle.

use std::time::Duration;
use tauri::{AppHandle, Manager};
use crate::AppState;

const HEALTH_URL: &str = "http://127.0.0.1:47474/health";
const MAX_RETRIES: u32 = 60;
const RETRY_MS:   u64  = 500;

pub async fn launch_backend(app: AppHandle) -> Result<(), String> {
    let port = {
        let s = app.state::<AppState>();
        let x = *s.sidecar_port.lock().unwrap(); x
    };

    // Resource dir is inside the .app bundle at Contents/Resources/
    let resource_dir = app
        .path_resolver()
        .resource_dir()
        .ok_or("Could not resolve resource directory")?;

    // Sidecar sits next to the main binary at Contents/MacOS/
    let exe_dir = std::env::current_exe()
        .map_err(|e| format!("Cannot find current exe: {}", e))?;
    let exe_dir = exe_dir.parent()
        .ok_or("Cannot find exe directory")?;

    // Try both the exact triple name and a plain name
    let sidecar_triple = format!("turrrbo-backend-{}", get_target_triple());
    let sidecar_path = exe_dir.join(&sidecar_triple);
    let sidecar_path = if sidecar_path.exists() {
        sidecar_path
    } else {
        exe_dir.join("turrrbo-backend")
    };

    let models_dir  = resource_dir.join("resources").join("models");
    let presets_dir = resource_dir.join("resources").join("presets");

    println!("[sidecar] exe_dir:     {:?}", exe_dir);
    println!("[sidecar] sidecar:     {:?}", sidecar_path);
    println!("[sidecar] models_dir:  {:?}", models_dir);

    std::process::Command::new(&sidecar_path)
        .args([
            "--port",        &port.to_string(),
            "--models-dir",  models_dir.to_str().unwrap_or(""),
            "--presets-dir", presets_dir.to_str().unwrap_or(""),
        ])
        .spawn()
        .map_err(|e| format!("Failed to spawn sidecar {:?}: {}", sidecar_path, e))?;

    println!("[sidecar] spawned, polling health...");

    let client = reqwest::Client::new();
    for i in 0..MAX_RETRIES {
        tokio::time::sleep(Duration::from_millis(RETRY_MS)).await;
        if let Ok(r) = client.get(HEALTH_URL).send().await {
            if r.status().is_success() {
                println!("[sidecar] healthy after {}ms", (i + 1) as u64 * RETRY_MS);
                return Ok(());
            }
        }
    }

    Err(format!("Backend not healthy after {} retries", MAX_RETRIES))
}

fn get_target_triple() -> &'static str {
    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    return "aarch64-apple-darwin";
    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    return "x86_64-apple-darwin";
    #[cfg(target_os = "windows")]
    return "x86_64-pc-windows-msvc";
    #[cfg(target_os = "linux")]
    return "x86_64-unknown-linux-gnu";
}
