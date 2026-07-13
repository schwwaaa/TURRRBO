// src-tauri/src/commands.rs
use serde::{Deserialize, Serialize};
use tauri::State;
use crate::AppState;

const API_BASE: &str = "http://127.0.0.1:47474";

fn client() -> reqwest::Client { reqwest::Client::new() }
fn api(path: &str) -> String { format!("{}{}", API_BASE, path) }

// ── Types ─────────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct StyleGANParams {
    pub seed: u64,
    pub truncation_psi: f32,
    pub noise_mode: String,
    pub mix_seed: Option<u64>,
    pub mix_layers: Option<Vec<u32>>,
    pub layer_weights: Option<Vec<f32>>,
    pub noise_strength: f32,
    pub coarse_psi: Option<f32>,
    pub fine_psi: Option<f32>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GenerateRequest {
    pub model_id: String,
    pub params: StyleGANParams,
    pub style_route: Option<String>,
    pub text_prompt: Option<String>,
    pub clip_steps: u32,
    pub clip_lr: f32,
    pub output_dir: Option<String>,
    pub session_note: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GenerateResponse {
    pub ok: bool,
    pub output_image: Option<String>,
    pub preview_image: Option<String>,
    pub model_id: String,
    pub run_id: String,
    pub timing_ms: u64,
    pub warnings: Vec<String>,
    pub error: Option<String>,
    pub effective_params: Option<serde_json::Value>,
    pub clip_guided: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ModelInfo {
    pub id: String,
    pub name: String,
    pub description: String,
    pub resolution: u32,
    pub category: String,
    pub provenance: String,
    pub checkpoint_file: String,
    pub recommended_psi: f32,
    pub tags: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BackendStatus {
    pub healthy: bool,
    pub gpu_available: bool,
    pub device: String,
    pub loaded_model: Option<String>,
    pub version: String,
    pub clip_available: bool,
}

// ── Commands ──────────────────────────────────────────────────────────────────

#[tauri::command]
pub async fn generate_image(
    state: State<'_, AppState>,
    request: GenerateRequest,
) -> Result<GenerateResponse, String> {
    if !*state.sidecar_ready.lock().unwrap() {
        return Ok(GenerateResponse {
            ok: false, output_image: None, preview_image: None,
            model_id: request.model_id, run_id: String::new(),
            timing_ms: 0, warnings: vec![],
            error: Some("Backend not ready".into()),
            effective_params: None, clip_guided: false,
        });
    }
    let resp = client().post(api("/generate")).json(&request).send().await
        .map_err(|e| format!("Request failed: {}", e))?;
    resp.json::<GenerateResponse>().await
        .map_err(|e| format!("Parse error: {}", e))
}

#[tauri::command]
pub async fn list_models(_state: State<'_, AppState>) -> Result<Vec<ModelInfo>, String> {
    let resp = client().get(api("/models")).send().await
        .map_err(|e| format!("Request failed: {}", e))?;
    resp.json::<Vec<ModelInfo>>().await.map_err(|e| format!("Parse error: {}", e))
}

#[tauri::command]
pub async fn get_model_info(model_id: String) -> Result<ModelInfo, String> {
    let resp = client().get(api(&format!("/models/{}", model_id))).send().await
        .map_err(|e| format!("Request failed: {}", e))?;
    resp.json::<ModelInfo>().await.map_err(|e| format!("Parse error: {}", e))
}

#[tauri::command]
pub async fn get_layer_count(model_id: String) -> Result<u32, String> {
    let resp = client().get(api(&format!("/models/{}/layer-count", model_id))).send().await
        .map_err(|e| format!("Request failed: {}", e))?;
    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Parse error: {}", e))?;
    Ok(data["layer_count"].as_u64().unwrap_or(18) as u32)
}

#[tauri::command]
pub async fn list_style_routes() -> Result<serde_json::Value, String> {
    let resp = client().get(api("/style-routes")).send().await
        .map_err(|e| format!("Request failed: {}", e))?;
    resp.json::<serde_json::Value>().await.map_err(|e| format!("Parse error: {}", e))
}

#[tauri::command]
pub async fn list_templates() -> Result<serde_json::Value, String> {
    let resp = client().get(api("/templates")).send().await
        .map_err(|e| format!("Request failed: {}", e))?;
    resp.json::<serde_json::Value>().await.map_err(|e| format!("Parse error: {}", e))
}

#[tauri::command]
pub async fn list_presets() -> Result<serde_json::Value, String> {
    let resp = client().get(api("/presets")).send().await
        .map_err(|e| format!("Request failed: {}", e))?;
    resp.json::<serde_json::Value>().await.map_err(|e| format!("Parse error: {}", e))
}

#[tauri::command]
pub async fn save_preset(preset: serde_json::Value) -> Result<serde_json::Value, String> {
    let resp = client().post(api("/presets")).json(&preset).send().await
        .map_err(|e| format!("Request failed: {}", e))?;
    resp.json::<serde_json::Value>().await.map_err(|e| format!("Parse error: {}", e))
}

#[tauri::command]
pub async fn get_backend_status() -> Result<BackendStatus, String> {
    let resp = client().get(api("/health")).send().await
        .map_err(|e| format!("Request failed: {}", e))?;
    resp.json::<BackendStatus>().await.map_err(|e| format!("Parse error: {}", e))
}

#[tauri::command]
pub async fn open_output_folder(path: String) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    std::process::Command::new("open").arg(&path).spawn().map_err(|e| e.to_string())?;
    #[cfg(target_os = "windows")]
    std::process::Command::new("explorer").arg(&path).spawn().map_err(|e| e.to_string())?;
    #[cfg(target_os = "linux")]
    std::process::Command::new("xdg-open").arg(&path).spawn().map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub async fn export_image(source_path: String) -> Result<Option<String>, String> {
    use tauri::api::dialog::blocking::FileDialogBuilder;
    let dest = FileDialogBuilder::new()
        .set_title("Export Image")
        .add_filter("PNG Image", &["png"])
        .save_file();
    match dest {
        Some(dest_path) => {
            std::fs::copy(&source_path, &dest_path)
                .map_err(|e| format!("Copy failed: {}", e))?;
            Ok(Some(dest_path.to_string_lossy().into_owned()))
        }
        None => Ok(None),
    }
}

#[tauri::command]
pub async fn pick_export_path(_app: tauri::AppHandle) -> Result<Option<String>, String> {
    Ok(None)
}

#[tauri::command]
pub async fn load_preset(preset_id: String) -> Result<serde_json::Value, String> {
    let resp = client().get(api(&format!("/presets/{}", preset_id))).send().await
        .map_err(|e| format!("Request failed: {}", e))?;
    resp.json::<serde_json::Value>().await.map_err(|e| format!("Parse error: {}", e))
}
