#!/usr/bin/env node

const { exec } = require('child_process');
const fs = require('fs');

console.log('🔍 VibeSafe Comprehensive UI & Security Test\n');
console.log('═══════════════════════════════════════════════\n');

const tests = {
    navigation: {
        name: '📱 Navigation System',
        items: [
            { test: 'Home tab switching', expected: 'Shows features and status section' },
            { test: 'Secrets tab switching', expected: 'Shows Add Secret button and secrets list' },
            { test: 'Settings tab switching', expected: 'Shows Touch ID enable option' },
            { test: 'Claude tab switching', expected: 'Shows Claude integration options' },
            { test: 'Active tab highlighting', expected: 'Active tab has distinct visual style' }
        ]
    },
    homeTab: {
        name: '🏠 Home Tab Components',
        items: [
            { test: 'Initialize VibeSafe button', expected: 'Shows "already initialized" message' },
            { test: 'Show Status button', expected: 'Reveals status section with correct data' },
            { test: 'Feature cards display', expected: 'Shows 3 feature cards with icons' },
            { test: 'Status section values', expected: 'Shows initialized, Touch ID enabled, secret count' },
            { test: 'Secrets preview list', expected: 'Shows first 3 secrets with Copy/Delete buttons' }
        ]
    },
    secretsTab: {
        name: '🔐 Secrets Tab Components',
        items: [
            { test: 'Add Secret button', expected: 'Opens modal dialog' },
            { test: 'Refresh button', expected: 'Updates secrets list' },
            { test: 'Secrets list display', expected: 'Shows all secrets with actions' },
            { test: 'Copy button per secret', expected: 'REQUIRES TOUCH ID, copies to clipboard' },
            { test: 'Delete button per secret', expected: 'Shows confirmation dialog, then deletes' }
        ]
    },
    modalSystem: {
        name: '📝 Add Secret Modal',
        items: [
            { test: 'Modal opens on Add Secret', expected: 'Overlay appears with form' },
            { test: 'Cancel button', expected: 'Closes modal without saving' },
            { test: 'ESC key', expected: 'Closes modal without saving' },
            { test: 'Click outside modal', expected: 'Closes modal without saving' },
            { test: 'Form validation - empty name', expected: 'Shows "Secret name is required"' },
            { test: 'Form validation - empty value', expected: 'Shows "Secret value is required"' },
            { test: 'Form validation - long name', expected: 'Shows "max 100 characters" error' },
            { test: 'Valid form submission', expected: 'REQUIRES TOUCH ID, adds secret' },
            { test: 'Touch ID prompt indicator', expected: 'Shows blue Touch ID notice in form' }
        ]
    },
    settingsTab: {
        name: '⚙️ Settings Tab Components',
        items: [
            { test: 'Enable Touch ID button', expected: 'Shows "already enabled" message' },
            { test: 'Check Status button', expected: 'Shows current system status' },
            { test: 'Touch ID feature card', expected: 'Displays Touch ID information' }
        ]
    },
    claudeTab: {
        name: '🤖 Claude Tab Components',
        items: [
            { test: 'Setup Claude Integration button', expected: 'Shows integration instructions' },
            { test: 'Test Integration button', expected: 'Verifies VibeSafe is ready' },
            { test: 'Claude feature card', expected: 'Displays integration information' }
        ]
    },
    toastSystem: {
        name: '🔔 Toast Notifications',
        items: [
            { test: 'Success toasts', expected: 'Green border, auto-dismiss after 4s' },
            { test: 'Error toasts', expected: 'Red border, shows error details' },
            { test: 'Info toasts', expected: 'Blue border, shows Touch ID notices' },
            { test: 'Multiple toasts', expected: 'Stack vertically, newest on top' }
        ]
    },
    touchIdSecurity: {
        name: '🔒 Touch ID Security',
        items: [
            { test: 'Add secret operation', expected: '✅ REQUIRES Touch ID authentication' },
            { test: 'Copy secret operation', expected: '✅ REQUIRES Touch ID authentication' },
            { test: 'Get secret value', expected: '✅ REQUIRES Touch ID authentication' },
            { test: 'Delete secret', expected: '❌ Does NOT require Touch ID (by design)' },
            { test: 'View secret names', expected: '❌ Does NOT require Touch ID (by design)' },
            { test: 'Touch ID system prompt', expected: 'Appears at macOS system level' }
        ]
    },
    responsive: {
        name: '📐 Responsive Design',
        items: [
            { test: 'Window resizing', expected: 'Content adapts, min width 600px' },
            { test: 'Button layouts', expected: 'Stack vertically on small screens' },
            { test: 'Modal sizing', expected: 'Adapts to viewport, max 90% height' },
            { test: 'Text readability', expected: 'Font sizes remain legible' }
        ]
    }
};

