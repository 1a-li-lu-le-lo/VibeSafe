import { invoke } from './secure-invoke.js'

// === APPLICATION STATE ===

class VibeSafeApp {
    constructor() {
        this.state = {
            initialized: false,
            touchIdEnabled: false,
            secrets: [],
            secretsCount: 0,
            currentTab: 'home'
        }
        
        this.elements = {}
        this.eventListeners = new Map()
        this.updateManager = null
        this.currentVersion = '1.0.0'
        this.clipboardTimer = null
        this.clipboardTimeout = 30000 // 30 seconds default
        
        this.init()
    }
    
    // === INITIALIZATION ===
    
    init() {
        this.cacheElements()
        this.bindEvents()
        this.loadInitialData()
        this.initializeUpdateManager()
    }
    
    cacheElements() {
        this.elements = {
            // Navigation
            navTabs: document.querySelectorAll('.nav-tab'),
            tabContents: document.querySelectorAll('.tab-content'),
            
            // Status elements
            statusSection: document.getElementById('status-section'),
            keysStatus: document.getElementById('keys-status'),
            touchIdStatus: document.getElementById('touchid-status'),
            secretsCount: document.getElementById('secrets-count'),
            secretsPreview: document.getElementById('secrets-preview'),
            secretsList: document.getElementById('secrets-list'),
            
            // Modal elements
            modal: document.getElementById('add-secret-modal'),
            modalForm: document.getElementById('add-secret-form'),
            secretNameInput: document.getElementById('secret-name'),
            secretValueInput: document.getElementById('secret-value'),
            nameValidation: document.getElementById('name-validation'),
            valueValidation: document.getElementById('value-validation'),
            
            // Toast container
            toastContainer: document.getElementById('toast-container')
        }
    }
    
    bindEvents() {
        // Navigation tabs
        this.elements.navTabs.forEach(tab => {
            tab.addEventListener('click', this.handleTabClick.bind(this))
        })
        
        // Action buttons - use event delegation
        document.addEventListener('click', this.handleActionClick.bind(this))
        
        // Form validation
        if (this.elements.secretNameInput) {
            this.elements.secretNameInput.addEventListener('input', this.validateForm.bind(this))
            this.elements.secretNameInput.addEventListener('blur', this.validateForm.bind(this))
        }
        
        if (this.elements.secretValueInput) {
            this.elements.secretValueInput.addEventListener('input', this.validateForm.bind(this))
            this.elements.secretValueInput.addEventListener('blur', this.validateForm.bind(this))
        }
        
        // Modal events
        if (this.elements.modal) {
            this.elements.modal.addEventListener('click', this.handleModalClick.bind(this))
        }
        
        if (this.elements.modalForm) {
            this.elements.modalForm.addEventListener('submit', this.handleFormSubmit.bind(this))
        }
        
        // Keyboard events
        document.addEventListener('keydown', this.handleKeyDown.bind(this))
    }
    
    async loadInitialData() {
        try {
            await this.refreshStatus()
            // Get app version
            this.currentVersion = await invoke('get_app_version')
            
            // Load saved clipboard timeout
            const savedTimeout = localStorage.getItem('vibesafe_clipboard_timeout')
            if (savedTimeout) {
                this.clipboardTimeout = parseInt(savedTimeout, 10)
            }
        } catch (error) {
            console.error('Error loading initial data:', error)
            // Don't show error toast on initial load - it might just be uninitialized
            // The user can click "Show Status" to see the actual status
        }
    }
    
    async initializeUpdateManager() {
        if (window.UpdateManager) {
            this.updateManager = new window.UpdateManager(this)
            await this.updateManager.init()
        }
    }
    
    // === EVENT HANDLERS ===
    
    handleTabClick(event) {
        const tab = event.target
        const tabName = tab.dataset.tab
        
        if (tabName && tabName !== this.state.currentTab) {
            this.switchTab(tabName)
        }
    }
    
