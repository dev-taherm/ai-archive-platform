mod agent;
mod commands;
mod tray;

use agent::AgentManager;
use commands::AuthTokens;
use std::sync::atomic::AtomicBool;
use std::sync::{Arc, Mutex};
use tauri::Manager;

pub struct AppState {
    pub agent_manager: Mutex<AgentManager>,
    pub auth_tokens: Arc<Mutex<Option<AuthTokens>>>,
    pub auth_stop: Arc<AtomicBool>,
    pub agent_start_error: Arc<Mutex<Option<String>>>,
    pub http_client: reqwest::Client,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            let _ = app.get_webview_window("main").map(|w| w.set_focus());
        }))
        .plugin(tauri_plugin_log::Builder::new().build())
        .manage(AppState {
            agent_manager: Mutex::new(AgentManager::new()),
            auth_tokens: Arc::new(Mutex::new(None)),
            auth_stop: Arc::new(AtomicBool::new(false)),
            agent_start_error: Arc::new(Mutex::new(None)),
            http_client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(30))
                .build()
                .expect("Failed to create HTTP client"),
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_agent_status,
            commands::agent_health,
            commands::call_agent_api,
            commands::get_agent_start_error,
            commands::start_agent,
            commands::stop_agent,
            commands::get_config,
            commands::update_config,
            commands::register_agent,
            commands::fetch_user_profile,
            commands::run_sync,
            commands::start_auth_server,
            commands::poll_auth_result,
            commands::stop_auth_server,
            commands::add_folder,
            commands::remove_folder,
            commands::get_folders,
            commands::get_files,
            commands::get_file,
            commands::scan_file,
            commands::scan_selected,
            commands::move_file,
            commands::rename_file,
            commands::delete_file,
            commands::copy_file,
            commands::archive_files,
            commands::restore_file,
            commands::get_trash,
        ])
        .setup(|app| {
            let handle = app.handle().clone();
            tray::create_tray(&handle)?;

            // Auto-start edge agent sidecar
            let state = handle.state::<AppState>();
            let mut manager = state.agent_manager.lock().map_err(|e| e.to_string())?;
            if let Err(e) = manager.start(&handle) {
                eprintln!("Failed to auto-start edge agent: {e}");
                if let Ok(mut err) = state.agent_start_error.lock() {
                    *err = Some(e);
                }
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
