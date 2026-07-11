use std::collections::HashMap;
use crate::AppState;
use serde::Serialize;
use std::io::{BufRead, BufReader, Write};
use std::sync::atomic::Ordering;
use tauri::{AppHandle, State};

// ── Types ──────────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct AgentStatus {
    pub running: bool,
    pub port: u16,
}

#[derive(Serialize, Clone)]
pub struct AuthTokens {
    pub access_token: String,
    pub refresh_token: String,
}

// ── Helper ─────────────────────────────────────────────────────────────────

fn get_port(state: &State<'_, AppState>) -> Result<u16, String> {
    state.agent_manager.lock().map_err(|e| e.to_string()).map(|m| m.port())
}

// ── Sidecar management ─────────────────────────────────────────────────────

#[tauri::command]
pub fn get_agent_status(state: State<'_, AppState>) -> Result<AgentStatus, String> {
    let mut manager = state.agent_manager.lock().map_err(|e| e.to_string())?;
    Ok(AgentStatus { running: manager.is_running(), port: manager.port() })
}

#[tauri::command]
pub async fn agent_health(state: State<'_, AppState>) -> Result<bool, String> {
    let port = state.agent_manager.lock().map_err(|e| e.to_string())?.port();
    match reqwest::get(format!("http://localhost:{port}/api/health")).await {
        Ok(resp) => Ok(resp.status().is_success()),
        Err(_) => Ok(false),
    }
}

// ── Generic API proxy ──────────────────────────────────────────────────────

#[tauri::command]
pub async fn call_agent_api(
    state: State<'_, AppState>,
    method: String,
    path: String,
    body: Option<serde_json::Value>,
) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())?;
    let url = format!("http://localhost:{port}{path}");
    let req = match method.to_uppercase().as_str() {
        "GET" => client.get(&url),
        "POST" => {
            let mut r = client.post(&url);
            if let Some(b) = body { r = r.json(&b); }
            r
        }
        "PUT" => {
            let mut r = client.put(&url);
            if let Some(b) = body { r = r.json(&b); }
            r
        }
        "DELETE" => client.delete(&url),
        _ => return Err(format!("Unsupported method: {method}")),
    };
    let resp = req.send().await.map_err(|e| format!("API request failed: {e}"))?;
    let status = resp.status();
    if status.is_success() {
        resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
    } else {
        let text = resp.text().await.unwrap_or_default();
        Err(format!("API error ({}): {text}", status.as_u16()))
    }
}

#[tauri::command]
pub fn get_agent_start_error(state: State<'_, AppState>) -> Result<Option<String>, String> {
    let err = state.agent_start_error.lock().map_err(|e| e.to_string())?;
    Ok(err.clone())
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

// ── Proxy: Config ──────────────────────────────────────────────────────────

#[tauri::command]
pub async fn get_config(state: State<'_, AppState>) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/config");
    let resp = client.get(&url).send().await.map_err(|e| e.to_string())?;
    resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn update_config(
    state: State<'_, AppState>,
    config: HashMap<String, String>,
) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/config");
    let resp = client.put(&url).json(&serde_json::json!({"config": config}))
        .send().await.map_err(|e| e.to_string())?;
    resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
}

// ── Proxy: Folders ─────────────────────────────────────────────────────────

#[tauri::command]
pub async fn get_folders(state: State<'_, AppState>) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/folders");
    let resp = client.get(&url).send().await.map_err(|e| e.to_string())?;
    resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn add_folder(
    state: State<'_, AppState>,
    path: String,
) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/folders");
    let resp = client.post(&url).json(&serde_json::json!({"path": path}))
        .send().await.map_err(|e| e.to_string())?;
    resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn remove_folder(
    state: State<'_, AppState>,
    path: String,
) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/folders");
    let resp = client.delete(&url).query(&[("path", &path)])
        .send().await.map_err(|e| e.to_string())?;
    resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
}

// ── Proxy: Files ───────────────────────────────────────────────────────────

#[tauri::command]
pub async fn get_files(
    state: State<'_, AppState>,
    status: Option<String>,
    limit: Option<i64>,
) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let mut url = format!("http://localhost:{port}/api/files?limit={}", limit.unwrap_or(1000));
    if let Some(s) = status {
        url.push_str(&format!("&status={}", s));
    }
    let resp = client.get(&url).send().await.map_err(|e| e.to_string())?;
    resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn get_file(
    state: State<'_, AppState>,
    id: String,
) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/files/{id}");
    let resp = client.get(&url).send().await.map_err(|e| e.to_string())?;
    if resp.status() == reqwest::StatusCode::NOT_FOUND {
        return Ok(serde_json::Value::Null);
    }
    resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
}

// ── Proxy: Scan ────────────────────────────────────────────────────────────

