# VibeSafe Security Guide

## 🔒 Security Architecture

VibeSafe implements defense-in-depth with multiple layers of security to protect your secrets.

### Encryption Scheme
- **Hybrid Encryption**: RSA-2048 + AES-256-GCM
- **Key Derivation**: Each secret gets a unique AES key
- **Authentication**: GCM mode provides authenticated encryption
- **Random Generation**: Cryptographically secure via `os.urandom()`

### Storage Security
- **Local-First**: All secrets stored locally in `~/.vibesafe/`
- **File Permissions**: 700 for directory, 600 for sensitive files
- **Atomic Writes**: Prevents corruption via temp file + rename
- **No Cloud Sync**: Never uploads secrets to remote servers

### Authentication Options
1. **Touch ID/Face ID** (macOS): Hardware-backed biometric authentication
2. **FIDO2/WebAuthn**: Cross-platform hardware security keys
3. **Passphrase Protection**: Optional password encryption for private key
4. **File-Based**: Default with OS file permissions

## 🛡️ Security Best Practices

### 1. Enable Strong Authentication

#### Touch ID/Face ID (Recommended for macOS)
```bash
vibesafe passkey enable
# Choose option 1 for Keychain-based Touch ID
```

#### Passphrase Protection (Cross-Platform)
```bash
vibesafe init --passphrase
# Enter a strong passphrase (min 8 characters)
```

#### Hardware Security Keys (FIDO2)
```bash
pip install vibesafe[fido2]
vibesafe passkey enable
# Choose option 2 for FIDO2/WebAuthn
```

### 2. Secure Secret Management

#### Never Expose Secrets
- ❌ Don't display secrets on screen
- ❌ Don't store in shell history
- ❌ Don't commit to version control
- ❌ Don't log secret values

#### Safe Usage Patterns
```bash
# ✅ GOOD: Direct substitution
export API_KEY=$(vibesafe get API_KEY)

# ✅ GOOD: Pipe to command
vibesafe get DB_PASSWORD | docker secret create db_pass -

# ❌ BAD: Display on screen
vibesafe get API_KEY
echo $API_KEY

# ❌ BAD: Save to file
vibesafe get API_KEY > key.txt
```

### 3. Secret Naming Guidelines

VibeSafe enforces secure secret names:
- ✅ Alphanumeric, underscore, hyphen only
- ✅ Maximum 100 characters
- ✅ Examples: `API_KEY`, `DB-PASSWORD-2024`, `jwt_secret_v2`
- ❌ No spaces or special characters
- ❌ No shell metacharacters

### 4. File Permission Security

VibeSafe automatically sets secure permissions, but verify:

```bash
# Check current permissions
vibesafe status

# Fix insecure permissions
chmod 700 ~/.vibesafe
chmod 600 ~/.vibesafe/*
```

Warning signs in `vibesafe status`:
- Directory permissions other than `drwx------` (700)
- File permissions other than `-rw-------` (600)

### 5. Regular Security Maintenance

#### Rotate Secrets Periodically
```bash
# Update individual secrets
vibesafe add API_KEY --overwrite

# Rotate encryption keys (re-encrypts all secrets)
vibesafe rotate --yes
```

#### Backup Securely
```bash
# Export with private key (DANGEROUS - secure this backup!)
vibesafe export --include-private-key --output backup.tar

# Export without private key (safer)
vibesafe export --output secrets_backup.tar
```

#### Audit Access
- Monitor `~/.vibesafe/` directory access
- Check system logs for authentication attempts
- Review secret access patterns

## 🚨 Security Features

### Terminal Output Protection
VibeSafe warns before displaying secrets in terminal:
```bash
$ vibesafe get API_KEY
⚠️  Warning: This will display your secret on screen!
Continue? [y/N]: n
Error: Secret retrieval cancelled for security
```

To bypass (use with caution):
```bash
vibesafe get API_KEY | command  # Pipe directly to command
yes | vibesafe get API_KEY       # Auto-confirm (DANGEROUS)
```

### Memory Protection
- Secrets cleared from memory after use
- No long-lived plaintext storage
- Garbage collection of sensitive data

### Secure Deletion
- Private key overwritten with random data before deletion
- Secure wipe during passkey migration
- Clean removal of secrets

