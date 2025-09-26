# VibeSafe Desktop App

A modern desktop GUI for VibeSafe built with Tauri, React, and TypeScript.

## Features

- 🔐 **Secure Secret Management**: Modern GUI for managing encrypted secrets
- 🖥️ **Native Desktop App**: Built with Tauri for optimal performance
- 🎨 **Modern UI**: React with TypeScript and shadcn/ui components
- 🔒 **Touch ID Integration**: Native biometric authentication support
- 🌙 **System Tray**: Quick access from the system tray
- 📋 **Clipboard Integration**: Secure copy-to-clipboard functionality

## Architecture

The desktop app uses Tauri's sidecar feature to bundle and communicate with the VibeSafe CLI:

```
Desktop App (Tauri)
├── Frontend (React/TypeScript)
├── Backend (Rust)
└── Sidecar (VibeSafe CLI)
```

## Development

### Prerequisites

- Node.js 18+
- Rust 1.60+
- VibeSafe CLI installed and accessible

### Setup

```bash
# Install dependencies
npm install

# Start development server
npm run tauri:dev
```

### Building

```bash
# Build for production
npm run tauri:build
```

## Commands Available

The app communicates with the VibeSafe CLI through these commands:

- `vibesafe_status` - Get system status
- `vibesafe_list` - List all secrets
- `vibesafe_add` - Add a new secret
- `vibesafe_delete` - Delete a secret
- `vibesafe_init` - Initialize VibeSafe
- `vibesafe_enable_passkey` - Enable Touch ID/FIDO2
- `copy_secret_to_clipboard` - Copy secret to clipboard

## Security

- All secret values are handled securely through the CLI
- No plaintext secrets are stored in the frontend
- Clipboard access is limited and secure
- File system access is restricted to VibeSafe directories

## UI Components

Built with modern React patterns and shadcn/ui:

- Dashboard with status cards
- Secret management interface
- Search and filtering
- Add/delete dialogs
- System tray integration

## Distribution

The app can be distributed as:

- macOS: `.dmg` installer with Touch ID support
- Windows: `.msi` installer with FIDO2 support
- Linux: `.deb`/`.rpm` packages