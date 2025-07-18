use std::process::Command;
use std::path::Path;
use serde::{Deserialize, Serialize};
use tauri::Manager;
use log::{info, error, warn};
use secrecy::{Secret, ExposeSecret};
use zeroize::Zeroize;

mod updater;
mod logger;

#[derive(Debug, Serialize, Deserialize)]
struct VibeSafeResult {
    success: bool,
    data: Option<serde_json::Value>,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct VibeSafeStatus {
    initialized: bool,
    touchid_enabled: bool,
    secrets: Vec<String>,
    secrets_count: u32,
}

// Helper function to find the vibesafe executable
fn find_vibesafe_command() -> String {
    // Common installation paths for VibeSafe
    let possible_paths = vec![
        "/usr/local/bin/vibesafe",
        "/usr/bin/vibesafe",
        "/opt/homebrew/bin/vibesafe",
        "/Library/Frameworks/Python.framework/Versions/3.11/bin/vibesafe",
        "/Library/Frameworks/Python.framework/Versions/3.10/bin/vibesafe",
        "/Library/Frameworks/Python.framework/Versions/3.9/bin/vibesafe",
        "/Users/holocep/.local/bin/vibesafe",
        "vibesafe", // Try PATH as fallback
    ];
    
    for path in possible_paths {
        if Path::new(path).exists() || path == "vibesafe" {
            info!("Found vibesafe at configured location");
            return path.to_string();
        }
    }
    
    warn!("VibeSafe not found in common paths, falling back to PATH");
    "vibesafe".to_string()
}

// Initialize VibeSafe
#[tauri::command]
async fn initialize_vibesafe() -> VibeSafeResult {
    info!("Initializing VibeSafe CLI");
    
    // First check if already initialized
    let vibesafe_cmd = find_vibesafe_command();
    match Command::new(&vibesafe_cmd).arg("status").output() {
        Ok(status_output) => {
            let status_str = String::from_utf8_lossy(&status_output.stdout);
            if status_str.contains("Key pair initialized") {
                // Already initialized
                return VibeSafeResult {
                    success: true,
                    data: Some(serde_json::json!({
                        "message": "VibeSafe is already initialized"
                    })),
                    error: None,
                };
            }
        }
        Err(_) => {} // Continue with init if status check fails
    }
    
    // Not initialized, proceed with initialization
    match Command::new(&vibesafe_cmd)
        .arg("init")
        .output()
    {
        Ok(output) => {
            if output.status.success() {
                VibeSafeResult {
                    success: true,
                    data: Some(serde_json::json!({
                        "message": "VibeSafe initialized successfully"
                    })),
                    error: None,
                }
            } else {
                let error_msg = String::from_utf8_lossy(&output.stderr);
                VibeSafeResult {
                    success: false,
                    data: None,
                    error: Some(error_msg.to_string()),
                }
            }
        }
        Err(e) => VibeSafeResult {
            success: false,
            data: None,
            error: Some(format!("Failed to execute vibesafe: {}", e)),
        },
    }
}

// Get VibeSafe status
#[tauri::command]
async fn get_vibesafe_status() -> VibeSafeResult {
    // Get status
    let status_output = Command::new(&find_vibesafe_command())
        .arg("status")
        .output();
    
    // Get secrets list
    let list_output = Command::new(&find_vibesafe_command())
        .arg("list")
        .output();
    
    match (status_output, list_output) {
        (Ok(status), Ok(list)) => {
            let status_str = String::from_utf8_lossy(&status.stdout);
            let list_str = String::from_utf8_lossy(&list.stdout);
            
            // Parse status
            let initialized = status_str.contains("Key pair initialized");
            let touchid_enabled = status_str.contains("Passkey protection: ENABLED");
            
            // Parse secrets list
            let secrets: Vec<String> = list_str
                .lines()
                .filter(|line| line.starts_with("  • "))
                .map(|line| line.trim_start_matches("  • ").to_string())
                .collect();
            
            let secrets_count = secrets.len() as u32;
            
            let status_data = VibeSafeStatus {
                initialized,
                touchid_enabled,
                secrets_count,
                secrets,
            };
            
            VibeSafeResult {
                success: true,
                data: Some(serde_json::to_value(status_data).unwrap()),
                error: None,
            }
        }
        (Err(e), _) | (_, Err(e)) => {
            // Check if it's a "command not found" error
            if e.kind() == std::io::ErrorKind::NotFound {
                VibeSafeResult {
                    success: false,
                    data: None,
                    error: Some("VibeSafe CLI not found. Please install VibeSafe first.".to_string()),
                }
            } else {
                VibeSafeResult {
                    success: false,
                    data: None,
                    error: Some(format!("Failed to get VibeSafe status: {}", e)),
                }
            }
        },
    }
}

// Add secret
#[tauri::command]
async fn add_secret(name: String, value: String) -> VibeSafeResult {
    use std::io::Write;
    use std::process::Stdio;
    
    // Convert value to secure string immediately
    let secret_value = Secret::new(value);
    
    // Validate input
    if name.is_empty() || secret_value.expose_secret().is_empty() {
        return VibeSafeResult {
            success: false,
            data: None,
            error: Some("Secret name and value cannot be empty".to_string()),
        };
    }
    
    if name.len() > 100 {
        return VibeSafeResult {
            success: false,
            data: None,
            error: Some("Secret name too long (max 100 characters)".to_string()),
        };
    }
    
    // Use stdin to pass the secret value securely
    let mut child = match Command::new(&find_vibesafe_command())
        .arg("add")
        .arg(&name)
        .arg("--stdin")  // Tell vibesafe to read from stdin
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn() {
        Ok(child) => child,
        Err(e) => {
            return VibeSafeResult {
                success: false,
                data: None,
                error: Some(format!("Failed to start vibesafe: {}", e)),
            }
        }
    };
    
    // Write the secret value to stdin
    if let Some(mut stdin) = child.stdin.take() {
        if let Err(e) = stdin.write_all(secret_value.expose_secret().as_bytes()) {
            error!("Failed to write to stdin: {}", e);
            return VibeSafeResult {
                success: false,
                data: None,
                error: Some("Failed to pass secret securely".to_string()),
            };
        }
        // Close stdin to signal EOF
        drop(stdin);
    }
    
    // The secret value will be automatically zeroed when it goes out of scope
    
    // Wait for the command to complete
    match child.wait_with_output() {
        Ok(output) => {
            if output.status.success() {
                VibeSafeResult {
                    success: true,
                    data: Some(serde_json::json!({
                        "message": format!("Secret '{}' added successfully", name)
                    })),
                    error: None,
                }
            } else {
                let error_msg = String::from_utf8_lossy(&output.stderr);
                VibeSafeResult {
                    success: false,
                    data: None,
                    error: Some(error_msg.to_string()),
                }
            }
        }
        Err(e) => VibeSafeResult {
            success: false,
            data: None,
            error: Some(format!("Failed to add secret: {}", e)),
        },
    }
}

// Get secret
#[tauri::command]
async fn get_secret(name: String) -> VibeSafeResult {
    // Validate input
    if name.is_empty() {
        return VibeSafeResult {
            success: false,
            data: None,
            error: Some("Secret name cannot be empty".to_string()),
        };
    }
    
    match Command::new(&find_vibesafe_command())
        .arg("get")
        .arg(&name)
        .output()
    {
        Ok(output) => {
            if output.status.success() {
                // Convert to secure string immediately
                let mut secret_bytes = output.stdout;
                let secret_str = String::from_utf8_lossy(&secret_bytes).trim().to_string();
                
                // Zero out the original bytes
                secret_bytes.zeroize();
                
                VibeSafeResult {
                    success: true,
                    data: Some(serde_json::json!(secret_str)),
                    error: None,
                }
            } else {
                let error_msg = String::from_utf8_lossy(&output.stderr);
                VibeSafeResult {
                    success: false,
                    data: None,
                    error: Some(error_msg.to_string()),
                }
            }
        }
        Err(e) => VibeSafeResult {
            success: false,
            data: None,
            error: Some(format!("Failed to get secret: {}", e)),
        },
    }
}

// Delete secret
#[tauri::command]
async fn delete_secret(name: String) -> VibeSafeResult {
    // Validate input
    if name.is_empty() {
        return VibeSafeResult {
            success: false,
            data: None,
            error: Some("Secret name cannot be empty".to_string()),
        };
    }
    
    match Command::new(&find_vibesafe_command())
        .arg("delete")
        .arg(&name)
        .arg("--yes")
        .output()
    {
        Ok(output) => {
            if output.status.success() {
                VibeSafeResult {
                    success: true,
                    data: Some(serde_json::json!({
                        "message": format!("Secret '{}' deleted successfully", name)
                    })),
                    error: None,
                }
            } else {
                let error_msg = String::from_utf8_lossy(&output.stderr);
                VibeSafeResult {
                    success: false,
                    data: None,
                    error: Some(error_msg.to_string()),
                }
            }
        }
        Err(e) => VibeSafeResult {
            success: false,
            data: None,
            error: Some(format!("Failed to delete secret: {}", e)),
        },
    }
}

// Enable Touch ID
#[tauri::command]
async fn enable_touchid() -> VibeSafeResult {
    // First check if Touch ID is already enabled
    match Command::new(&find_vibesafe_command()).arg("status").output() {
        Ok(status_output) => {
            let status_str = String::from_utf8_lossy(&status_output.stdout);
            if status_str.contains("Passkey protection: ENABLED") {
                // Already enabled
                return VibeSafeResult {
                    success: true,
                    data: Some(serde_json::json!({
                        "message": "Touch ID protection is already enabled"
                    })),
                    error: None,
                };
            }
        }
        Err(_) => {} // Continue with enable if status check fails
    }
    
    // Not enabled, proceed with enabling
    match Command::new(&find_vibesafe_command())
        .arg("passkey")
        .arg("enable")
        .output()
    {
        Ok(output) => {
            if output.status.success() {
                VibeSafeResult {
                    success: true,
                    data: Some(serde_json::json!({
                        "message": "Touch ID protection enabled successfully"
                    })),
                    error: None,
                }
            } else {
                let error_msg = String::from_utf8_lossy(&output.stderr);
                // Check if it's the "private key not found" error
                if error_msg.contains("Private key file not found") {
                    VibeSafeResult {
                        success: false,
                        data: None,
                        error: Some("VibeSafe needs to be initialized first. Please click 'Initialize VibeSafe' on the Home tab.".to_string()),
                    }
                } else {
                    VibeSafeResult {
                        success: false,
                        data: None,
                        error: Some(error_msg.to_string()),
                    }
                }
            }
        }
        Err(e) => VibeSafeResult {
            success: false,
            data: None,
            error: Some(format!("Failed to enable Touch ID: {}", e)),
        },
    }
}

fn main() {
    // Initialize sanitizing logger
    logger::init_sanitizing_logger();
    
    info!("Starting VibeSafe application");
    
    tauri::Builder::default()
        .setup(|app| {
            let window = app.get_webview_window("main").unwrap();
            
            // Set window properties
            window.set_title("VibeSafe - Secure Secrets Manager").unwrap();
            
            info!("VibeSafe application window initialized");
            
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            initialize_vibesafe,
            get_vibesafe_status,
            add_secret,
            get_secret,
            delete_secret,
            enable_touchid,
            updater::get_app_version,
            updater::check_for_updates,
            updater::download_update,
            updater::install_update,
            updater::get_update_settings,
            updater::save_update_settings
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}