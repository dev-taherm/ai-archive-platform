mod agent;
mod commands;
mod tray;

use agent::AgentManager;
use std::sync::Mutex;
use tauri::Manager;

pub struct AppState {
    pub agent_manager: Mutex<AgentManager>,
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
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_agent_status,
            commands::start_agent,
            commands::stop_agent,
            commands::get_config,
            commands::update_config,
            commands::call_agent_api,
        ])
        .setup(|app| {
            let handle = app.handle().clone();
            tray::create_tray(&handle)?;

            // Auto-start edge agent sidecar
            let state = handle.state::<AppState>();
            let mut manager = state.agent_manager.lock().map_err(|e| e.to_string())?;
            if let Err(e) = manager.start(&handle) {
                eprintln!("Failed to auto-start edge agent: {e}");
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
