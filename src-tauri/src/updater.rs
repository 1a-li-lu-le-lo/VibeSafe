use serde::{Deserialize, Serialize};
use tauri::Manager;
use std::path::PathBuf;
use chrono::{DateTime, Utc};

#[derive(Debug, Serialize, Deserialize)]
pub struct UpdateInfo {
    pub version: String,
    pub pub_date: DateTime<Utc>,
    pub notes: String,
    pub signature: String,
    pub download_url: String,
    pub size: u64,
    pub checksum: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct UpdateSettings {
    pub auto_check: bool,
    pub auto_download: bool,
    pub auto_install: bool,
    pub channel: UpdateChannel,
    pub notifications: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub enum UpdateChannel {
    Stable,
    Beta,
    Security,
}

impl Default for UpdateSettings {
    fn default() -> Self {
        Self {
            auto_check: true,
            auto_download: false,
            auto_install: false,
            channel: UpdateChannel::Stable,
            notifications: true,
        }
    }
}

// Get current app version
#[tauri::command]
pub async fn get_app_version() -> Result<String, String> {
    Ok(env!("CARGO_PKG_VERSION").to_string())
}

// Check for available updates
#[tauri::command]
pub async fn check_for_updates(settings: UpdateSettings) -> Result<Option<UpdateInfo>, String> {
    let current_version = env!("CARGO_PKG_VERSION");
    let platform = get_platform();
    let channel = match settings.channel {
        UpdateChannel::Stable => "stable",
        UpdateChannel::Beta => "beta",
        UpdateChannel::Security => "security",
    };
    
    let url = format!(
        "https://api.vibesafe.app/updates/{}/{}/{}",
        platform, current_version, channel
    );
    
    match reqwest::get(&url).await {
        Ok(response) => {
            if response.status() == 204 {
                // No update available
                return Ok(None);
            }
            
            match response.json::<UpdateInfo>().await {
                Ok(update_info) => {
                    // Verify version is newer
                    if is_newer_version(&current_version, &update_info.version) {
                        Ok(Some(update_info))
                    } else {
                        Ok(None)
                    }
                }
                Err(e) => Err(format!("Failed to parse update info: {}", e)),
            }
        }
        Err(e) => Err(format!("Failed to check for updates: {}", e)),
    }
}

// Download and verify update
#[tauri::command]
pub async fn download_update(update_info: UpdateInfo, app_handle: tauri::AppHandle) -> Result<PathBuf, String> {
    let downloads_dir = app_handle
        .path_resolver()
        .app_data_dir()
        .unwrap()
        .join("updates");
    
    std::fs::create_dir_all(&downloads_dir)
        .map_err(|e| format!("Failed to create downloads directory: {}", e))?;
    
    let file_name = format!("VibeSafe-{}.dmg", update_info.version);
    let file_path = downloads_dir.join(&file_name);
    
    // Download the update
    let response = reqwest::get(&update_info.download_url)
        .await
        .map_err(|e| format!("Failed to download update: {}", e))?;
    
    let content = response
        .bytes()
        .await
        .map_err(|e| format!("Failed to read update content: {}", e))?;
    
    // Verify checksum
    let actual_checksum = calculate_sha256(&content);
    if actual_checksum != update_info.checksum {
        return Err("Update verification failed: checksum mismatch".to_string());
    }
    
    // Verify signature
    if !verify_signature(&content, &update_info.signature) {
        return Err("Update verification failed: invalid signature".to_string());
    }
    
    // Save the verified update
    std::fs::write(&file_path, content)
        .map_err(|e| format!("Failed to save update: {}", e))?;
    
    Ok(file_path)
}

// Install downloaded update
#[tauri::command]
pub async fn install_update(update_path: PathBuf, app_handle: tauri::AppHandle) -> Result<(), String> {
    // Create backup before installing
    backup_current_version(&app_handle)?;
    
    // Mount DMG and copy app
    let mount_output = std::process::Command::new("hdiutil")
        .args(&["attach", update_path.to_str().unwrap()])
        .output()
        .map_err(|e| format!("Failed to mount update: {}", e))?;
    
    if !mount_output.status.success() {
        return Err("Failed to mount update DMG".to_string());
    }
    
    // Extract mount point from output
    let output_str = String::from_utf8_lossy(&mount_output.stdout);
    let mount_point = extract_mount_point(&output_str)?;
    
    // Copy new app to Applications
    let copy_result = std::process::Command::new("cp")
        .args(&["-R", &format!("{}/VibeSafe.app", mount_point), "/Applications/"])
        .output();
    
    // Unmount DMG
    let _ = std::process::Command::new("hdiutil")
        .args(&["detach", &mount_point])
        .output();
    
    match copy_result {
        Ok(output) if output.status.success() => {
            // Schedule restart
            schedule_restart(&app_handle);
            Ok(())
        }
        _ => Err("Failed to install update".to_string()),
    }
}

// Get update settings
#[tauri::command]
pub async fn get_update_settings(app_handle: tauri::AppHandle) -> Result<UpdateSettings, String> {
    let config_path = app_handle
        .path_resolver()
        .app_config_dir()
        .unwrap()
        .join("update_settings.json");
    
    if config_path.exists() {
        let content = std::fs::read_to_string(&config_path)
            .map_err(|e| format!("Failed to read settings: {}", e))?;
        
        serde_json::from_str(&content)
            .map_err(|e| format!("Failed to parse settings: {}", e))
    } else {
        Ok(UpdateSettings::default())
    }
}

// Save update settings
#[tauri::command]
pub async fn save_update_settings(settings: UpdateSettings, app_handle: tauri::AppHandle) -> Result<(), String> {
    let config_dir = app_handle
        .path_resolver()
        .app_config_dir()
        .unwrap();
    
    std::fs::create_dir_all(&config_dir)
        .map_err(|e| format!("Failed to create config directory: {}", e))?;
    
    let config_path = config_dir.join("update_settings.json");
    let content = serde_json::to_string_pretty(&settings)
        .map_err(|e| format!("Failed to serialize settings: {}", e))?;
    
    std::fs::write(&config_path, content)
        .map_err(|e| format!("Failed to save settings: {}", e))?;
    
    Ok(())
}

// Helper functions

fn get_platform() -> &'static str {
    #[cfg(target_os = "macos")]
    {
        #[cfg(target_arch = "aarch64")]
        return "darwin-aarch64";
        #[cfg(target_arch = "x86_64")]
        return "darwin-x86_64";
    }
    
    "unknown"
}

fn is_newer_version(current: &str, new: &str) -> bool {
    let current_parts: Vec<u32> = current
        .split('.')
        .filter_map(|s| s.parse().ok())
        .collect();
    
    let new_parts: Vec<u32> = new
        .split('.')
        .filter_map(|s| s.parse().ok())
        .collect();
    
    for i in 0..3 {
        let current_part = current_parts.get(i).unwrap_or(&0);
        let new_part = new_parts.get(i).unwrap_or(&0);
        
        if new_part > current_part {
            return true;
        } else if new_part < current_part {
            return false;
        }
    }
    
    false
}

fn calculate_sha256(data: &[u8]) -> String {
    use sha2::{Sha256, Digest};
    let mut hasher = Sha256::new();
    hasher.update(data);
    format!("{:x}", hasher.finalize())
}

fn verify_signature(data: &[u8], signature: &str) -> bool {
    // TODO: Implement proper signature verification
    // This would use the embedded public key to verify the signature
    true
}

fn backup_current_version(app_handle: &tauri::AppHandle) -> Result<(), String> {
    let backup_dir = app_handle
        .path_resolver()
        .app_data_dir()
        .unwrap()
        .join("backups")
        .join(env!("CARGO_PKG_VERSION"));
    
    std::fs::create_dir_all(&backup_dir)
        .map_err(|e| format!("Failed to create backup directory: {}", e))?;
    
    // TODO: Implement actual backup logic
    Ok(())
}

fn extract_mount_point(hdiutil_output: &str) -> Result<String, String> {
    // Parse hdiutil output to find mount point
    for line in hdiutil_output.lines() {
        if line.contains("/Volumes/") {
            let parts: Vec<&str> = line.split_whitespace().collect();
            if let Some(mount_point) = parts.last() {
                return Ok(mount_point.to_string());
            }
        }
    }
    
    Err("Failed to find mount point".to_string())
}

fn schedule_restart(app_handle: &tauri::AppHandle) {
    // Emit restart event to frontend
    app_handle
        .emit_all("update:restart-required", ())
        .unwrap();
}