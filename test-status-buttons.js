#!/usr/bin/env node

const { exec } = require('child_process');

console.log('🔍 Testing VibeSafe Status Buttons\n');

console.log('There are status-related buttons in multiple tabs:\n');

console.log('1️⃣ HOME TAB - "Show Status" Button:');
console.log('   Expected behavior:');
console.log('   - Reveals the status section below');
console.log('   - Shows encryption key status');
console.log('   - Shows Touch ID enabled/disabled'); 
console.log('   - Shows total secrets count');
console.log('   - Shows preview of first 3 secrets\n');

console.log('2️⃣ SETTINGS TAB - "Check Status" Button:');
console.log('   Expected behavior:');
console.log('   - Calls the same status function');
console.log('   - Updates the app state');
console.log('   - Should show toast notification with status\n');

console.log('3️⃣ Testing Backend Status Command:');

exec('vibesafe status', (error, stdout, stderr) => {
    if (error) {
        console.log('   ❌ VibeSafe status command failed:', stderr);
    } else {
        console.log('   ✅ VibeSafe status command works:');
        console.log(stdout);
    }
    
    console.log('\n4️⃣ Expected Status Display in App:');
    console.log('   • Encryption Keys: Initialized ✅');
    console.log('   • Touch ID Protection: Enabled ✅');
    console.log('   • Secrets Stored: [current count]');
    console.log('   • Secrets list with Copy/Delete buttons\n');
    
    console.log('5️⃣ JavaScript Functions Involved:');
    console.log('   - showStatus() - Main function');
    console.log('   - refreshStatus() - Calls showStatus()');
    console.log('   - updateStatusDisplay() - Updates UI');
    console.log('   - get_vibesafe_status - Rust command\n');
    
    console.log('📋 Manual Test Steps:');
    console.log('   1. Click "Show Status" on Home tab');
    console.log('      → Status section should appear');
    console.log('   2. Click "Check Status" on Settings tab');
    console.log('      → Should update status & show toast');
    console.log('   3. Add/delete a secret');
    console.log('   4. Click status buttons again');
    console.log('      → Count should update\n');
    
    console.log('⚠️  If status buttons don\'t work:');
    console.log('   - Check browser console for errors');
    console.log('   - Ensure VibeSafe is initialized');
    console.log('   - Check if data-action="show-status" exists');
});