# VibeSafe - Secure Secrets Manager

<p align="center">
  <img src="mockups/logo.png" alt="VibeSafe Logo" width="120" height="120">
</p>

<p align="center">
  <strong>🔐 Military-grade encryption meets Touch ID convenience</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#security">Security</a> •
  <a href="#development">Development</a>
</p>

---

## Overview

VibeSafe is a secure secrets manager for macOS that combines military-grade encryption with the convenience of Touch ID. Built with Tauri and Rust, it provides a native macOS experience while ensuring your sensitive data remains protected.

## ✨ Features

- **🛡️ Military-Grade Encryption**: RSA-2048 + AES-256-GCM hybrid encryption
- **👆 Touch ID Protection**: Hardware-backed biometric authentication for accessing secrets
- **🚫 Zero Exposure**: Secrets are never exposed in plaintext
- **🎨 Modern UI**: Clean, intuitive interface following Apple's design guidelines
- **🔄 Claude Integration**: Seamlessly integrate with Claude Code for development workflows
- **⚡ Native Performance**: Built with Rust and Tauri for optimal performance

## 📸 Screenshots

### Home Screen
The main dashboard showing VibeSafe's core features and status information.

![Home Screen](screenshots/01-home-default.png)

### System Status
View detailed information about your VibeSafe installation and stored secrets.

![System Status](screenshots/02-home-status.png)

### Secrets Management
Easily manage all your secrets with Touch ID protection for sensitive operations.

![Secrets Tab](screenshots/03-secrets-tab.png)

### Add Secret Modal
Securely add new secrets with built-in validation and Touch ID authentication.

![Add Secret](screenshots/04-add-secret-modal.png)

### Form Validation
Real-time validation ensures data integrity and security.

![Form Validation](screenshots/05-form-validation.png)

### Settings
Configure Touch ID and other security settings.

![Settings Tab](screenshots/06-settings-tab.png)

### Claude Integration
Connect VibeSafe with Claude Code for seamless development workflows.

![Claude Tab](screenshots/07-claude-tab.png)

### Notifications
Stay informed with toast notifications for all operations.

![Toast Notifications](screenshots/08-toast-notifications.png)

## 🚀 Installation

### Prerequisites

1. **macOS 10.15 or later** with Touch ID support
2. **VibeSafe CLI** - Install the command-line tool first:
   ```bash
   # Install VibeSafe CLI (Python 3.9+ required)
   pip install vibesafe
   
   # Initialize VibeSafe
   vibesafe init
   
   # Enable Touch ID protection
   vibesafe passkey enable
   ```

### Download the App

1. Download the latest release from the [Releases](https://github.com/1a-li-lu-le-lo/VibeSafe/releases) page
2. Open the `.dmg` file and drag VibeSafe to your Applications folder
3. Launch VibeSafe from your Applications folder

### Build from Source

```bash
# Clone the repository
git clone https://github.com/1a-li-lu-le-lo/VibeSafe.git
cd VibeSafe

# Install dependencies
npm install

# Build the app
npm run tauri build

# The app will be in src-tauri/target/release/bundle/macos/VibeSafe.app
```

## 📖 Usage

### Getting Started

1. **Launch VibeSafe** from your Applications folder
2. **Initialize** - Click "Initialize VibeSafe" if this is your first time
3. **Add Secrets** - Navigate to the Secrets tab and click "Add Secret"
4. **Authenticate** - Use Touch ID when prompted to securely store your secret
5. **Access Secrets** - Click "Copy" on any secret to copy it to your clipboard (requires Touch ID)

### Touch ID Security

VibeSafe requires Touch ID authentication for:
- ✅ Adding new secrets
- ✅ Copying secret values
- ✅ Viewing secret values

No authentication required for:
- ❌ Viewing secret names
- ❌ Deleting secrets (confirmation only)
- ❌ Navigation and general UI operations

### Claude Code Integration

To use VibeSafe with Claude Code:

1. Navigate to the Claude tab
2. Click "Setup Claude Integration"
3. In your Claude Code session, use:
   ```bash
   vibesafe get SECRET_NAME
   ```

## 🔒 Security

### Encryption Architecture

- **Hybrid Encryption**: Combines RSA-2048 for key exchange and AES-256-GCM for data encryption
- **Hardware Security**: Touch ID integration via macOS Keychain
- **Zero Knowledge**: The app never stores or transmits unencrypted secrets
- **Secure Storage**: All data is encrypted at rest using platform-specific secure storage

### Security Best Practices

1. **Regular Backups**: Export your encrypted vault regularly
2. **Strong Authentication**: Ensure Touch ID is properly configured
3. **Access Control**: Only grant access to trusted applications
4. **Audit Trail**: Monitor access logs for suspicious activity

## 🛠️ Development

### Tech Stack

- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Backend**: Rust with Tauri
- **CLI**: Python with Click framework
- **Security**: macOS Keychain API, Touch ID

### Project Structure

```
vibesafe-app/
├── src/                    # Frontend source files
│   └── main.js            # Main JavaScript application
├── src-tauri/             # Rust backend
│   ├── src/
│   │   └── main.rs        # Tauri application logic
│   └── Cargo.toml         # Rust dependencies
├── index.html             # Main HTML file
├── package.json           # Node dependencies
└── tauri.conf.json        # Tauri configuration
```

### Development Setup

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Node.js dependencies
npm install

# Run in development mode
npm run tauri dev

# Run tests
npm test

# Build for production
npm run tauri build
```

### Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Tauri](https://tauri.app/) - The secure app framework
- UI inspired by Apple's Human Interface Guidelines
- Encryption powered by industry-standard cryptographic libraries

## 📞 Support

- **Documentation**: [Read the Docs](https://github.com/1a-li-lu-le-lo/VibeSafe/wiki)
- **Issues**: [GitHub Issues](https://github.com/1a-li-lu-le-lo/VibeSafe/issues)
- **Discussions**: [GitHub Discussions](https://github.com/1a-li-lu-le-lo/VibeSafe/discussions)

---

<p align="center">
  Made with ❤️ by the VibeSafe Team
</p>