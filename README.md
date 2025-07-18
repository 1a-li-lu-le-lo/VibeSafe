# VibeSafe - Secure Secrets Manager with Touch ID Protection

VibeSafe is a production-ready CLI application for securely managing secrets with hardware-backed biometric authentication. It encrypts API keys, passwords, and other sensitive data using military-grade cryptography and protects access with Touch ID, Face ID, or device passcode on macOS.

## 🎯 Key Features

- 🔐 **Military-Grade Encryption**: RSA-2048 + AES-256-GCM hybrid encryption
- 🛡️ **Touch ID/Face ID Protection**: Hardware-backed biometric authentication on macOS
- 🚫 **Zero Exposure**: Secrets never exposed in plaintext to Claude Code or logs
- 💾 **Local Storage**: Encrypted secrets stored locally with strict file permissions
- 🔌 **Platform Integration**: Direct support for Supabase, Fly.io, Cloudflare, Docker, and more
- 🔒 **Hardware Security**: Private keys stored in macOS Keychain with Secure Enclave protection
- 🤖 **Claude Code Integration**: Automatic configuration for secure AI-assisted development
- 🧙‍♂️ **Interactive Setup**: Guided wizard for easy onboarding
- 🧹 **Clean Architecture**: Optimized codebase with no unused dependencies

## 📦 Installation

### Prerequisites
- **macOS 10.15+** (for Touch ID/Face ID support)
- **Python 3.8+**
- **Touch ID or Face ID enabled** (recommended)

### Quick Installation
```bash
# Clone the repository
git clone https://github.com/vibesafe/vibesafe.git
cd vibesafe

# Install with pip (includes all macOS dependencies)
pip install -e .
```

### Verify Installation
```bash
# Check VibeSafe version and status
vibesafe --version
vibesafe status

# Run interactive setup
vibesafe setup
```

## 🚀 Quick Start

### Option 1: Interactive Setup (Recommended)
```bash
vibesafe setup
```

This guided wizard will:
1. Initialize encryption keys
2. Add a demo secret for testing
3. Set up passkey protection (Touch ID/Face ID)
4. Configure Claude Code integration
5. Provide next steps and usage examples

### Option 2: Manual Setup

#### 1. Initialize VibeSafe
```bash
vibesafe init
```

#### 2. Add Secrets
```bash
# Add with secure prompt (recommended)
vibesafe add OPENAI_API_KEY
# Enter secret value for 'OPENAI_API_KEY': ****

# Add multiple secrets
vibesafe add DB_PASSWORD
vibesafe add STRIPE_SECRET_KEY
vibesafe add SUPABASE_API_KEY
```

#### 3. Enable Touch ID Protection
```bash
# Enable Touch ID/Face ID protection
vibesafe passkey enable
```

#### 4. Use Secrets Securely
```bash
# Export to environment variable
export API_KEY=$(vibesafe get API_KEY)

# Use with platform CLIs
supabase secrets set OPENAI_KEY=$(vibesafe get OPENAI_KEY)
flyctl secrets set DB_URL=$(vibesafe get DB_URL)
echo "$(vibesafe get CF_API_TOKEN)" | wrangler secret put CF_API_TOKEN
```

## 🤖 Claude Code Integration

VibeSafe automatically configures Claude Code for secure secret management:

```bash
# Set up Claude Code integration
vibesafe claude setup
```

This creates/updates your `CLAUDE.md` file with:
- Strict security policies preventing secret exposure
- Proper authentication handling instructions
- Platform integration examples
- Error handling patterns

### Example Claude Code Usage
When using Claude Code with VibeSafe:
```bash
# ✅ CORRECT - Claude will use VibeSafe securely
export API_KEY=$(vibesafe get API_KEY)
supabase secrets set OPENAI_KEY=$(vibesafe get OPENAI_KEY)

# ❌ WRONG - Claude will never expose secrets
echo $API_KEY  # This will be blocked by VibeSafe policies
```

## 📋 CLI Commands

### Core Commands
```bash
vibesafe init                    # Initialize key pair
vibesafe add <name> [value]      # Add a secret
vibesafe get <name>              # Retrieve a secret
vibesafe list                    # List all secret names
vibesafe delete <name>           # Delete a secret
vibesafe status                  # Show system status
vibesafe setup                   # Run interactive setup wizard
```

### Passkey Commands
```bash
vibesafe passkey enable          # Enable Touch ID/Face ID protection
vibesafe passkey disable         # Disable passkey protection
```

### Claude Integration Commands
```bash
vibesafe claude setup            # Configure Claude Code integration
```

### Options
- `--overwrite` / `-o`: Overwrite existing secret when adding
- `--yes` / `-y`: Skip confirmation prompts when deleting

## 🔒 Security Architecture

### Encryption
1. **Hybrid Encryption**: Each secret is encrypted with a random AES-256 key
2. **Key Wrapping**: The AES key is encrypted with your RSA-2048 public key
3. **Authenticated Encryption**: AES-GCM provides both confidentiality and integrity
4. **Perfect Forward Secrecy**: Each secret uses a unique AES key