#[tauri::command]
pub async fn scan_file(
    state: State<'_, AppState>,
    file_id: String,
) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/scan");
    let resp = client.post(&url).json(&serde_json::json!({"file_id": file_id}))
        .send().await.map_err(|e| e.to_string())?;
    let status = resp.status();
    if status.is_success() {
        resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
    } else {
        Err(resp.text().await.unwrap_or_default())
    }
}

#[tauri::command]
pub async fn scan_selected(
    state: State<'_, AppState>,
    file_ids: Vec<String>,
) -> Result<serde_json::Value, String> {
    let mut results = Vec::new();
    let mut errors = Vec::new();
    for id in &file_ids {
        match scan_file(state.clone(), id.clone()).await {
            Ok(r) => results.push(r),
            Err(e) => errors.push(format!("{id}: {e}")),
        }
    }
    Ok(serde_json::json!({
        "status": if errors.is_empty() { "completed" } else { "partial" },
        "processed": results.len(),
        "errors": errors,
    }))
}

// ── SaaS Communication (proxy to Python agent) ─────────────────────────────

#[tauri::command]
pub async fn register_agent(
    state: State<'_, AppState>,
    server_url: String,
    access_token: String,
) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/register");
    let resp = client.post(&url)
        .json(&serde_json::json!({"server_url": server_url, "access_token": access_token}))
        .send().await.map_err(|e| e.to_string())?;
    if resp.status().is_success() {
        resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
    } else {
        Err(resp.text().await.unwrap_or_default())
    }
}

#[tauri::command]
pub async fn run_sync(state: State<'_, AppState>) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/sync");
    let resp = client.post(&url).send().await.map_err(|e| e.to_string())?;
    if resp.status().is_success() {
        resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
    } else {
        Err(resp.text().await.unwrap_or_default())
    }
}

// ── Proxy: File Operations ─────────────────────────────────────────────────

#[tauri::command]
pub async fn move_file(
    state: State<'_, AppState>,
    file_id: String,
    dest_path: String,
) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/files/move");
    let resp = client.post(&url)
        .json(&serde_json::json!({"file_id": file_id, "dest_path": dest_path}))
        .send().await.map_err(|e| e.to_string())?;
    resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn rename_file(
    state: State<'_, AppState>,
    file_id: String,
    new_name: String,
) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/files/rename");
    let resp = client.post(&url)
        .json(&serde_json::json!({"file_id": file_id, "new_name": new_name}))
        .send().await.map_err(|e| e.to_string())?;
    resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn delete_file(
    state: State<'_, AppState>,
    file_id: String,
) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/files/delete");
    let resp = client.post(&url)
        .json(&serde_json::json!({"file_id": file_id}))
        .send().await.map_err(|e| e.to_string())?;
    resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn copy_file(
    state: State<'_, AppState>,
    file_id: String,
    dest_path: String,
) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/files/copy");
    let resp = client.post(&url)
        .json(&serde_json::json!({"file_id": file_id, "dest_path": dest_path}))
        .send().await.map_err(|e| e.to_string())?;
    resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn archive_files(
    state: State<'_, AppState>,
    file_ids: Vec<String>,
    dest_path: String,
    format: String,
) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/files/archive");
    let resp = client.post(&url)
        .json(&serde_json::json!({"file_ids": file_ids, "dest_path": dest_path, "format": format}))
        .send().await.map_err(|e| e.to_string())?;
    resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn restore_file(
    state: State<'_, AppState>,
    trash_id: String,
) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/files/restore");
    let resp = client.post(&url)
        .json(&serde_json::json!({"trash_id": trash_id}))
        .send().await.map_err(|e| e.to_string())?;
    resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn get_trash(
    state: State<'_, AppState>,
) -> Result<serde_json::Value, String> {
    let port = get_port(&state)?;
    let client = reqwest::Client::new();
    let url = format!("http://localhost:{port}/api/trash");
    let resp = client.get(&url).send().await.map_err(|e| e.to_string())?;
    resp.json::<serde_json::Value>().await.map_err(|e| e.to_string())
}

// ── Browser-based auth ─────────────────────────────────────────────────────

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
            if stop.load(Ordering::Relaxed) { break; }
            if start.elapsed() > timeout { break; }
            match listener.accept() {
                Ok((mut stream, _)) => {
                    let mut reader = BufReader::new(&stream);
                    let mut request_line = String::new();
                    let _ = reader.read_line(&mut request_line);
                    let mut header = String::new();
                    while reader.read_line(&mut header).unwrap_or(0) > 0 {
                        if header.trim().is_empty() { break; }
                        header.clear();
                    }
                    let path = request_line.split_whitespace().nth(1).unwrap_or("/");
                    if let Some(query) = path.strip_prefix("/callback?") {
                        let params: std::collections::HashMap<String, String> = query
                            .split('&')
                            .filter_map(|pair| {
                                let mut parts = pair.splitn(2, '=');
                                Some((parts.next()?.to_string(), parts.next().unwrap_or("").to_string()))
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
    state.auth_stop.store(true, Ordering::Relaxed);
    Ok(())
}
