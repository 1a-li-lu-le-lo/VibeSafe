"""
Claude Code integration module for VibeSafe
Handles automatic CLAUDE.md updates and integration setup
"""
import os
import shutil
from pathlib import Path
import click

CLAUDE_MD_TEMPLATE = """
# VibeSafe - Secure Secrets Management

**CRITICAL SECURITY POLICY**: This system uses VibeSafe for secure secret management. You MUST follow these rules strictly to prevent secret exposure.

## 🔐 Core Security Rules

1. **NEVER reveal plaintext secrets** in any form:
   - ❌ Do not print, echo, or display secret values
   - ❌ Do not include secrets in responses or code comments
   - ❌ Do not cache secrets in variables for debugging
   - ❌ Do not show secrets in error messages or logs
   - ❌ Do not copy secrets to clipboard or temporary files

2. **ALWAYS use VibeSafe CLI** for secret operations:
   - ✅ Use `vibesafe get <SECRET_NAME>` to retrieve secrets
   - ✅ Pipe output directly to destination commands
   - ✅ Handle authentication prompts gracefully
   - ✅ Use command substitution: `$(vibesafe get SECRET_NAME)`

3. **SECRET HANDLING PROTOCOL**:
   - ✅ Secrets flow directly from VibeSafe to destination
   - ✅ No intermediate storage or display
   - ✅ Authenticate user before secret access
   - ✅ Inform user about authentication without showing secrets

## 📋 VibeSafe Commands

```bash
# Core operations
vibesafe status                  # Check system status
vibesafe add <name> [value]      # Add a secret
vibesafe get <name>              # Retrieve a secret
vibesafe list                    # List secret names
vibesafe delete <name>           # Delete a secret

# Security features
vibesafe passkey enable          # Enable Touch ID/Face ID (macOS)
vibesafe passkey disable         # Disable passkey protection
```

## 🛡️ Safe Usage Patterns

### Environment Variables
```bash
# ✅ CORRECT - Direct substitution
export API_KEY=$(vibesafe get API_KEY)

# ❌ NEVER DO THIS
echo $API_KEY  # FORBIDDEN
```

### Platform Deployments
```bash
# Supabase
supabase secrets set API_KEY=$(vibesafe get API_KEY)

# Fly.io
flyctl secrets set API_KEY=$(vibesafe get API_KEY)

# Vercel
echo "$(vibesafe get API_KEY)" | vercel env add API_KEY production
```

## 🔒 Authentication Handling

When passkey protection is enabled:
- First access triggers Touch ID/Face ID prompt
- Wait patiently for user authentication
- Inform user about authentication requirements
- Handle authentication timeouts gracefully

### Authentication Flow
```bash
# When you encounter authentication prompts:
echo "🔐 VibeSafe requires authentication to access secrets"
echo "👆 Please authenticate with Touch ID/Face ID when prompted"
echo "⏳ Waiting for authentication..."

# Check for common authentication errors:
if vibesafe get API_KEY 2>&1 | grep -q "Authentication cancelled"; then
    echo "❌ Authentication was cancelled"
    echo "💡 Please try again and complete the authentication prompt"
    exit 1
elif vibesafe get API_KEY 2>&1 | grep -q "Authentication failed"; then
    echo "❌ Authentication failed"
    echo "💡 Please check your Touch ID/Face ID settings"
    exit 1
fi
```

### Biometric Authentication Messages
- **Touch ID Required**: "🔐 Touch ID required to access secrets"
- **Face ID Required**: "🔐 Face ID required to access secrets"
- **Authentication Timeout**: "⏰ Authentication timed out. Please try again."
- **Authentication Success**: "✅ Authentication successful. Proceeding with secret access."

## 📤 User Communication

### ✅ Safe confirmations:
- "✅ Successfully deployed using API_KEY (stored securely)"
- "✅ Environment configured with database credentials"

### ❌ NEVER reveal secrets:
- "Your API key sk-123..." (FORBIDDEN)
- "The password is abc123" (FORBIDDEN)
- "Setting API_KEY to: sk-abc123..." (FORBIDDEN)
- "Using token: bearer_xyz..." (FORBIDDEN)
- "Debug: SECRET_VALUE = xyz" (FORBIDDEN)

### 🔐 Claude Code Behavior Rules:
- **NO VISIBILITY**: Claude never sees plaintext secrets
- **NO LOGGING**: Secrets never appear in chat logs or responses
- **NO CACHING**: Secrets are never stored in variables
- **NO DEBUGGING**: Secrets never appear in debug output
- **DIRECT FLOW**: Secrets flow directly from VibeSafe to destination
- **AUTHENTICATION**: User authenticates via Touch ID/Face ID before access

## 🚨 Error Handling

### Missing Secret:
```bash
if ! vibesafe get API_KEY >/dev/null 2>&1; then
    echo "❌ Secret 'API_KEY' not found"
    echo "💡 Add it with: vibesafe add API_KEY"
    exit 1
fi
```

---

**By following these instructions, Claude Code ensures all sensitive data remains confidential while maintaining full automation capabilities.**
"""

