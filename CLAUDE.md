# VibeSafe - Claude Code Integration Instructions

## 🔐 Secure Secrets Management with VibeSafe

**PURPOSE:** This document provides strict instructions for Claude Code on handling sensitive secrets using VibeSafe CLI tool, ensuring zero exposure of plaintext secrets.

### ⚠️ CRITICAL SECURITY RULES

1. **NEVER reveal plaintext secrets** in any form:
   - ❌ Do not print, echo, or log secret values
   - ❌ Do not include secrets in responses or code comments
   - ❌ Do not display secrets even partially or encoded
   - ❌ Do not cache secrets in variables for debugging

2. **ALWAYS use VibeSafe CLI** for secret operations:
   - ✅ Use `vibesafe get <SECRET_NAME>` to retrieve secrets
   - ✅ Pipe or substitute output directly to destination
   - ✅ Handle authentication prompts gracefully

### 📋 Command Reference

```bash
# Core commands
vibesafe init                    # Initialize key pair
vibesafe add <name> [value]      # Add a secret
vibesafe get <name>              # Retrieve a secret (output to stdout)
vibesafe list                    # List secret names
vibesafe delete <name>           # Delete a secret
vibesafe status                  # Show system status

# Passkey commands
vibesafe passkey enable          # Enable Touch ID/Face ID/FIDO2
vibesafe passkey disable         # Disable passkey protection
```

### 🔧 Usage Patterns

#### Environment Variables
```bash
# ✅ CORRECT - Direct substitution
export API_KEY=$(vibesafe get API_KEY)

# ❌ WRONG - Never echo the value
API_KEY=$(vibesafe get API_KEY)
echo $API_KEY  # FORBIDDEN
```

#### Platform CLIs

**Supabase:**
```bash
supabase secrets set OPENAI_KEY=$(vibesafe get OPENAI_KEY)
```

**Fly.io:**
```bash
flyctl secrets set DB_PASSWORD=$(vibesafe get DB_PASSWORD)
```

**Cloudflare Workers:**
```bash
echo "$(vibesafe get CF_API_TOKEN)" | wrangler secret put CF_API_TOKEN
```

**Docker BuildKit:**
```bash
DOCKER_BUILDKIT=1 docker build \
  --secret id=api_key,src=<(vibesafe get API_KEY) \
  -t app .
```

#### File Operations
```bash
# ✅ CORRECT - Direct output to file
vibesafe get SSL_CERT > /tmp/cert.pem

# ❌ WRONG - Never cat or display
cat /tmp/cert.pem  # FORBIDDEN
```

### 🔒 Passkey Authentication

When passkey protection is enabled:

1. **First access triggers authentication:**
   - macOS: Touch ID/Face ID prompt appears
   - FIDO2: User must touch security key

2. **Handle authentication gracefully:**
   ```bash
   # If command fails with exit code 128 or 129
   echo "⏳ Waiting for biometric authentication..."
   # Retry the command
   ```

3. **User messages:**
   - "Please authenticate with Touch ID to access secrets"
   - "Touch your security key when it blinks"
   - "Authentication cancelled - please try again"

### 🚨 Error Handling

#### Missing Secret
```bash
# Check if secret exists
if ! vibesafe get API_KEY 2>/dev/null; then
    echo "❌ Secret 'API_KEY' not found"
    echo "💡 Add it with: vibesafe add API_KEY"
    exit 1
fi
```

#### No Keys Initialized
```bash
if ! vibesafe status | grep -q "Key pair initialized"; then
    echo "❌ VibeSafe not initialized"
    echo "💡 Run: vibesafe init"
    exit 1
fi
```

### 📝 User Communication

#### When you need a secret that's missing:
```
❌ Secret 'DATABASE_URL' not found.
Please add it by running:
  vibesafe add DATABASE_URL

Do not paste the secret here - use the command above.
```

#### When confirming secret usage:
```
✅ Successfully deployed using API_KEY (stored securely)
✅ Environment configured with database credentials
✅ Authentication token applied to request headers
```

#### NEVER say:
```
❌ "Your API key sk-123... was used"
❌ "I set the password to abc123"
❌ "The token value is: ..."
```

### 🛡️ Security Checklist

Before using any secret:
- [ ] Verify VibeSafe is initialized (`vibesafe status`)
- [ ] Check secret exists (`vibesafe list`)
- [ ] Use command substitution or piping
- [ ] Never store in intermediate variables
- [ ] Never print or log values
- [ ] Handle authentication prompts
- [ ] Confirm actions without revealing values

### 🔄 Common Workflows

#### Deploy with Multiple Secrets
```bash
# Deploy to production with all required secrets
for secret in API_KEY DB_URL STRIPE_KEY; do
    if ! vibesafe get $secret >/dev/null 2>&1; then
        echo "Missing secret: $secret"
        exit 1
    fi
done

# All secrets verified, proceed with deployment
flyctl deploy \
  --build-secret api_key=$(vibesafe get API_KEY) \
  --build-secret db_url=$(vibesafe get DB_URL) \
  --build-secret stripe_key=$(vibesafe get STRIPE_KEY)
```

#### Rotate a Secret
```bash
# Update existing secret
vibesafe add --overwrite API_KEY
# Then redeploy services that use it
```

### 🚫 Forbidden Operations

1. **Reading key files directly:**
   ```bash
   # ❌ NEVER DO THIS
   cat ~/.vibesafe/private.pem
   cat ~/.vibesafe/secrets.json
   ```

2. **Debugging with secrets:**
   ```bash
   # ❌ NEVER DO THIS
   SECRET=$(vibesafe get API_KEY)
   echo "Debug: $SECRET"
   ```

3. **Storing in files:**
   ```bash
   # ❌ NEVER DO THIS
   vibesafe get API_KEY > visible_file.txt
   git add visible_file.txt
   ```

### 💡 Remember

- Secrets are encrypted at rest with RSA + AES-GCM
- Private keys can be protected with biometrics
- Every secret access is intentional and auditable
- Users trust you to never expose their secrets
- When in doubt, err on the side of caution

**By following these instructions, Claude Code ensures all sensitive data remains confidential while maintaining full automation capabilities.**