    async handleActionClick(event) {
        const button = event.target.closest('[data-action]')
        if (!button) return
        
        const action = button.dataset.action
        
        // Prevent double-clicking
        if (button.disabled) return
        
        try {
            switch (action) {
                case 'initialize':
                    await this.initializeVibeSafe(button)
                    break
                case 'show-status':
                    await this.showStatus()
                    break
                case 'add-secret':
                    this.showAddSecretModal()
                    break
                case 'refresh-secrets':
                    await this.refreshSecrets()
                    break
                case 'enable-touchid':
                    await this.enableTouchId(button)
                    break
                case 'check-status':
                    await this.showStatus()
                    break
                case 'setup-claude':
                    this.setupClaude()
                    break
                case 'test-claude':
                    await this.testClaude()
                    break
                case 'cancel-add-secret':
                    this.hideAddSecretModal()
                    break
                case 'submit-add-secret':
                    await this.submitAddSecret(button)
                    break
                default:
                    // Handle secret actions
                    if (action.startsWith('get-secret-')) {
                        const secretName = action.replace('get-secret-', '')
                        await this.getSecret(secretName)
                    } else if (action.startsWith('delete-secret-')) {
                        const secretName = action.replace('delete-secret-', '')
                        await this.deleteSecret(secretName)
                    }
            }
        } catch (error) {
            console.error('Error handling action:', action, error)
            this.showToast(`Error: ${error.message}`, 'error')
        }
    }
    
    handleModalClick(event) {
        if (event.target === this.elements.modal) {
            this.hideAddSecretModal()
        }
    }
    
    async handleFormSubmit(event) {
        event.preventDefault()
        const submitButton = this.elements.modal.querySelector('[data-action="submit-add-secret"]')
        await this.submitAddSecret(submitButton)
    }
    
    handleKeyDown(event) {
        if (event.key === 'Escape') {
            if (this.elements.modal && this.elements.modal.classList.contains('modal--active')) {
                this.hideAddSecretModal()
            }
        }
    }
    
    // === NAVIGATION ===
    
    switchTab(tabName) {
        // Update nav tabs
        this.elements.navTabs.forEach(tab => {
            const isActive = tab.dataset.tab === tabName
            tab.classList.toggle('nav-tab--active', isActive)
            tab.setAttribute('aria-selected', isActive)
        })
        
        // Update tab contents
        this.elements.tabContents.forEach(content => {
            const isActive = content.id === `${tabName}-tab`
            content.classList.toggle('tab-content--active', isActive)
        })
        
        // Update state
        this.state.currentTab = tabName
        
        // Load update settings UI when switching to settings tab
        if (tabName === 'settings') {
            if (this.updateManager) {
                this.renderUpdateSettings()
            }
            this.attachClipboardSettingsListeners()
        }
        
        // Load tab-specific data
        if (tabName === 'secrets') {
            this.refreshSecrets()
        }
    }
    
    // === VIBESAFE OPERATIONS ===
    
    async initializeVibeSafe(button) {
        const originalText = button.textContent
        
        try {
            this.setButtonLoading(button, 'Initializing...')
            
            const result = await invoke('initialize_vibesafe')
            
            if (result.success) {
                this.state.initialized = true
                this.showToast('VibeSafe initialized successfully!', 'success')
                await this.refreshStatus()
            } else {
                this.showToast(`Failed to initialize VibeSafe: ${result.error}`, 'error')
            }
        } catch (error) {
            this.showToast(`Error initializing VibeSafe: ${error.message}`, 'error')
        } finally {
            this.setButtonNormal(button, originalText)
        }
    }
    
    async showStatus() {
        try {
            const result = await invoke('get_vibesafe_status')
            
            if (result.success) {
                this.state = { ...this.state, ...result.data }
                this.updateStatusDisplay()
                this.elements.statusSection?.classList.remove('hidden')
            } else {
                this.showToast(`Failed to get status: ${result.error}`, 'error')
            }
        } catch (error) {
            this.showToast(`Error getting status: ${error.message}`, 'error')
        }
    }
    
    async refreshStatus() {
        await this.showStatus()
    }
    
    async refreshSecrets() {
        await this.refreshStatus()
        this.updateSecretsDisplay()
    }
    
