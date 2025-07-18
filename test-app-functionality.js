#!/usr/bin/env node

const { exec } = require('child_process');
const fs = require('fs');

console.log('VibeSafe App Functionality Test');
console.log('================================\n');

// Test checklist based on Gemini analysis
const tests = [
    {
        name: 'App Launch',
        description: 'Check if the app launches successfully',
        priority: 'High'
    },
    {
        name: 'Navigation',
        description: 'Verify tab navigation works (Home, Secrets, Settings, Claude)',
        priority: 'High'
    },
    {
        name: 'Initialize VibeSafe',
        description: 'Test the "Initialize VibeSafe" button functionality',
        priority: 'High'
    },
    {
        name: 'Add Secret Modal',
        description: 'Test if "Add Secret" button opens modal correctly',
        priority: 'High'
    },
    {
        name: 'Cancel Button',
        description: 'Verify modal cancel button and ESC key close the modal',
        priority: 'High'
    },
    {
        name: 'Form Validation',
        description: 'Test form validation for secret name and value',
        priority: 'Medium'
    },
    {
        name: 'Touch ID Prompt',
        description: 'Check if Touch ID authentication is triggered when adding secrets',
        priority: 'High'
    },
    {
        name: 'Toast Notifications',
        description: 'Verify toast notifications appear for various actions',
        priority: 'Medium'
    },
    {
        name: 'Status Display',
        description: 'Check if system status updates correctly',
        priority: 'Medium'
    },
    {
        name: 'Responsive Design',
        description: 'Test window resizing and responsive behavior',
        priority: 'Low'
    }
];

console.log('Test Checklist:');
console.log('---------------');
tests.forEach((test, index) => {
    console.log(`${index + 1}. [${test.priority}] ${test.name}`);
    console.log(`   ${test.description}`);
    console.log('');
});

console.log('\nManual Testing Instructions:');
console.log('----------------------------');
console.log('1. The app should be running at http://localhost:1420/');
console.log('2. Go through each test in the checklist above');
console.log('3. Note any issues or failures');
console.log('4. Pay special attention to Touch ID prompts and error handling');
console.log('\n');

// Check if VibeSafe CLI is available
exec('which vibesafe', (error, stdout, stderr) => {
    if (error) {
        console.log('⚠️  VibeSafe CLI not found in PATH');
        console.log('   Make sure VibeSafe CLI is installed for Touch ID functionality');
    } else {
        console.log('✅ VibeSafe CLI found at:', stdout.trim());
    }
});

// Create a test results file
const testResults = {
    date: new Date().toISOString(),
    tests: tests.map(test => ({
        ...test,
        status: 'pending',
        notes: ''
    }))
};

fs.writeFileSync('test-results.json', JSON.stringify(testResults, null, 2));
console.log('\n📝 Test results template created at: test-results.json');
console.log('   Update this file with your test results.');