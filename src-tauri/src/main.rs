// src-tauri/src/main.rs
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod sidecar;

use std::sync::Mutex;
use tauri::Manager;

pub struct AppState {
    pub sidecar_port: Mutex<u16>,
    pub sidecar_ready: Mutex<bool>,
}

fn main() {
    let state = AppState {
        sidecar_port: Mutex::new(47474),
        // In dev mode the backend is launched by concurrently — already ready.
        // In release mode we launch it ourselves and wait for health.
        sidecar_ready: Mutex::new(cfg!(debug_assertions)),
    };

    tauri::Builder::default()
        .manage(state)
        .invoke_handler(tauri::generate_handler![
            commands::generate_image,
            commands::list_models,
            commands::get_model_info,
            commands::get_layer_count,
            commands::list_style_routes,
            commands::list_templates,
            commands::list_presets,
            commands::save_preset,
            commands::load_preset,
            commands::get_backend_status,
            commands::open_output_folder,
            commands::export_image,
            commands::pick_export_path,
        ])
        .setup(|app| {
            // Only launch the sidecar in release builds.
            // In dev, the backend is started by `npm run tauri:dev` via concurrently.
            #[cfg(not(debug_assertions))]
            {
                let handle = app.handle();
                tauri::async_runtime::spawn(async move {
                    match sidecar::launch_backend(handle.clone()).await {
                        Ok(_) => {
                            println!("[turrrbo] backend ready");
                            let s = handle.state::<AppState>();
                            *s.sidecar_ready.lock().unwrap() = true;
                        }
                        Err(e) => eprintln!("[turrrbo] backend failed: {}", e),
                    }
                });
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while building tauri application");
}
