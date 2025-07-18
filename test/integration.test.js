// Integration tests with Tauri backend
const { spawn } = require('child_process');
const { WebDriver, By, until } = require('selenium-webdriver');

describe('Integration Tests', () => {
    let driver;
    let tauriProcess;
    
    beforeAll(async () => {
        // Start Tauri in test mode
        tauriProcess = spawn('npm', ['run', 'tauri', 'dev'], {
            env: { ...process.env, RUST_LOG: 'info' }
        });
        
        // Wait for app to start
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // Connect WebDriver
        driver = await new WebDriver.Builder()
            .forBrowser('safari')
            .build();
            
        await driver.get('tauri://localhost');
    }, 30000);
    
    afterAll(async () => {
        if (driver) {
            await driver.quit();
        }
        if (tauriProcess) {
            tauriProcess.kill();
        }
    });
    
    describe('Full Workflow', () => {
        test('should complete full secret management workflow', async () => {
            // Wait for app to load
            await driver.wait(until.elementLocated(By.css('.tabs')), 10000);
            
            // Navigate to secrets tab
            const secretsTab = await driver.findElement(By.css('[data-tab="secrets"]'));
            await secretsTab.click();
            
            // Click add secret
            const addButton = await driver.findElement(By.css('[data-action="add-secret"]'));
            await addButton.click();
            
            // Fill form
            const nameInput = await driver.findElement(By.id('secret-name'));
            await nameInput.sendKeys('INTEGRATION_TEST_SECRET');
            
            const valueInput = await driver.findElement(By.id('secret-value'));
            await valueInput.sendKeys('test-value-12345');
            
            // Submit (will trigger Touch ID)
            const submitButton = await driver.findElement(By.css('[data-action="confirm-add-secret"]'));
            await submitButton.click();
            
            // Wait for Touch ID prompt and result
            await driver.wait(until.elementLocated(By.css('.toast')), 30000);
            
            // Verify secret was added
            await driver.navigate().refresh();
            await driver.wait(until.elementLocated(By.css('.secret-item')), 10000);
            
            const secretItem = await driver.findElement(By.css('.secret-item'));
            const secretName = await secretItem.getText();
            expect(secretName).toContain('INTEGRATION_TEST_SECRET');
            
            // Test copy functionality
            const copyButton = await driver.findElement(By.css('[data-action="copy-secret"]'));
            await copyButton.click();
            
            // Wait for Touch ID and copy confirmation
            await driver.wait(until.elementLocated(By.css('.toast.success')), 30000);
            
            // Clean up - delete the test secret
            const deleteButton = await driver.findElement(By.css('[data-action="delete-secret"]'));
            await deleteButton.click();
            
            // Confirm deletion
            const confirmButton = await driver.findElement(By.css('[data-action="confirm-delete"]'));
            await confirmButton.click();
            
            await driver.wait(until.elementLocated(By.css('.toast.success')), 10000);
        }, 60000);
    });
    
    describe('Error Scenarios', () => {
        test('should handle VibeSafe not initialized', async () => {
            // This assumes VibeSafe is not initialized
            // Navigate to home
            const homeTab = await driver.findElement(By.css('[data-tab="home"]'));
            await homeTab.click();
            
            // Should show initialization prompt
            await driver.wait(until.elementLocated(By.css('[data-action="initialize"]')), 10000);
            
            const initButton = await driver.findElement(By.css('[data-action="initialize"]'));
            expect(await initButton.isDisplayed()).toBe(true);
        });
        
        test('should handle Touch ID cancellation', async () => {
            // Navigate to secrets
            const secretsTab = await driver.findElement(By.css('[data-tab="secrets"]'));
            await secretsTab.click();
            
            // Try to add secret but cancel Touch ID
            const addButton = await driver.findElement(By.css('[data-action="add-secret"]'));
            await addButton.click();
            
            const nameInput = await driver.findElement(By.id('secret-name'));
            await nameInput.sendKeys('CANCEL_TEST');
            
            const valueInput = await driver.findElement(By.id('secret-value'));
            await valueInput.sendKeys('test');
            
            const submitButton = await driver.findElement(By.css('[data-action="confirm-add-secret"]'));
            await submitButton.click();
            
            // User cancels Touch ID here
            // Wait for error toast
            await driver.wait(until.elementLocated(By.css('.toast.error')), 30000);
            
            const errorToast = await driver.findElement(By.css('.toast.error'));
            const errorText = await errorToast.getText();
            expect(errorText.toLowerCase()).toContain('cancel');
        });
    });
});