    async enableTouchId(button) {
        const originalText = button.textContent
        
        try {
            this.setButtonLoading(button, 'Enabling...')
            
            const result = await invoke('enable_touchid')
            
            if (result.success) {
                this.state.touchIdEnabled = true
                this.showToast('Touch ID protection enabled!', 'success')
                await this.refreshStatus()
            } else {
                this.showToast(`Failed to enable Touch ID: ${result.error}`, 'error')
            }
        } catch (error) {
            this.showToast(`Error enabling Touch ID: ${error.message}`, 'error')
        } finally {
            this.setButtonNormal(button, originalText)
        }
    }
    
    async getSecret(name) {
        try {
            this.showToast('Touch ID authentication required...', 'info')
            
            const result = await invoke('get_secret', { name })
            
            if (result.success) {
                // Extract the actual value but never log it
                let secretValue = result.data.value
                
                // Copy to clipboard
                await navigator.clipboard.writeText(secretValue)
                
                // Show success with masked value for security
                this.showToast(`Secret "${name}" copied to clipboard! Will clear in ${this.clipboardTimeout / 1000} seconds.`, 'success')
                this.startClipboardTimer()
                
                // Clear the secret from memory
                secretValue = null
            } else {
                this.showToast(`Failed to get secret: ${result.error}`, 'error')
            }
        } catch (error) {
            this.showToast(`Error getting secret: ${error.message}`, 'error')
        }
    }
    
    startClipboardTimer() {
        // Don't start timer if timeout is 0 (disabled)
        if (this.clipboardTimeout === 0) {
            return
        }
        
        // Clear any existing timer
        if (this.clipboardTimer) {
            clearTimeout(this.clipboardTimer)
        }
        
        // Start new timer
        this.clipboardTimer = setTimeout(async () => {
            try {
                // Clear clipboard by writing empty string
                await navigator.clipboard.writeText('')
                this.showToast('Clipboard cleared for security', 'info')
            } catch (error) {
                console.error('Failed to clear clipboard:', error)
            }
            this.clipboardTimer = null
        }, this.clipboardTimeout)
    }
    
    async deleteSecret(name) {
        const confirmed = confirm(
            `Are you sure you want to delete the secret "${name}"?\n\nThis action cannot be undone.`
        )
        
        if (!confirmed) return
        
        try {
            const result = await invoke('delete_secret', { name })
            
            if (result.success) {
                this.showToast(`Secret "${name}" deleted successfully!`, 'success')
                await this.refreshSecrets()
            } else {
                this.showToast(`Failed to delete secret: ${result.error}`, 'error')
            }
        } catch (error) {
            this.showToast(`Error deleting secret: ${error.message}`, 'error')
        }
    }
    
    // === MODAL MANAGEMENT ===
    
    showAddSecretModal() {
        if (!this.elements.modal) return
        
        this.elements.modal.classList.add('modal--active')
        this.elements.modal.setAttribute('aria-hidden', 'false')
        
        // Focus first input
        if (this.elements.secretNameInput) {
            this.elements.secretNameInput.focus()
        }
    }
    
    hideAddSecretModal() {
        if (!this.elements.modal) return
        
        this.elements.modal.classList.remove('modal--active')
        this.elements.modal.setAttribute('aria-hidden', 'true')
        
        // Clear form
        this.clearForm()
    }
    
    clearForm() {
        if (this.elements.secretNameInput) {
            this.elements.secretNameInput.value = ''
            this.elements.secretNameInput.classList.remove('form-input--error', 'form-input--success')
        }
        
        if (this.elements.secretValueInput) {
            this.elements.secretValueInput.value = ''
            this.elements.secretValueInput.classList.remove('form-input--error', 'form-input--success')
        }
        
        if (this.elements.nameValidation) {
            this.elements.nameValidation.textContent = ''
            this.elements.nameValidation.className = 'form-validation'
        }
        
        if (this.elements.valueValidation) {
            this.elements.valueValidation.textContent = ''
            this.elements.valueValidation.className = 'form-validation'
        }
    }
    
