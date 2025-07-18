# VibeSafe Update Mechanism

## Overview

VibeSafe implements a secure, user-friendly update mechanism that ensures users always have the latest security patches and features while maintaining the integrity of their encrypted secrets.

## Update Architecture

### 1. Version Management

#### Semantic Versioning
```
MAJOR.MINOR.PATCH
1.0.0 -> 1.0.1 (patch: bug fixes)
1.0.0 -> 1.1.0 (minor: new features, backwards compatible)
1.0.0 -> 2.0.0 (major: breaking changes)
```

#### Version Tracking
- App version in `tauri.conf.json`
- CLI version via `vibesafe --version`
- Version compatibility matrix maintained

### 2. Update Channels

#### Stable Channel (Default)
- Production-ready releases
- Thoroughly tested
- Security audited
- Release cycle: Monthly

#### Beta Channel (Opt-in)
- Pre-release versions
- New features testing
- Release cycle: Bi-weekly

#### Security Channel (Automatic)
- Critical security patches
- Immediate deployment
- Minimal changes
- Automatic installation

### 3. Update Detection

#### Automatic Check
```javascript
// Check for updates on startup and every 6 hours
async function checkForUpdates() {
    try {
        const currentVersion = await __TAURI__.invoke('get_app_version');
        const latestVersion = await __TAURI__.invoke('check_latest_version');
        
        if (needsUpdate(currentVersion, latestVersion)) {
            showUpdateNotification(latestVersion);
        }
    } catch (error) {
        console.error('Update check failed:', error);
    }
}

// Run on startup
setTimeout(checkForUpdates, 5000);

// Run periodically
setInterval(checkForUpdates, 6 * 60 * 60 * 1000);
```

#### Manual Check
- Settings > Check for Updates
- Shows current version
- Shows available updates
- Update changelog

### 4. Update Process

#### User Flow
1. **Notification**: Toast notification about available update
2. **Review**: Show changelog and update size
3. **Confirmation**: User approves update
4. **Download**: Background download with progress
5. **Verification**: Checksum and signature verification
6. **Installation**: Install and restart

#### Security Verification
```rust
// Verify update package
fn verify_update(package_path: &Path) -> Result<bool> {
    // 1. Verify checksum
    let expected_hash = fetch_official_checksum()?;
    let actual_hash = calculate_sha256(package_path)?;
    
    if expected_hash != actual_hash {
        return Ok(false);
    }
    
    // 2. Verify signature
    let signature = fetch_signature()?;
    let public_key = include_str!("../update_public_key.pem");
    
    verify_signature(package_path, &signature, public_key)
}
```

### 5. Implementation Details

#### Tauri Updater Configuration
```json
// tauri.conf.json
{
  "updater": {
    "active": true,
    "endpoints": [
      "https://api.vibesafe.app/updates/{{target}}/{{current_version}}"
    ],
    "dialog": true,
    "pubkey": "YOUR_PUBLIC_KEY_HERE"
  }
}
```

#### Update Manifest
```json
{
  "version": "1.1.0",
  "pub_date": "2025-07-18T10:00:00Z",
  "platforms": {
    "darwin-aarch64": {
      "signature": "...",
      "url": "https://github.com/1a-li-lu-le-lo/VibeSafe/releases/download/v1.1.0/VibeSafe-1.1.0-arm64.dmg",
      "size": 15728640,
      "checksum": "93b2fab9a118dbb61bcf2228ba013263e7b614b538758239338791efae21fcd1"
    }
  },
  "notes": "## What's New\n- Improved Touch ID reliability\n- Added secret categories\n- Fixed clipboard auto-clear"
}
```

### 6. Data Migration

#### Backwards Compatibility
```rust
// Handle version migrations
fn migrate_data(from_version: &str, to_version: &str) -> Result<()> {
    match (from_version, to_version) {
        ("1.0.0", "1.1.0") => migrate_1_0_to_1_1(),
        ("1.1.0", "1.2.0") => migrate_1_1_to_1_2(),
        _ => Ok(()) // No migration needed
    }
}

fn migrate_1_0_to_1_1() -> Result<()> {
    // Add new fields with defaults
    // Preserve existing data
    // Update schema version
    Ok(())
}
```

### 7. Rollback Mechanism

#### Automatic Backup
```rust
// Before update
fn backup_before_update() -> Result<PathBuf> {
    let backup_dir = app_data_dir().join("backups").join(current_version());
    
    // Backup vault
    copy_dir(&vault_dir(), &backup_dir.join("vault"))?;
    
    // Backup config
    copy_file(&config_path(), &backup_dir.join("config.json"))?;
    
    Ok(backup_dir)
}
```

#### Manual Rollback
1. Keep previous version in Applications folder
2. Restore from Time Machine
3. Download previous version from GitHub

### 8. Update Server Infrastructure

#### CDN Distribution
- GitHub Releases for binaries
- CloudFlare CDN for manifest
- Fallback mirrors for reliability

#### Update API
```
GET /updates/{platform}/{current_version}
Response: Update manifest or 204 No Content
```

### 9. Security Considerations

#### Code Signing
- All updates must be code signed
- Notarized by Apple for macOS
- Public key embedded in app

#### Secure Channel
- HTTPS only for all update communications
- Certificate pinning for update server
- No automatic execution without verification

### 10. User Settings

#### Update Preferences
```javascript
// User configurable settings
const updateSettings = {
    autoCheck: true,
    autoDownload: false,
    autoInstall: false,
    channel: 'stable', // stable, beta
    notifications: true
};
```

#### Privacy
- No telemetry without consent
- Version check is anonymous
- No tracking of update behavior

## Implementation Checklist

- [ ] Set up update server endpoint
- [ ] Generate signing keys
- [ ] Configure Tauri updater
- [ ] Implement version checking
- [ ] Add update UI components
- [ ] Create rollback mechanism
- [ ] Write migration handlers
- [ ] Set up CDN distribution
- [ ] Document update process
- [ ] Test update workflow

## Testing Updates

### Local Testing
```bash
# Build update package
npm run tauri:build

# Start local update server
python -m http.server 8080

# Test with different versions
TAURI_UPDATE_ENDPOINT=http://localhost:8080 npm run tauri:dev
```

### Staging Environment
1. Deploy to staging server
2. Test with beta users
3. Monitor for issues
4. Rollback if needed

## User Communication

### Update Notifications
- Non-intrusive toast notifications
- Clear changelog with highlights
- Option to skip version
- Remind later functionality

### Release Notes Template
```markdown
## VibeSafe v1.1.0

### ✨ New Features
- Added secret categories for better organization
- Import/Export functionality with encryption
- Keyboard shortcuts for power users

### 🐛 Bug Fixes
- Fixed Touch ID prompt not appearing on M1 Macs
- Resolved clipboard clearing too quickly
- Corrected dark mode contrast issues

### 🔒 Security Updates
- Updated encryption libraries
- Enhanced input validation
- Improved error handling

### 📝 Notes
- Minimum macOS version: 10.15
- VibeSafe CLI 1.2+ required
```

---

*This update mechanism ensures VibeSafe users receive timely updates while maintaining security and reliability.*