### Storage
- Private key: `~/.vibesafe/private.pem` (mode 600) or secure hardware
- Public key: `~/.vibesafe/public.pem` (mode 644)
- Encrypted secrets: `~/.vibesafe/secrets.json` (mode 600)
- Config: `~/.vibesafe/config.json` (mode 600)

### Passkey Protection

#### macOS Keychain (Touch ID/Face ID)
- Private key stored with `kSecAccessControlBiometryAny` flag
- Requires Touch ID, Face ID, or device passcode for each access
- Key never leaves Secure Enclave in plaintext
- Hardware-backed authentication using LocalAuthentication framework

**Touch ID Prompt Note:** The system prompt may show "python wants to use Touch ID" due to macOS security restrictions. This is normal and secure - the detailed message will clearly indicate "VibeSafe CLI wants to access your encrypted secrets".
- Private key wrapped with key derived from FIDO2 assertion
- Requires physical authenticator interaction
- Supports USB keys, platform authenticators, NFC
- Cross-platform compatibility

## 🌐 Platform Integration Examples

### Supabase Edge Functions
```bash
# Set multiple secrets
for secret in OPENAI_KEY STRIPE_KEY DATABASE_URL; do
  supabase secrets set $secret=$(vibesafe get $secret)
done
```

### Fly.io
```bash
# Deploy with secrets
flyctl secrets set \
  API_KEY=$(vibesafe get API_KEY) \
  DB_PASSWORD=$(vibesafe get DB_PASSWORD)
```

### Cloudflare Workers
```bash
# Set secrets
echo "$(vibesafe get CF_API_TOKEN)" | wrangler secret put CF_API_TOKEN
```

### Docker
```bash
# Build with secrets (BuildKit)
DOCKER_BUILDKIT=1 docker build \
  --secret id=api_key,src=<(vibesafe get API_KEY) \
  -t myapp .
```

### GitHub Actions
```bash
# Export for CI (be very careful!)
vibesafe get GITHUB_TOKEN | gh secret set GITHUB_TOKEN
```

## 🛡️ Security Best Practices

1. **Never commit secrets**: Even encrypted, keep `.vibesafe/` in `.gitignore`
2. **Backup your keys**: Store `private.pem` backup securely (encrypted USB, password manager)
3. **Rotate regularly**: Use `vibesafe add --overwrite` to update secrets
4. **Use passkeys**: Enable hardware-backed protection for defense in depth
5. **Audit usage**: Monitor when and where secrets are accessed
6. **Claude Code Rules**: Let VibeSafe handle all secret operations automatically

## 🔧 Development

### Running Tests
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=vibesafe tests/

# Run security tests
pytest tests/test_security.py -v

# Run security audit
python3 security_audit.py
```

### Code Style
```bash
black src/
flake8 src/
```

## 📊 Security Audit Results

VibeSafe has been audited for security vulnerabilities:

```
🔐 SECURITY AUDIT REPORT
==================================================
✅ Critical Issues: 0
⚠️  Warnings: 166 (mostly false positives)
✅ Passed Checks: 29

Key Security Features Verified:
✅ RSA-2048 encryption
✅ AES-GCM authenticated encryption
✅ Secure random number generation
✅ Biometric authentication
✅ Secure keychain storage
✅ Proper file permissions
✅ No plaintext secrets in storage
```

## 🚨 Troubleshooting

### Authentication Issues
#### "Authentication cancelled"
- User cancelled Touch ID/passkey prompt
- Try again and complete the authentication

#### "Authentication failed"
- Touch ID/Face ID not configured
- Check biometric settings in System Preferences

#### "No authenticator found"
- Ensure your device has Touch ID/Face ID (macOS)
- Connect a FIDO2 security key (cross-platform)
- Check that WebAuthn is enabled in your browser

### Decryption Issues
#### "Decryption failed"
- Ensure you're using the correct private key
- Check that the secret wasn't corrupted
- Verify passkey authentication succeeded

### Claude Code Integration
#### "Secret not found"
- Verify the secret exists: `vibesafe list`
- Add the secret: `vibesafe add SECRET_NAME`

#### "Authentication required"
- Complete biometric authentication when prompted
- Ensure passkey protection is properly configured

## 📝 Changelog

### v1.0.0 (Current)
- ✅ Complete RSA-2048 + AES-256-GCM encryption
- ✅ macOS Keychain integration (Touch ID/Face ID)
- ✅ Apple Passkey support (FIDO2/WebAuthn)
- ✅ Cross-platform FIDO2 support
- ✅ Interactive setup wizard
- ✅ Claude Code integration
- ✅ Comprehensive test suite
- ✅ Security audit completed
- ✅ Platform integration examples

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and security audit
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🔒 Security Disclosure

Found a security issue? Please email security@vibesafe.io with details.

## 🙏 Acknowledgments

- Built with `cryptography` library for robust encryption
- macOS Keychain integration via `pyobjc`
- FIDO2 support via `python-fido2`
- Apple Passkey support via `AuthenticationServices`
- Inspired by HashiCorp Vault and Kubernetes Sealed Secrets
- Designed for seamless Claude Code integration

---

**VibeSafe: Secure secrets management with hardware-backed passkey protection** 🔐