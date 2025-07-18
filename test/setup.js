// Test setup and utilities
const { spawn } = require('child_process');
const path = require('path');

// Mock Tauri API for testing
global.__TAURI__ = {
    invoke: jest.fn(),
    window: {
        appWindow: {
            minimize: jest.fn(),
            toggleMaximize: jest.fn(),
            close: jest.fn()
        }
    }
};

// Mock Touch ID responses
global.mockTouchIdSuccess = () => {
    global.__TAURI__.invoke.mockResolvedValue({
        success: true,
        data: { message: "Touch ID authenticated" }
    });
};

global.mockTouchIdFailure = () => {
    global.__TAURI__.invoke.mockResolvedValue({
        success: false,
        error: "Touch ID authentication failed"
    });
};

// Test utilities
global.createTestApp = () => {
    document.body.innerHTML = `
        <div id="app">
            <nav class="tabs">
                <div class="tab active" data-tab="home">Home</div>
                <div class="tab" data-tab="secrets">Secrets</div>
                <div class="tab" data-tab="settings">Settings</div>
                <div class="tab" data-tab="claude">Claude</div>
            </nav>
            <main id="main-content"></main>
            <div id="add-secret-modal" class="modal"></div>
            <div id="toast-container"></div>
        </div>
    `;
    
    // Load the app
    require('../src/main.js');
    
    return window.app;
};

// Wait for async operations
global.waitFor = (condition, timeout = 5000) => {
    return new Promise((resolve, reject) => {
        const interval = 100;
        let elapsed = 0;
        
        const check = () => {
            if (condition()) {
                resolve();
            } else if (elapsed >= timeout) {
                reject(new Error('Timeout waiting for condition'));
            } else {
                elapsed += interval;
                setTimeout(check, interval);
            }
        };
        
        check();
    });
};