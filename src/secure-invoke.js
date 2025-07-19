// Secure wrapper for Tauri invoke to prevent accidental logging of secrets
import { invoke as tauriInvoke } from '@tauri-apps/api/core'

// Commands that might return sensitive data
const SENSITIVE_COMMANDS = ['get_secret', 'add_secret']

// Wrap the invoke function to add security
export async function invoke(cmd, args) {
    const isSensitive = SENSITIVE_COMMANDS.includes(cmd)
    
    // Create a safe version of args for logging
    const safeArgs = isSensitive && args ? {
        ...args,
        value: args.value ? '<REDACTED>' : undefined,
        password: args.password ? '<REDACTED>' : undefined,
        secret: args.secret ? '<REDACTED>' : undefined
    } : args
    
    try {
        // Call the actual Tauri invoke
        const result = await tauriInvoke(cmd, args)
        
        // If this is a sensitive command, wrap the result
        if (isSensitive && result && result.success && result.data) {
            // Override toString to prevent accidental logging
            Object.defineProperty(result, 'toString', {
                value: function() {
                    return JSON.stringify({
                        ...this,
                        data: this.data.masked || '<SENSITIVE_DATA>'
                    })
                },
                enumerable: false
            })
            
            // Add a warning if someone tries to log it
            Object.defineProperty(result, 'toJSON', {
                value: function() {
                    console.warn('Warning: Attempting to serialize sensitive data')
                    return {
                        ...this,
                        data: this.data.masked || '<SENSITIVE_DATA>'
                    }
                },
                enumerable: false
            })
        }
        
        return result
    } catch (error) {
        // Sanitize error messages that might contain sensitive data
        if (isSensitive && error.message) {
            error.message = error.message
                .replace(/value[:\s]*"[^"]+"/gi, 'value: <REDACTED>')
                .replace(/secret[:\s]*"[^"]+"/gi, 'secret: <REDACTED>')
                .replace(/password[:\s]*"[^"]+"/gi, 'password: <REDACTED>')
        }
        throw error
    }
}

// Export a secure console wrapper
export const secureConsole = {
    log: (...args) => {
        const sanitized = args.map(arg => {
            if (typeof arg === 'object' && arg !== null) {
                // Check if this might be a result from a sensitive command
                if (arg.data && (arg.data.value || arg.data.secret)) {
                    return {
                        ...arg,
                        data: arg.data.masked || '<SENSITIVE_DATA>'
                    }
                }
            }
            return arg
        })
        console.log(...sanitized)
    },
    error: console.error,
    warn: console.warn,
    info: console.info
}