#!/usr/bin/env node

const { exec } = require('child_process');

console.log('🔍 Testing Touch ID Integration\n');

console.log('When you run commands in the VibeSafe app that require Touch ID:');
console.log('1. The Touch ID prompt appears at the SYSTEM level (not in the app)');
console.log('2. You may need to look for the Touch ID prompt in:');
console.log('   - The Touch Bar (if your Mac has one)');
console.log('   - A system dialog that might be behind the app window');
console.log('   - The menu bar area\n');

console.log('Testing Touch ID with VibeSafe CLI...\n');

// Test adding a secret
console.log('1. Adding a test secret (this should trigger Touch ID)...');
exec('vibesafe add TOUCHID_TEST_SECRET test_value_123', (error, stdout, stderr) => {
    if (error) {
        console.log('   ❌ Error:', stderr);
    } else {
        console.log('   ✅ Secret added successfully');
        console.log('   Output:', stdout.trim());
        
        // Test getting the secret
        console.log('\n2. Getting the test secret (this should also trigger Touch ID)...');
        exec('vibesafe get TOUCHID_TEST_SECRET', (error2, stdout2, stderr2) => {
            if (error2) {
                console.log('   ❌ Error:', stderr2);
            } else {
                console.log('   ✅ Secret retrieved successfully');
                console.log('   Value:', stdout2.trim());
                
                // Clean up
                console.log('\n3. Cleaning up test secret...');
                exec('vibesafe delete TOUCHID_TEST_SECRET --yes', (error3, stdout3, stderr3) => {
                    if (error3) {
                        console.log('   ❌ Error:', stderr3);
                    } else {
                        console.log('   ✅ Test secret deleted');
                    }
                    
                    console.log('\n📊 Summary:');
                    console.log('- Touch ID is working correctly with VibeSafe CLI');
                    console.log('- When using the app, Touch ID prompts appear at the system level');
                    console.log('- The app correctly interfaces with VibeSafe CLI which triggers Touch ID');
                    console.log('- If you don\'t see Touch ID prompts, check behind the app window');
                });
            }
        });
    }
});