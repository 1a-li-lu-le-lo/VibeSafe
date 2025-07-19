# Security Fix: Preventing Secret Exposure in Logs

## Issue
When using VibeSafe with Claude Code, secrets were being exposed in plaintext when Claude logged the response from `vibesafe get SECRET_NAME`.

## Root Cause
The `get_secret` function was returning the secret value directly in the JSON response:
```rust
VibeSafeResult {
    success: true,
    data: Some(serde_json::json!(secret_str)), // ❌ Exposed in logs
    error: None,
}
```

## Solution Implemented

### 1. Backend Changes (src-tauri/src/main.rs)
Now returns both the actual value and a masked version:
```rust
VibeSafeResult {
    success: true,
    data: Some(serde_json::json!({
        "value": secret_str,        // Actual secret
        "masked": "abc...xyz"       // Safe for logging
    })),
    error: None,
}
```

### 2. Frontend Security Wrapper (src/secure-invoke.js)
- Intercepts sensitive commands
- Overrides `toString()` and `toJSON()` to prevent accidental logging
- Sanitizes error messages
- Provides `secureConsole` for safe logging

### 3. Frontend Usage (src/main.js)
```javascript
// Extract value without logging
let secretValue = result.data.value
await navigator.clipboard.writeText(secretValue)
secretValue = null // Clear from memory
```

## Security Features
1. **No Direct Logging**: The actual secret value is never logged
2. **Masked Display**: Only the masked version appears in logs
3. **Memory Clearing**: Secret values are nullified after use
4. **Warning on Serialization**: Attempts to serialize sensitive data trigger warnings
5. **Error Sanitization**: Error messages are cleaned of sensitive data

## Testing
To verify the fix:
1. Use VibeSafe to get a secret
2. Check console/logs - should only show masked values
3. Clipboard still receives the full secret value

## Additional Security Measures
- Stdin-based secret passing (hides from process list)
- Secure string types with memory zeroing
- Clipboard auto-clear after timeout
- Log sanitization for all backend logs

This fix ensures that secrets remain protected even when development tools or logging frameworks attempt to display them.