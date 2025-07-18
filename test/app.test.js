// Main app functionality tests
require('./setup');

describe('VibeSafe App', () => {
    let app;
    
    beforeEach(() => {
        jest.clearAllMocks();
        app = createTestApp();
    });
    
    afterEach(() => {
        document.body.innerHTML = '';
    });
    
    describe('Initialization', () => {
        test('should create app instance', () => {
            expect(app).toBeDefined();
            expect(app.constructor.name).toBe('VibeSafeApp');
        });
        
        test('should initialize with default state', () => {
            expect(app.state).toEqual({
                initialized: false,
                touchIdEnabled: false,
                secrets: [],
                secretsCount: 0,
                currentTab: 'home'
            });
        });
        
        test('should check status on startup', async () => {
            await waitFor(() => __TAURI__.invoke.mock.calls.length > 0);
            expect(__TAURI__.invoke).toHaveBeenCalledWith('get_vibesafe_status');
        });
    });
    
    describe('Navigation', () => {
        test('should switch tabs correctly', () => {
            const secretsTab = document.querySelector('[data-tab="secrets"]');
            secretsTab.click();
            
            expect(app.state.currentTab).toBe('secrets');
            expect(secretsTab.classList.contains('active')).toBe(true);
        });
        
        test('should render correct content for each tab', () => {
            const tabs = ['home', 'secrets', 'settings', 'claude'];
            
            tabs.forEach(tabName => {
                const tab = document.querySelector(`[data-tab="${tabName}"]`);
                tab.click();
                
                const content = document.getElementById('main-content');
                expect(content.innerHTML).toContain(`${tabName}-tab`);
            });
        });
    });
    
    describe('Secret Management', () => {
        beforeEach(() => {
            // Navigate to secrets tab
            document.querySelector('[data-tab="secrets"]').click();
        });
        
        test('should open add secret modal', () => {
            const addButton = document.querySelector('[data-action="add-secret"]');
            addButton.click();
            
            const modal = document.getElementById('add-secret-modal');
            expect(modal.classList.contains('active')).toBe(true);
        });
        
        test('should validate secret form', () => {
            const addButton = document.querySelector('[data-action="add-secret"]');
            addButton.click();
            
            const nameInput = document.getElementById('secret-name');
            const valueInput = document.getElementById('secret-value');
            const submitButton = document.querySelector('[data-action="confirm-add-secret"]');
            
            // Empty form should be invalid
            submitButton.click();
            expect(nameInput.classList.contains('error')).toBe(true);
            expect(valueInput.classList.contains('error')).toBe(true);
            
            // Fill form
            nameInput.value = 'TEST_SECRET';
            nameInput.dispatchEvent(new Event('input'));
            valueInput.value = 'test-value-123';
            valueInput.dispatchEvent(new Event('input'));
            
            // Should remove error classes
            expect(nameInput.classList.contains('error')).toBe(false);
            expect(valueInput.classList.contains('error')).toBe(false);
        });
        
        test('should add secret with Touch ID', async () => {
            __TAURI__.invoke.mockResolvedValue({
                success: true,
                data: { message: 'Secret added successfully' }
            });
            
            const addButton = document.querySelector('[data-action="add-secret"]');
            addButton.click();
            
            const nameInput = document.getElementById('secret-name');
            const valueInput = document.getElementById('secret-value');
            const submitButton = document.querySelector('[data-action="confirm-add-secret"]');
            
            nameInput.value = 'TEST_SECRET';
            nameInput.dispatchEvent(new Event('input'));
            valueInput.value = 'test-value-123';
            valueInput.dispatchEvent(new Event('input'));
            
            submitButton.click();
            
            await waitFor(() => __TAURI__.invoke.mock.calls.some(call => call[0] === 'add_secret'));
            
            expect(__TAURI__.invoke).toHaveBeenCalledWith('add_secret', {
                name: 'TEST_SECRET',
                value: 'test-value-123'
            });
        });
        
        test('should copy secret with Touch ID', async () => {
            // Mock secrets list
            app.state.secrets = ['API_KEY', 'DATABASE_URL'];
            app.updateSecretsTab();
            
            __TAURI__.invoke.mockResolvedValue({
                success: true,
                data: 'secret-value-123'
            });
            
            const copyButton = document.querySelector('[data-action="copy-secret"]');
            copyButton.click();
            
            await waitFor(() => __TAURI__.invoke.mock.calls.some(call => call[0] === 'get_secret'));
            
            expect(__TAURI__.invoke).toHaveBeenCalledWith('get_secret', {
                name: 'API_KEY'
            });
        });
    });
    
    describe('Touch ID', () => {
        test('should enable Touch ID', async () => {
            document.querySelector('[data-tab="settings"]').click();
            
            __TAURI__.invoke.mockResolvedValue({
                success: true,
                data: { message: 'Touch ID enabled' }
            });
            
            const enableButton = document.querySelector('[data-action="enable-touchid"]');
            enableButton.click();
            
            await waitFor(() => __TAURI__.invoke.mock.calls.some(call => call[0] === 'enable_touchid'));
            
            expect(__TAURI__.invoke).toHaveBeenCalledWith('enable_touchid');
        });
    });
    
    describe('Error Handling', () => {
        test('should show error toast on failure', async () => {
            __TAURI__.invoke.mockResolvedValue({
                success: false,
                error: 'Test error message'
            });
            
            const checkButton = document.querySelector('[data-action="check-status"]');
            checkButton.click();
            
            await waitFor(() => document.querySelector('.toast.error'));
            
            const errorToast = document.querySelector('.toast.error');
            expect(errorToast.textContent).toContain('Test error message');
        });
        
        test('should handle network errors gracefully', async () => {
            __TAURI__.invoke.mockRejectedValue(new Error('Network error'));
            
            const checkButton = document.querySelector('[data-action="check-status"]');
            checkButton.click();
            
            await waitFor(() => document.querySelector('.toast.error'));
            
            const errorToast = document.querySelector('.toast.error');
            expect(errorToast.textContent).toContain('unexpected error');
        });
    });
    
    describe('Modal Management', () => {
        test('should close modal on escape key', () => {
            const addButton = document.querySelector('[data-action="add-secret"]');
            addButton.click();
            
            const modal = document.getElementById('add-secret-modal');
            expect(modal.classList.contains('active')).toBe(true);
            
            const escEvent = new KeyboardEvent('keydown', { key: 'Escape' });
            document.dispatchEvent(escEvent);
            
            expect(modal.classList.contains('active')).toBe(false);
        });
        
        test('should close modal on backdrop click', () => {
            const addButton = document.querySelector('[data-action="add-secret"]');
            addButton.click();
            
            const modal = document.getElementById('add-secret-modal');
            modal.click();
            
            expect(modal.classList.contains('active')).toBe(false);
        });
    });
});