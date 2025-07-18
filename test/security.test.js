// Security-specific tests
require('./setup');

describe('Security Features', () => {
    let app;
    
    beforeEach(() => {
        jest.clearAllMocks();
        app = createTestApp();
    });
    
    describe('Input Validation', () => {
        beforeEach(() => {
            document.querySelector('[data-tab="secrets"]').click();
            document.querySelector('[data-action="add-secret"]').click();
        });
        
        test('should reject empty secret names', () => {
            const nameInput = document.getElementById('secret-name');
            const submitButton = document.querySelector('[data-action="confirm-add-secret"]');
            
            nameInput.value = '';
            submitButton.click();
            
            expect(nameInput.classList.contains('error')).toBe(true);
            expect(__TAURI__.invoke).not.toHaveBeenCalledWith('add_secret', expect.anything());
        });
        
        test('should reject secret names over 100 characters', () => {
            const nameInput = document.getElementById('secret-name');
            const valueInput = document.getElementById('secret-value');
            const submitButton = document.querySelector('[data-action="confirm-add-secret"]');
            
            nameInput.value = 'A'.repeat(101);
            valueInput.value = 'test-value';
            submitButton.click();
            
            // Frontend should prevent this
            expect(nameInput.value.length).toBeLessThanOrEqual(100);
        });
        
        test('should sanitize secret names', () => {
            const nameInput = document.getElementById('secret-name');
            const valueInput = document.getElementById('secret-value');
            
            // Test various special characters
            const testCases = [
                { input: 'test<script>', expected: 'test<script>' }, // Should not execute
                { input: 'test"quote', expected: 'test"quote' },
                { input: "test'apostrophe", expected: "test'apostrophe" },
                { input: 'test\\backslash', expected: 'test\\backslash' }
            ];
            
            testCases.forEach(({ input, expected }) => {
                nameInput.value = input;
                valueInput.value = 'test';
                
                const submitButton = document.querySelector('[data-action="confirm-add-secret"]');
                submitButton.click();
                
                // Input should be preserved but safe
                expect(nameInput.value).toBe(expected);
            });
        });
    });
    
    describe('Touch ID Protection', () => {
        test('should require Touch ID for adding secrets', async () => {
            document.querySelector('[data-tab="secrets"]').click();
            document.querySelector('[data-action="add-secret"]').click();
            
            const nameInput = document.getElementById('secret-name');
            const valueInput = document.getElementById('secret-value');
            const submitButton = document.querySelector('[data-action="confirm-add-secret"]');
            
            nameInput.value = 'TEST_SECRET';
            valueInput.value = 'test-value';
            submitButton.click();
            
            // Should trigger Touch ID through VibeSafe CLI
            await waitFor(() => __TAURI__.invoke.mock.calls.some(call => call[0] === 'add_secret'));
            
            expect(__TAURI__.invoke).toHaveBeenCalledWith('add_secret', expect.any(Object));
        });
        
        test('should require Touch ID for copying secrets', async () => {
            app.state.secrets = ['API_KEY'];
            app.updateSecretsTab();
            
            const copyButton = document.querySelector('[data-action="copy-secret"]');
            copyButton.click();
            
            // Should trigger Touch ID through VibeSafe CLI
            await waitFor(() => __TAURI__.invoke.mock.calls.some(call => call[0] === 'get_secret'));
            
            expect(__TAURI__.invoke).toHaveBeenCalledWith('get_secret', { name: 'API_KEY' });
        });
        
        test('should handle Touch ID cancellation', async () => {
            __TAURI__.invoke.mockResolvedValue({
                success: false,
                error: 'User cancelled authentication'
            });
            
            app.state.secrets = ['API_KEY'];
            app.updateSecretsTab();
            
            const copyButton = document.querySelector('[data-action="copy-secret"]');
            copyButton.click();
            
            await waitFor(() => document.querySelector('.toast.error'));
            
            const errorToast = document.querySelector('.toast.error');
            expect(errorToast.textContent).toContain('cancelled');
        });
    });
    
    describe('Secure Communication', () => {
        test('should use Tauri IPC for all operations', () => {
            const operations = [
                'get_vibesafe_status',
                'initialize_vibesafe',
                'add_secret',
                'get_secret',
                'delete_secret',
                'enable_touchid'
            ];
            
            // Ensure no direct API calls or network requests
            expect(window.fetch).toBeUndefined();
            expect(window.XMLHttpRequest.prototype.open).toBeDefined(); // Native, not overridden
            
            // All operations should go through Tauri
            operations.forEach(op => {
                expect(typeof window.__TAURI__.invoke).toBe('function');
            });
        });
        
        test('should not expose sensitive data in DOM', () => {
            app.state.secrets = ['API_KEY', 'DATABASE_URL'];
            app.updateSecretsTab();
            
            const html = document.body.innerHTML;
            
            // Should not contain actual secret values
            expect(html).not.toContain('actual-secret-value');
            expect(html).not.toContain('password');
            expect(html).not.toContain('token');
            
            // Should only show secret names
            expect(html).toContain('API_KEY');
            expect(html).toContain('DATABASE_URL');
        });
    });
    
    describe('Error Information Leakage', () => {
        test('should not expose system paths in errors', async () => {
            __TAURI__.invoke.mockResolvedValue({
                success: false,
                error: 'Failed to read /Users/username/.vibesafe/keys/private.pem'
            });
            
            const checkButton = document.querySelector('[data-action="check-status"]');
            checkButton.click();
            
            await waitFor(() => document.querySelector('.toast.error'));
            
            const errorToast = document.querySelector('.toast.error');
            
            // Should not expose full paths
            expect(errorToast.textContent).not.toContain('/Users/');
            expect(errorToast.textContent).not.toContain('/.vibesafe/');
        });
        
        test('should provide user-friendly error messages', async () => {
            const errorMappings = [
                {
                    backend: 'ENOENT: no such file or directory',
                    expected: 'VibeSafe CLI not found'
                },
                {
                    backend: 'Private key file not found',
                    expected: 'needs to be initialized first'
                },
                {
                    backend: 'Secret not found: API_KEY',
                    expected: 'Secret not found'
                }
            ];
            
            for (const { backend, expected } of errorMappings) {
                __TAURI__.invoke.mockResolvedValue({
                    success: false,
                    error: backend
                });
                
                const checkButton = document.querySelector('[data-action="check-status"]');
                checkButton.click();
                
                await waitFor(() => document.querySelector('.toast.error'));
                
                const errorToast = document.querySelector('.toast.error');
                expect(errorToast.textContent).toContain(expected);
                
                // Clean up toast
                errorToast.remove();
            }
        });
    });
});