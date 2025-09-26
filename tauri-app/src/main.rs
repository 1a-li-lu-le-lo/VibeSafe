#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tauri::{
    command, generate_context, generate_handler, Builder, CustomMenuItem, Manager, SystemTray,
    SystemTrayEvent, SystemTrayMenu, SystemTrayMenuItem, Window, WindowBuilder, WindowUrl,
};
use tauri::api::shell::Command as ShellCommand;

#[derive(Debug, Serialize, Deserialize)]
struct SecretInfo {
    name: String,
    created_at: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct VibeSafeStatus {
    initialized: bool,
    key_exists: bool,
    passkey_enabled: bool,
    secrets_count: u32,
    claude_integration: bool,
}

#[command]
async fn vibesafe_status() -> Result<VibeSafeStatus, String> {
    let output = ShellCommand::new_sidecar("vibesafe")
        .map_err(|e| format!("Failed to create vibesafe command: {}", e))?
        .args(["status", "--json"])
        .output()
        .await
        .map_err(|e| format!("Failed to execute vibesafe status: {}", e))?;

    if output.status.success() {
        let status_str = String::from_utf8_lossy(&output.stdout);
        serde_json::from_str(&status_str)
            .map_err(|e| format!("Failed to parse status JSON: {}", e))
    } else {
        let error = String::from_utf8_lossy(&output.stderr);
        Err(format!("VibeSafe error: {}", error))
    }
}

#[command]
async fn vibesafe_list() -> Result<Vec<SecretInfo>, String> {
    let output = ShellCommand::new_sidecar("vibesafe")
        .map_err(|e| format!("Failed to create vibesafe command: {}", e))?
        .args(["list", "--json"])
        .output()
        .await
        .map_err(|e| format!("Failed to execute vibesafe list: {}", e))?;

    if output.status.success() {
        let list_str = String::from_utf8_lossy(&output.stdout);
        serde_json::from_str(&list_str)
            .map_err(|e| format!("Failed to parse list JSON: {}", e))
    } else {
        let error = String::from_utf8_lossy(&output.stderr);
        Err(format!("VibeSafe error: {}", error))
    }
}

#[command]
async fn vibesafe_add(name: String, value: String) -> Result<String, String> {
    let output = ShellCommand::new_sidecar("vibesafe")
        .map_err(|e| format!("Failed to create vibesafe command: {}", e))?
        .args(["add", &name, &value])
        .output()
        .await
        .map_err(|e| format!("Failed to execute vibesafe add: {}", e))?;

    if output.status.success() {
        Ok("Secret added successfully".to_string())
    } else {
        let error = String::from_utf8_lossy(&output.stderr);
        Err(format!("VibeSafe error: {}", error))
    }
}

#[command]
async fn vibesafe_delete(name: String) -> Result<String, String> {
    let output = ShellCommand::new_sidecar("vibesafe")
        .map_err(|e| format!("Failed to create vibesafe command: {}", e))?
        .args(["delete", &name, "--yes"])
        .output()
        .await
        .map_err(|e| format!("Failed to execute vibesafe delete: {}", e))?;

    if output.status.success() {
        Ok("Secret deleted successfully".to_string())
    } else {
        let error = String::from_utf8_lossy(&output.stderr);
        Err(format!("VibeSafe error: {}", error))
    }
}

#[command]
async fn vibesafe_init() -> Result<String, String> {
    let output = ShellCommand::new_sidecar("vibesafe")
        .map_err(|e| format!("Failed to create vibesafe command: {}", e))?
        .args(["init"])
        .output()
        .await
        .map_err(|e| format!("Failed to execute vibesafe init: {}", e))?;

    if output.status.success() {
        Ok("VibeSafe initialized successfully".to_string())
    } else {
        let error = String::from_utf8_lossy(&output.stderr);
        Err(format!("VibeSafe error: {}", error))
    }
}

#[command]
async fn vibesafe_enable_passkey(passkey_type: String) -> Result<String, String> {
    let output = ShellCommand::new_sidecar("vibesafe")
        .map_err(|e| format!("Failed to create vibesafe command: {}", e))?
        .args(["passkey", "enable", "--type", &passkey_type])
        .output()
        .await
        .map_err(|e| format!("Failed to execute vibesafe passkey enable: {}", e))?;

    if output.status.success() {
        Ok("Passkey enabled successfully".to_string())
    } else {
        let error = String::from_utf8_lossy(&output.stderr);
        Err(format!("VibeSafe error: {}", error))
    }
}

#[command]
async fn copy_secret_to_clipboard(name: String) -> Result<String, String> {
    let output = ShellCommand::new_sidecar("vibesafe")
        .map_err(|e| format!("Failed to create vibesafe command: {}", e))?
        .args(["get", &name])
        .output()
        .await
        .map_err(|e| format!("Failed to execute vibesafe get: {}", e))?;

    if output.status.success() {
        let secret_value = String::from_utf8_lossy(&output.stdout).trim().to_string();

        // Copy to clipboard using Tauri's clipboard API
        use tauri::api::clipboard::write_text;
        write_text(&secret_value)
            .map_err(|e| format!("Failed to copy to clipboard: {}", e))?;

        // Auto-clear clipboard after 30 seconds for security
        tokio::spawn(async move {
            tokio::time::sleep(std::time::Duration::from_secs(30)).await;
            // Clear clipboard by overwriting with empty string
            let _ = write_text("");
        });

        Ok("Secret copied to clipboard (auto-clear in 30s)".to_string())
    } else {
        let error = String::from_utf8_lossy(&output.stderr);
        Err(format!("VibeSafe error: {}", error))
    }
}

fn create_tray() -> SystemTray {
    let quit = CustomMenuItem::new("quit".to_string(), "Quit");
    let show = CustomMenuItem::new("show".to_string(), "Show Window");
    let add_secret = CustomMenuItem::new("add_secret".to_string(), "Add Secret");

    let tray_menu = SystemTrayMenu::new()
        .add_item(show)
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(add_secret)
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(quit);

    SystemTray::new().with_menu(tray_menu)
}

fn main() {
    let tray = create_tray();

    Builder::default()
        .system_tray(tray)
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::LeftClick {
                position: _,
                size: _,
                ..
            } => {
                let window = app.get_window("main").unwrap();
                window.show().unwrap();
                window.set_focus().unwrap();
            }
            SystemTrayEvent::MenuItemClick { id, .. } => match id.as_str() {
                "quit" => {
                    std::process::exit(0);
                }
                "show" => {
                    let window = app.get_window("main").unwrap();
                    window.show().unwrap();
                    window.set_focus().unwrap();
                }
                "add_secret" => {
                    let window = app.get_window("main").unwrap();
                    window.show().unwrap();
                    window.set_focus().unwrap();
                    // Emit event to frontend to show add secret dialog
                    window.emit("show_add_secret", {}).unwrap();
                }
                _ => {}
            }
            _ => {}
        })
        .invoke_handler(generate_handler![
            vibesafe_status,
            vibesafe_list,
            vibesafe_add,
            vibesafe_delete,
            vibesafe_init,
            vibesafe_enable_passkey,
            copy_secret_to_clipboard
        ])
        .run(generate_context!())
        .expect("error while running tauri application");
}