    async submitAddSecret(button) {
        if (!this.validateForm()) return
        
        const name = this.elements.secretNameInput?.value?.trim()
        const value = this.elements.secretValueInput?.value?.trim()
        
        if (!name || !value) {
            this.showToast('Please enter both secret name and value', 'error')
            return
        }
        
        const originalText = button.textContent
        
        try {
            this.setButtonLoading(button, 'Adding...')
            this.showToast('Touch ID authentication required...', 'info')
            
            const result = await invoke('add_secret', { name, value })
            
            if (result.success) {
                this.showToast('Secret added successfully!', 'success')
                this.hideAddSecretModal()
                await this.refreshSecrets()
            } else {
                this.showToast(`Failed to add secret: ${result.error}`, 'error')
            }
        } catch (error) {
            this.showToast(`Error adding secret: ${error.message}`, 'error')
        } finally {
            this.setButtonNormal(button, originalText)
        }
    }
    
    // === FORM VALIDATION ===
    
    validateForm() {
        let isValid = true
        
        // Validate name
        if (this.elements.secretNameInput && this.elements.nameValidation) {
            const name = this.elements.secretNameInput.value.trim()
            
            if (!name) {
                this.setFieldError(this.elements.secretNameInput, this.elements.nameValidation, 'Secret name is required')
                isValid = false
            } else if (name.length > 100) {
                this.setFieldError(this.elements.secretNameInput, this.elements.nameValidation, 'Secret name too long (max 100 characters)')
                isValid = false
            } else {
                this.setFieldSuccess(this.elements.secretNameInput, this.elements.nameValidation, '✓ Valid name')
            }
        }
        
        // Validate value
        if (this.elements.secretValueInput && this.elements.valueValidation) {
            const value = this.elements.secretValueInput.value.trim()
            
            if (!value) {
                this.setFieldError(this.elements.secretValueInput, this.elements.valueValidation, 'Secret value is required')
                isValid = false
            } else {
                this.setFieldSuccess(this.elements.secretValueInput, this.elements.valueValidation, '✓ Valid value')
            }
        }
        
        return isValid
    }
    
    setFieldError(input, validation, message) {
        input.classList.remove('form-input--success')
        input.classList.add('form-input--error')
        validation.textContent = message
        validation.className = 'form-validation'
    }
    
    setFieldSuccess(input, validation, message) {
        input.classList.remove('form-input--error')
        input.classList.add('form-input--success')
        validation.textContent = message
        validation.className = 'form-validation form-validation--success'
    }
    
    // === UI UPDATES ===
    
    updateStatusDisplay() {
        if (this.elements.keysStatus) {
            this.elements.keysStatus.textContent = this.state.initialized ? 'Initialized' : 'Not initialized'
        }
        
        if (this.elements.touchIdStatus) {
            this.elements.touchIdStatus.textContent = this.state.touchIdEnabled ? 'Enabled' : 'Disabled'
        }
        
        if (this.elements.secretsCount) {
            this.elements.secretsCount.textContent = this.state.secretsCount.toString()
        }
        
        this.updateSecretsDisplay()
    }
    
    updateSecretsDisplay() {
        // Update secrets preview in home tab
        if (this.elements.secretsPreview) {
            this.renderSecretsList(this.elements.secretsPreview, true)
        }
        
        // Update full secrets list in secrets tab
        if (this.elements.secretsList) {
            this.renderSecretsList(this.elements.secretsList, false)
        }
    }
    
