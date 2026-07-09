use std::process::{Child, Command};

pub struct AgentManager {
    process: Option<Child>,
    port: u16,
}

impl AgentManager {
    pub fn new() -> Self {
        Self {
            process: None,
            port: 8420,
        }
    }

    pub fn is_running(&mut self) -> bool {
        if let Some(ref mut child) = self.process {
            match child.try_wait() {
                Ok(Some(_)) => false,
                Ok(None) => true,
                Err(_) => false,
            }
        } else {
            false
        }
    }

    pub fn start(&mut self) -> Result<String, String> {
        if self.is_running() {
            return Ok("Agent is already running".to_string());
        }

        let python_bin = std::env::var("PYTHON_BIN").unwrap_or_else(|_| "python3".to_string());

        let child = Command::new(python_bin)
            .args(["-m", "edge_agent", "api", "--port", &self.port.to_string()])
            .spawn()
            .map_err(|e| format!("Failed to start agent: {e}"))?;

        self.process = Some(child);
        Ok(format!("Agent started on port {}", self.port))
    }

    pub fn stop(&mut self) -> Result<String, String> {
        if let Some(mut child) = self.process.take() {
            child.kill().map_err(|e| format!("Failed to stop agent: {e}"))?;
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
