# VibeSafe Programmatic API Documentation

## Overview

VibeSafe provides a programmatic API for integration with scripts, automation tools, and AI assistants. The API allows secure secret management without exposing plaintext values to stdout or logs.

## Quick Start

```python
from vibesafe import create_api_client

# Create a non-interactive API client
vs = create_api_client()

# Store a secret
vs.store_secret("API_KEY", "sk-123abc...", overwrite=True)

# Retrieve a secret
api_key = vs.fetch_secret("API_KEY")

# List all secret names
names = vs.list_secret_names()

# Check if a secret exists
if vs.secret_exists("API_KEY"):
    print("API key is configured")

# Remove a secret
vs.remove_secret("API_KEY")
```

## API Methods

### `create_api_client()`

Creates a VibeSafe instance optimized for programmatic usage with:
- Non-interactive mode (no prompts or messages)
- Silent authentication for passkey operations
- Suitable for automation and tool integration

```python
from vibesafe import create_api_client
vs = create_api_client()
```

### Core Methods

#### `fetch_secret(name: str) -> str`

Retrieve a secret's plaintext value.

**Security Warning:** The returned value is plaintext. Never log or display this value.

```python
secret = vs.fetch_secret("DATABASE_URL")
# Use the secret directly in your code
conn = psycopg2.connect(secret)
```

#### `store_secret(name: str, value: str, overwrite: bool = False)`

Store a new secret or update an existing one.

```python
vs.store_secret("API_TOKEN", "token123", overwrite=True)
```

#### `list_secret_names() -> list`

Get a list of all stored secret names (not values).

```python
secrets = vs.list_secret_names()
for name in secrets:
    print(f"Found secret: {name}")
```

#### `secret_exists(name: str) -> bool`

Check if a secret exists without retrieving it.

```python
if not vs.secret_exists("OPENAI_KEY"):
    print("Please configure your OpenAI API key")
```

#### `remove_secret(name: str)`

Delete a secret permanently.

```python
vs.remove_secret("OLD_API_KEY")
```

#### `get_status_info() -> dict`

Get system status information.

```python
status = vs.get_status_info()
print(f"Initialized: {status['initialized']}")
print(f"Secrets count: {status['secret_count']}")
print(f"Passkey enabled: {status['passkey_enabled']}")
```

## Advanced Usage

### Custom Interactive Mode

You can create a VibeSafe instance with custom settings:

```python
from vibesafe import VibeSafe

# Create with specific passkey type
vs = VibeSafe(passkey_type='keychain', interactive=False)

# Or for FIDO2
vs = VibeSafe(passkey_type='fido2', interactive=False)
```

### Error Handling

All methods raise `VibeSafeError` on failure:

```python
from vibesafe import create_api_client, VibeSafeError

vs = create_api_client()

try:
    secret = vs.fetch_secret("MISSING_KEY")
except VibeSafeError as e:
    print(f"Error: {e}")
    # Handle missing secret
```

### Authentication with Passkey

When passkey protection is enabled, the API handles authentication automatically:

```python
vs = create_api_client()

# This will trigger Touch ID/Face ID silently (no prompts)
try:
    secret = vs.fetch_secret("PROTECTED_SECRET")
except VibeSafeError as e:
    if "timeout" in str(e).lower():
        print("Authentication timed out")
    elif "cancelled" in str(e).lower():
        print("Authentication was cancelled")
```

## Integration Examples

### Environment Variables

```python
import os
from vibesafe import create_api_client

vs = create_api_client()

# Set environment variables from VibeSafe
os.environ['API_KEY'] = vs.fetch_secret('API_KEY')
os.environ['DATABASE_URL'] = vs.fetch_secret('DATABASE_URL')

# Now run your application
import app
app.run()
```

### Docker Secrets

```python
import subprocess
from vibesafe import create_api_client

vs = create_api_client()

# Pass secrets to Docker build
api_key = vs.fetch_secret('API_KEY')
subprocess.run([
    'docker', 'build',
    '--secret', f'id=api_key,src=/dev/stdin',
    '-t', 'myapp', '.'
], input=api_key.encode())
```

### AI Tool Integration

```python
from vibesafe import create_api_client

class SecretManager:
    """Tool for AI assistants to safely retrieve secrets"""

    def __init__(self):
        self.vs = create_api_client()

    def get_api_key(self, service: str) -> str:
        """Get API key for a service (never log the result!)"""
        try:
            return self.vs.fetch_secret(f"{service.upper()}_API_KEY")
        except:
            return None

    def has_credential(self, name: str) -> bool:
        """Check if a credential exists"""
        return self.vs.secret_exists(name)

# Usage in AI tool
tool = SecretManager()
if tool.has_credential("OPENAI_API_KEY"):
    # Use the key internally, never expose to output
    client = OpenAI(api_key=tool.get_api_key("openai"))
```

### Continuous Integration

```python
#!/usr/bin/env python3
# deploy.py - CI/CD deployment script

from vibesafe import create_api_client
import subprocess

vs = create_api_client()

# Get deployment credentials
aws_key = vs.fetch_secret('AWS_ACCESS_KEY')
aws_secret = vs.fetch_secret('AWS_SECRET_KEY')

# Configure AWS CLI
subprocess.run(['aws', 'configure', 'set', 'aws_access_key_id', aws_key])
subprocess.run(['aws', 'configure', 'set', 'aws_secret_access_key', aws_secret])

# Deploy
subprocess.run(['aws', 's3', 'sync', './dist', 's3://my-bucket'])
```

## Best Practices

1. **Never Log Secrets**: Retrieved secrets are plaintext. Never print, log, or display them.

2. **Use create_api_client()**: For programmatic usage, always use `create_api_client()` instead of `VibeSafe()` to ensure non-interactive mode.

3. **Handle Authentication**: When passkey is enabled, handle authentication errors gracefully.

4. **Validate Existence**: Check if secrets exist before trying to retrieve them.

5. **Error Handling**: Always wrap API calls in try-except blocks.

6. **Secure Memory**: After using a secret, consider overwriting the variable:
   ```python
   secret = vs.fetch_secret("KEY")
   use_secret(secret)
   secret = None  # Clear from memory
   ```

## Security Considerations

- The API returns **plaintext secrets** - handle with extreme care
- Never pass secrets as command-line arguments
- Don't store retrieved secrets in files or logs
- Use the secrets immediately and clear from memory
- Consider the security of your Python process and environment

## Troubleshooting

### Authentication Timeout

If you get authentication timeouts with passkey:
- Ensure you're responding to Touch ID/Face ID prompts
- Consider disabling passkey for automated environments
- Use a longer timeout if available

### Module Not Found

Ensure VibeSafe is installed:
```bash
pip install vibesafe
# or for development
pip install -e /path/to/vibesafe
```

### Permission Denied

Check file permissions:
```bash
chmod 700 ~/.vibesafe
chmod 600 ~/.vibesafe/*
```