## 🔐 Threat Model & Mitigations

### Protected Against

| Threat | Mitigation |
|--------|------------|
| **Stolen secrets file** | Encrypted with RSA + AES-GCM |
| **Shoulder surfing** | TTY detection, warning prompts |
| **Shell history exposure** | Hidden input via `getpass()` |
| **Memory dumps** | Immediate clearing of plaintext |
| **File corruption** | Atomic writes with temp files |
| **Weak permissions** | Automatic 600/700 enforcement |
| **Command injection** | Input validation, no shell execution |
| **Brute force** | Hardware-backed keys, strong crypto |

### Not Protected Against

| Threat | Recommendation |
|--------|----------------|
| **Compromised system** | Use hardware security keys |
| **Keyloggers** | Enable Touch ID/FIDO2 |
| **Root access** | Full disk encryption |
| **Physical access** | Screen lock, secure workspace |
| **Social engineering** | Security awareness training |

## 🔑 Key Management

### Key Hierarchy
```
RSA Private Key (2048-bit)
    ├── Protects: AES Keys
    └── Storage Options:
        ├── macOS Keychain (Touch ID)
        ├── FIDO2 Device (Hardware key)
        ├── Passphrase-encrypted file
        └── File with OS permissions

AES Keys (256-bit)
    ├── Unique per secret
    ├── Generated randomly
    └── Encrypted with RSA public key

Secrets (Variable length)
    ├── Encrypted with AES-GCM
    └── Authenticated encryption
```

### Key Rotation
```bash
# Rotate all keys and re-encrypt secrets
vibesafe rotate

# Backup old keys automatically created in:
# ~/.vibesafe/key_backup/YYYYMMDD_HHMMSS/
```

## 🤖 AI Integration Security

### Claude Code Integration
VibeSafe includes strict rules for AI assistants:

1. **Never reveal plaintext secrets**
2. **No copying to clipboard**
3. **No writing to files**
4. **Only retrieve for direct use**

The `CLAUDE.md` file enforces these rules automatically.

### Programmatic API Security
```python
from vibesafe import create_api_client

# Non-interactive mode (no prompts)
vs = create_api_client()

# Safe usage - never log the value
api_key = vs.fetch_secret("API_KEY")
use_api(api_key)
api_key = None  # Clear from memory
```

## 📊 Security Audit Checklist

Regular security checks:

- [ ] File permissions: `vibesafe status`
- [ ] Authentication enabled: Touch ID/FIDO2/Passphrase
- [ ] No plaintext secrets in: shell history, logs, temp files
- [ ] Regular key rotation (quarterly)
- [ ] Secure backups stored encrypted
- [ ] Dependencies updated: `pip install --upgrade vibesafe`
- [ ] No sensitive data in version control
- [ ] Claude integration configured properly

## 🆘 Security Incident Response

If you suspect compromise:

1. **Immediate Actions**
   ```bash
   # Rotate all keys
   vibesafe rotate --yes

   # Change all secrets
   vibesafe add SECRET_NAME --overwrite
   ```

2. **Investigation**
   - Check file access times: `ls -la ~/.vibesafe/`
   - Review system authentication logs
   - Verify file permissions haven't changed

3. **Recovery**
   - Regenerate all API keys/passwords at source
   - Update secrets in VibeSafe
   - Enable stronger authentication (Touch ID/FIDO2)
   - Consider fresh installation

## 📚 Additional Resources

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [NIST Cryptographic Standards](https://csrc.nist.gov/publications/detail/sp/800-175b/rev-1/final)
- [Apple Secure Enclave Documentation](https://support.apple.com/guide/security/secure-enclave-sec59b0b31ff/web)
- [FIDO2/WebAuthn Specification](https://fidoalliance.org/specifications/)

## 🐛 Reporting Security Issues

Found a security vulnerability? Please report it responsibly:

1. **DO NOT** create a public GitHub issue
2. Email: security@vibesafe.io (if available)
3. Or use GitHub's private vulnerability reporting
4. Include: description, steps to reproduce, potential impact

We appreciate responsible disclosure and will acknowledge your contribution.

---

*Remember: Security is a journey, not a destination. Stay vigilant and keep your secrets safe!*