use crate::AppState;
use serde::{Deserialize, Serialize};
use std::io::{BufRead, BufReader, Write};
use std::sync::atomic::Ordering;
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

#[derive(Serialize, Deserialize)]
pub struct ServerConfig {
    pub server_url: String,
    #[serde(default)]
    pub web_url: String,
}

#[tauri::command]
pub fn read_server_config() -> Result<ServerConfig, String> {
    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .map_err(|_| "Cannot determine home directory".to_string())?;
    
    let config_path = std::path::PathBuf::from(home).join(".basirah").join("config.json");
    
    if !config_path.exists() {
        return Ok(ServerConfig {
            server_url: String::new(),
            web_url: String::new(),
        });
    }
    
    let content = std::fs::read_to_string(&config_path)
        .map_err(|e| format!("Failed to read config: {e}"))?;
    
    let config: ServerConfig = serde_json::from_str(&content)
        .map_err(|e| format!("Failed to parse config: {e}"))?;
    
    Ok(config)
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

// ── Browser-based auth ─────────────────────────────────────────────────────

#[derive(Serialize, Clone)]
pub struct AuthTokens {
    pub access_token: String,
    pub refresh_token: String,
}

#[tauri::command]
pub fn start_auth_server(state: State<'_, AppState>) -> Result<u16, String> {
    let listener = std::net::TcpListener::bind("127.0.0.1:0")
        .map_err(|e| format!("Failed to start auth server: {e}"))?;
    let port = listener.local_addr().map_err(|e| e.to_string())?.port();

    let tokens = state.auth_tokens.clone();
    let stop = state.auth_stop.clone();

    std::thread::spawn(move || {
        listener.set_nonblocking(true).ok();
        let start = std::time::Instant::now();
        let timeout = std::time::Duration::from_secs(300);

        loop {
            if stop.load(Ordering::Relaxed) {
                break;
            }
            if start.elapsed() > timeout {
                break;
            }
            match listener.accept() {
                Ok((mut stream, _)) => {
                    let mut reader = BufReader::new(&stream);
                    let mut request_line = String::new();
                    let _ = reader.read_line(&mut request_line);

                    // Drain remaining headers
                    let mut header = String::new();
                    while reader.read_line(&mut header).unwrap_or(0) > 0 {
                        if header.trim().is_empty() {
                            break;
                        }
                        header.clear();
                    }

                    let path = request_line
                        .split_whitespace()
                        .nth(1)
                        .unwrap_or("/");

                    if let Some(query) = path.strip_prefix("/callback?") {
                        let params: std::collections::HashMap<String, String> = query
                            .split('&')
                            .filter_map(|pair| {
                                let mut parts = pair.splitn(2, '=');
                                Some((
                                    parts.next()?.to_string(),
                                    parts.next().unwrap_or("").to_string(),
                                ))
                            })
                            .collect();

                        if let (Some(access), Some(refresh)) =
                            (params.get("access_token"), params.get("refresh_token"))
                        {
                            let mut t = tokens.lock().unwrap();
                            *t = Some(AuthTokens {
                                access_token: access.clone(),
                                refresh_token: refresh.clone(),
                            });

                            let body = b"<!DOCTYPE html><html><head><title>Authenticated</title><style>body{font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#0f172a;color:#f8fafc}h1{font-size:1.5rem}p{color:#94a3b8}</style></head><body><div style='text-align:center'><h1>Authenticated!</h1><p>You can close this tab and return to Basirah.</p></div></body></html>";
                            let response = format!(
                                "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
                                body.len()
                            );
                            let _ = stream.write_all(response.as_bytes());
                            let _ = stream.write_all(body);
                            break;
                        }
                    }

                    // Unknown path — return 404
                    let resp = b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n";
                    let _ = stream.write_all(resp);
                }
                Err(ref e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                    std::thread::sleep(std::time::Duration::from_millis(50));
                    continue;
                }
                Err(_) => break,
            }
        }
    });

    Ok(port)
}

#[tauri::command]
pub fn poll_auth_result(state: State<'_, AppState>) -> Result<Option<AuthTokens>, String> {
    let t = state.auth_tokens.lock().map_err(|e| e.to_string())?;
    Ok(t.clone())
}

#[tauri::command]
pub fn stop_auth_server(state: State<'_, AppState>) -> Result<(), String> {
    state
        .auth_stop
        .store(true, Ordering::Relaxed);
    Ok(())
}