    renderSecretsList(container, isPreview = false) {
        if (!container) return
        
        container.innerHTML = ''
        
        if (!this.state.secrets || this.state.secrets.length === 0) {
            const emptyState = document.createElement('div')
            emptyState.className = 'empty-state'
            emptyState.innerHTML = `
                <div class="empty-state__icon">🔐</div>
                <div class="empty-state__title">No secrets stored yet</div>
                <div class="empty-state__description">
                    Click "Add Secret" to securely store your first API key or password
                </div>
            `
            container.appendChild(emptyState)
            return
        }
        
        const secretsToShow = isPreview ? this.state.secrets.slice(0, 3) : this.state.secrets
        
        secretsToShow.forEach(secret => {
            const secretItem = document.createElement('div')
            secretItem.className = 'secret-item'
            secretItem.innerHTML = `
                <span class="secret-item__name">${this.escapeHtml(secret)}</span>
                <div class="secret-item__actions">
                    <button class="btn btn--small btn--primary" data-action="get-secret-${secret}">
                        Copy
                    </button>
                    <button class="btn btn--small btn--danger" data-action="delete-secret-${secret}">
                        Delete
                    </button>
                </div>
            `
            container.appendChild(secretItem)
        })
        
        if (isPreview && this.state.secrets.length > 3) {
            const moreItem = document.createElement('div')
            moreItem.className = 'secret-item'
            moreItem.innerHTML = `
                <span class="secret-item__name">... and ${this.state.secrets.length - 3} more</span>
                <div class="secret-item__actions">
                    <button class="btn btn--small btn--secondary" data-action="view-all-secrets">
                        View All
                    </button>
                </div>
            `
            container.appendChild(moreItem)
        }
    }
    
    // === BUTTON STATES ===
    
    setButtonLoading(button, text) {
        button.disabled = true
        button.innerHTML = `
            <span class="loading-spinner"></span>
            ${text}
        `
    }
    
    setButtonNormal(button, text) {
        button.disabled = false
        button.innerHTML = text
    }
    
    // === TOAST NOTIFICATIONS ===
    
    showToast(message, type = 'info') {
        if (!this.elements.toastContainer) return
        
        const toast = document.createElement('div')
        toast.className = `toast toast--${type}`
        toast.innerHTML = `
            <div class="toast__message">${this.escapeHtml(message)}</div>
        `
        
        this.elements.toastContainer.appendChild(toast)
        
        // Trigger animation
        setTimeout(() => {
            toast.classList.add('toast--active')
        }, 100)
        
        // Remove after 4 seconds
        setTimeout(() => {
            toast.classList.remove('toast--active')
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast)
                }
            }, 300)
        }, 4000)
    }
    
    // === CLAUDE INTEGRATION ===
    
    setupClaude() {
        this.showToast('Claude integration is ready! Use "vibesafe get SECRET_NAME" in Claude Code sessions.', 'info')
    }
    
    async testClaude() {
        try {
            const result = await invoke('get_vibesafe_status')
            
            if (result.success && result.data.initialized) {
                this.showToast('✅ Claude integration test passed! VibeSafe is ready for use with Claude Code.', 'success')
            } else {
                this.showToast('❌ Claude integration test failed! Please initialize VibeSafe first.', 'error')
            }
        } catch (error) {
            this.showToast(`❌ Claude integration test failed! Error: ${error.message}`, 'error')
        }
    }
    
    // === UPDATE MANAGEMENT ===
    
    renderUpdateSettings() {
        const container = document.getElementById('update-settings-container')
        if (!container || !this.updateManager) return
        
        container.innerHTML = this.updateManager.renderSettingsUI()
        this.updateManager.attachSettingsListeners(container)
    }
    
    attachClipboardSettingsListeners() {
        const clipboardSelect = document.getElementById('clipboard-timeout')
        if (clipboardSelect) {
            // Set current value
            clipboardSelect.value = this.clipboardTimeout.toString()
            
            // Add change listener
            clipboardSelect.addEventListener('change', (e) => {
                this.clipboardTimeout = parseInt(e.target.value, 10)
                
                // Save to localStorage
                localStorage.setItem('vibesafe_clipboard_timeout', this.clipboardTimeout.toString())
                
                if (this.clipboardTimeout === 0) {
                    this.showToast('Clipboard auto-clear disabled', 'info')
                } else {
                    this.showToast(`Clipboard will auto-clear after ${this.clipboardTimeout / 1000} seconds`, 'success')
                }
            })
        }
    }
    
    // === UTILITIES ===
    
    escapeHtml(text) {
        const div = document.createElement('div')
        div.textContent = text
        return div.innerHTML
    }
}

// === INITIALIZE APP ===

document.addEventListener('DOMContentLoaded', () => {
    new VibeSafeApp()
})