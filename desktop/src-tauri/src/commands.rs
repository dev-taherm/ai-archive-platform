use crate::AppState;
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, State};

#[derive(Serialize)]
pub struct AgentStatus {
    pub running: bool,
    pub port: u16,
}

#[derive(Serialize, Deserialize)]
pub struct AgentConfig {
    pub server_url: Option<String>,
    pub api_key: Option<String>,
    pub jwt_token: Option<String>,
    pub agent_name: Option<String>,
    pub agent_id: Option<String>,
    pub folders: Option<Vec<String>>,
    pub ocr_engine: Option<String>,
    pub ocr_lang: Option<String>,
    pub parser_backend: Option<String>,
    pub sync_interval_minutes: Option<u32>,
}

#[tauri::command]
pub fn get_agent_status(state: State<'_, AppState>) -> Result<AgentStatus, String> {
    let mut manager = state.agent_manager.lock().map_err(|e| e.to_string())?;
    Ok(AgentStatus {
        running: manager.is_running(),
        port: manager.port(),
    })
}

#[tauri::command]
pub fn start_agent(state: State<'_, AppState>, app: AppHandle) -> Result<String, String> {
    let mut manager = state.agent_manager.lock().map_err(|e| e.to_string())?;
    manager.start(&app)
}

#[tauri::command]
pub fn stop_agent(state: State<'_, AppState>) -> Result<String, String> {
    let mut manager = state.agent_manager.lock().map_err(|e| e.to_string())?;
    manager.stop()
}

#[tauri::command]
pub async fn get_config(state: State<'_, AppState>) -> Result<AgentConfig, String> {
    let port = state.agent_manager.lock().map_err(|e| e.to_string())?.port();
    let url = format!("http://localhost:{port}/api/config");

    let resp = reqwest::get(&url)
        .await
        .map_err(|e| format!("Failed to connect to agent: {e}"))?;

    resp.json::<AgentConfig>()
        .await
        .map_err(|e| format!("Failed to parse config: {e}"))
}

#[tauri::command]
pub async fn update_config(
    state: State<'_, AppState>,
    config: AgentConfig,
) -> Result<String, String> {
    let port = state.agent_manager.lock().map_err(|e| e.to_string())?.port();
    let url = format!("http://localhost:{port}/api/config");

    let client = reqwest::Client::new();
    let resp = client
        .put(&url)
        .json(&config)
        .send()
        .await
        .map_err(|e| format!("Failed to connect to agent: {e}"))?;

    resp.text()
        .await
        .map_err(|e| format!("Failed to read response: {e}"))
}

#[tauri::command]
pub async fn call_agent_api(
    state: State<'_, AppState>,
    method: String,
    path: String,
    body: Option<serde_json::Value>,
) -> Result<serde_json::Value, String> {
    let port = state.agent_manager.lock().map_err(|e| e.to_string())?.port();
    let url = format!("http://localhost:{port}{path}");

    let client = reqwest::Client::new();
    let mut req = match method.as_str() {
        "GET" => client.get(&url),
        "POST" => client.post(&url),
        "PUT" => client.put(&url),
        "DELETE" => client.delete(&url),
        _ => return Err(format!("Unsupported method: {method}")),
    };

    if let Some(body) = body {
        req = req.json(&body);
    }

    let resp = req
        .send()
        .await
        .map_err(|e| format!("Failed to connect to agent: {e}"))?;

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse response: {e}"))
}