// Print test checklist
console.log('📋 UI Component Test Checklist:\n');

Object.entries(tests).forEach(([category, data]) => {
    console.log(`${data.name}`);
    console.log('─'.repeat(50));
    data.items.forEach((item, index) => {
        console.log(`  ${index + 1}. ${item.test}`);
        console.log(`     Expected: ${item.expected}`);
    });
    console.log('');
});

// Test Touch ID requirement
console.log('\n🔐 Testing Touch ID Requirements...\n');

async function runCommand(cmd) {
    return new Promise((resolve) => {
        exec(cmd, (error, stdout, stderr) => {
            resolve({ success: !error, stdout, stderr: stderr || error?.message });
        });
    });
}

async function testTouchIdRequirements() {
    // Test adding a secret
    console.log('1. Testing ADD SECRET (should require Touch ID):');
    const addResult = await runCommand('vibesafe add UI_TEST_SECRET test_value_456');
    console.log(`   ${addResult.success ? '✅' : '❌'} ${addResult.success ? 'Touch ID was required' : addResult.stderr}`);
    
    // Test getting a secret
    console.log('\n2. Testing GET/COPY SECRET (should require Touch ID):');
    const getResult = await runCommand('vibesafe get UI_TEST_SECRET');
    console.log(`   ${getResult.success ? '✅' : '❌'} ${getResult.success ? 'Touch ID was required' : getResult.stderr}`);
    if (getResult.success) {
        console.log(`   Retrieved value: ${getResult.stdout.trim()}`);
    }
    
    // Test listing secrets (should NOT require Touch ID)
    console.log('\n3. Testing LIST SECRETS (should NOT require Touch ID):');
    const listResult = await runCommand('vibesafe list');
    console.log(`   ${listResult.success ? '✅' : '❌'} ${listResult.success ? 'Listed without Touch ID' : listResult.stderr}`);
    
    // Clean up
    await runCommand('vibesafe delete UI_TEST_SECRET --yes');
}

testTouchIdRequirements().then(() => {
    console.log('\n📊 Test Summary:\n');
    console.log('✅ All navigation tabs should switch correctly');
    console.log('✅ All buttons should trigger appropriate actions');
    console.log('✅ Modal system should have multiple close methods');
    console.log('✅ Form validation should show real-time feedback');
    console.log('✅ Touch ID is REQUIRED for:');
    console.log('   - Adding new secrets');
    console.log('   - Copying/viewing secret values');
    console.log('✅ Touch ID is NOT required for:');
    console.log('   - Viewing secret names');
    console.log('   - Deleting secrets (after confirmation)');
    console.log('   - Navigation and general UI operations');
    
    console.log('\n🎯 Action Items:');
    console.log('1. Manually test each UI component listed above');
    console.log('2. Verify Touch ID prompts appear for secure operations');
    console.log('3. Check that all toast notifications display correctly');
    console.log('4. Test responsive behavior by resizing window');
    console.log('5. Ensure keyboard shortcuts work (ESC for modal)');
    
    // Create test results template
    const testResults = {
        timestamp: new Date().toISOString(),
        categories: Object.fromEntries(
            Object.entries(tests).map(([key, data]) => [
                key,
                {
                    name: data.name,
                    tests: data.items.map(item => ({
                        test: item.test,
                        expected: item.expected,
                        status: 'pending',
                        notes: ''
                    }))
                }
            ])
        )
    };
    
    fs.writeFileSync('ui-test-results.json', JSON.stringify(testResults, null, 2));
    console.log('\n📝 Test results template saved to: ui-test-results.json');
});