def find_claude_md_file(start_dir=None):
    """Find the CLAUDE.md file in the current project"""
    if start_dir is None:
        start_dir = Path.cwd()
    else:
        start_dir = Path(start_dir)
    
    # Search current directory and parents
    for path in [start_dir] + list(start_dir.parents):
        claude_file = path / "CLAUDE.md"
        if claude_file.exists():
            return claude_file
    
    return None

def backup_claude_md(claude_file):
    """Create a backup of the existing CLAUDE.md file"""
    backup_file = claude_file.with_suffix('.md.backup')
    shutil.copy2(claude_file, backup_file)
    return backup_file

def update_claude_md(claude_file=None, project_dir=None):
    """Update or create CLAUDE.md with VibeSafe integration"""
    if claude_file is None:
        claude_file = find_claude_md_file(project_dir)
    
    if claude_file is None:
        # Create new CLAUDE.md in current directory
        claude_file = Path.cwd() / "CLAUDE.md"
        click.echo(f"📝 Creating new CLAUDE.md at {claude_file}")
        
        with open(claude_file, 'w') as f:
            f.write(CLAUDE_MD_TEMPLATE.strip())
        
        click.echo("✅ CLAUDE.md created with VibeSafe integration")
        return claude_file
    
    # Read existing content
    with open(claude_file, 'r') as f:
        content = f.read()
    
    # Check if VibeSafe integration already exists
    if "VibeSafe" in content and "vibesafe get" in content:
        click.echo("ℹ️  VibeSafe integration already exists in CLAUDE.md")
        return claude_file
    
    # Create backup
    backup_file = backup_claude_md(claude_file)
    click.echo(f"📋 Backup created: {backup_file}")
    
    # Add VibeSafe integration
    vibesafe_section = CLAUDE_MD_TEMPLATE.strip()
    
    # Append to existing content
    updated_content = content.rstrip() + "\n\n" + "# " + "="*50 + "\n"
    updated_content += "# VibeSafe Integration (Auto-generated)\n"
    updated_content += "# " + "="*50 + "\n\n"
    updated_content += vibesafe_section
    
    # Write updated content
    with open(claude_file, 'w') as f:
        f.write(updated_content)
    
    click.echo(f"✅ CLAUDE.md updated with VibeSafe integration")
    return claude_file

def setup_claude_integration(project_dir=None):
    """Complete Claude Code integration setup"""
    click.echo("\n🔧 Setting up Claude Code integration...")
    
    # Update CLAUDE.md
    claude_file = update_claude_md(project_dir=project_dir)
    
    # Show success message
    click.echo("\n" + "="*60)
    click.echo("🎉 Claude Code Integration Complete!")
    click.echo("="*60)
    click.echo(f"📝 CLAUDE.md updated: {claude_file}")
    click.echo("\n📋 What's configured:")
    click.echo("  • Secure secret handling rules")
    click.echo("  • VibeSafe command reference")
    click.echo("  • Platform integration examples")
    click.echo("  • Error handling patterns")
    click.echo("\n💡 Claude Code will now:")
    click.echo("  • Use VibeSafe for all secret operations")
    click.echo("  • Never expose secrets in chat")
    click.echo("  • Handle authentication prompts")
    click.echo("  • Follow security best practices")
    
    return claude_file