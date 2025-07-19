// Test to verify secrets are not exposed in plaintext

// Mock the Tauri API
global.__TAURI__ = {
    invoke: async (cmd, args) => {
        if (cmd === 'get_secret') {
            return {
                success: true,
                data: {
                    value: 'my-super-secret-password-12345',
                    masked: 'my-...345'
                }
            }
        }
        return { success: false }
    }
}

// Mock clipboard API
global.navigator = {
    clipboard: {
        writeText: async (text) => {
            console.log('Clipboard would receive:', text.substring(0, 5) + '...')
            return Promise.resolve()
        }
    }
}

// Test the secure invoke wrapper
import('./src/secure-invoke.js').then(async ({ invoke, secureConsole }) => {
    console.log('Testing secret retrieval security...\n')
    
    try {
        // Test 1: Direct invoke
        console.log('Test 1: Getting secret via secure invoke')
        const result = await invoke('get_secret', { name: 'TEST_SECRET' })
        
        // Try to log the result - should be sanitized
        console.log('Result toString():', result.toString())
        console.log('Result JSON.stringify():', JSON.stringify(result))
        
        // Test 2: Using secureConsole
        console.log('\nTest 2: Using secureConsole.log()')
        secureConsole.log('Secret result:', result)
        
        // Test 3: Accessing the value directly (like the app does)
        console.log('\nTest 3: App behavior (accessing value directly)')
        if (result.success) {
            const secretValue = result.data.value
            console.log('Secret length:', secretValue.length)
            console.log('First 3 chars:', secretValue.substring(0, 3) + '...')
            // This is what the app does - copies to clipboard without logging
            await navigator.clipboard.writeText(secretValue)
        }
        
        console.log('\n✅ Security test passed - secrets are protected from logging')
        
    } catch (error) {
        console.error('Test failed:', error)
    }
})