use tauri::AppHandle;
use tauri_plugin_shell::ShellExt;

pub struct AgentManager {
    child: Option<tauri_plugin_shell::process::CommandChild>,
    running: bool,
    port: u16,
}

impl AgentManager {
    pub fn new() -> Self {
        Self {
            child: None,
            running: false,
            port: 8420,
        }
    }

    pub fn is_running(&mut self) -> bool {
        self.running
    }

    pub fn start(&mut self, app: &AppHandle) -> Result<String, String> {
        if self.running {
            return Ok("Agent is already running".to_string());
        }

        let sidecar = app
            .shell()
            .sidecar("edge-agent")
            .map_err(|e| format!("Failed to resolve sidecar: {e}"))?;

        let (_rx, child) = sidecar
            .args(["api", "--port", &self.port.to_string()])
            .spawn()
            .map_err(|e| format!("Failed to start agent: {e}"))?;

        self.child = Some(child);
        self.running = true;
        Ok(format!("Agent started on port {}", self.port))
    }

    pub fn stop(&mut self) -> Result<String, String> {
        if let Some(child) = self.child.take() {
            child
                .kill()
                .map_err(|e| format!("Failed to stop agent: {e}"))?;
            self.running = false;
            Ok("Agent stopped".to_string())
        } else {
            Ok("Agent is not running".to_string())
        }
    }

    pub fn port(&self) -> u16 {
        self.port
    }
}

impl Default for AgentManager {
    fn default() -> Self {
        Self::new()
    }
}
