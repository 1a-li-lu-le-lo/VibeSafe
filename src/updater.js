// Update management module
class UpdateManager {
    constructor(app) {
        this.app = app;
        this.checkInterval = null;
        this.settings = {
            autoCheck: true,
            autoDownload: false,
            autoInstall: false,
            channel: 'stable',
            notifications: true
        };
        this.pendingUpdate = null;
    }

    async init() {
        // Load settings
        await this.loadSettings();
        
        // Check for updates on startup
        if (this.settings.autoCheck) {
            setTimeout(() => this.checkForUpdates(true), 5000);
        }
        
        // Set up periodic checks
        this.startPeriodicChecks();
        
        // Listen for restart events
        window.__TAURI__.event.listen('update:restart-required', () => {
            this.showRestartPrompt();
        });
    }

    async loadSettings() {
        try {
            const settings = await window.__TAURI__.invoke('get_update_settings');
            this.settings = settings;
        } catch (error) {
            console.error('Failed to load update settings:', error);
        }
    }

    async saveSettings() {
        try {
            await window.__TAURI__.invoke('save_update_settings', {
                settings: this.settings
            });
        } catch (error) {
            console.error('Failed to save update settings:', error);
        }
    }

    startPeriodicChecks() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
        }
        
        if (this.settings.autoCheck) {
            // Check every 6 hours
            this.checkInterval = setInterval(() => {
                this.checkForUpdates(true);
            }, 6 * 60 * 60 * 1000);
        }
    }

    async checkForUpdates(silent = false) {
        try {
            const updateInfo = await window.__TAURI__.invoke('check_for_updates', {
                settings: this.settings
            });
            
            if (updateInfo) {
                this.pendingUpdate = updateInfo;
                
                if (this.settings.notifications || !silent) {
                    this.showUpdateNotification(updateInfo);
                }
                
                if (this.settings.autoDownload) {
                    await this.downloadUpdate();
                }
            } else if (!silent) {
                this.app.showToast('You are using the latest version', 'success');
            }
            
            return updateInfo;
        } catch (error) {
            console.error('Update check failed:', error);
            if (!silent) {
                this.app.showToast('Failed to check for updates', 'error');
            }
            return null;
        }
    }

    showUpdateNotification(updateInfo) {
        const notification = document.createElement('div');
        notification.className = 'update-notification';
        notification.innerHTML = `
            <div class="update-notification__content">
                <h3>Update Available</h3>
                <p>Version ${updateInfo.version} is available (you have ${this.app.currentVersion})</p>
                <div class="update-notification__actions">
                    <button class="btn btn-primary" data-action="view-update">View Details</button>
                    <button class="btn btn-text" data-action="dismiss-update">Later</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Add event listeners
        notification.querySelector('[data-action="view-update"]').addEventListener('click', () => {
            this.showUpdateDialog(updateInfo);
            notification.remove();
        });
        
        notification.querySelector('[data-action="dismiss-update"]').addEventListener('click', () => {
            notification.remove();
        });
        
        // Auto-dismiss after 10 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 10000);
    }

    showUpdateDialog(updateInfo) {
        const modal = document.createElement('div');
        modal.className = 'modal active';
        modal.innerHTML = `
            <div class="modal-content update-dialog">
                <div class="modal-header">
                    <h2>Update Available</h2>
                    <button class="modal-close" data-action="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="update-info">
                        <h3>VibeSafe ${updateInfo.version}</h3>
                        <p class="update-date">Released ${new Date(updateInfo.pub_date).toLocaleDateString()}</p>
                        <div class="update-size">Size: ${this.formatBytes(updateInfo.size)}</div>
                    </div>
                    
                    <div class="update-notes">
                        <h4>What's New</h4>
                        <div class="update-notes__content">${this.formatReleaseNotes(updateInfo.notes)}</div>
                    </div>
                    
                    <div class="update-progress" style="display: none;">
                        <div class="progress-bar">
                            <div class="progress-bar__fill" style="width: 0%"></div>
                        </div>
                        <p class="progress-text">Downloading update...</p>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" data-action="close-modal">Later</button>
                    <button class="btn btn-primary" data-action="download-update">Download Update</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Event handlers
        const closeModal = () => modal.remove();
        
        modal.querySelectorAll('[data-action="close-modal"]').forEach(el => {
            el.addEventListener('click', closeModal);
        });
        
        modal.querySelector('[data-action="download-update"]').addEventListener('click', async () => {
            modal.querySelector('.update-progress').style.display = 'block';
            modal.querySelector('[data-action="download-update"]').disabled = true;
            
            try {
                await this.downloadUpdate((progress) => {
                    modal.querySelector('.progress-bar__fill').style.width = `${progress}%`;
                    modal.querySelector('.progress-text').textContent = `Downloading update... ${progress}%`;
                });
                
                modal.querySelector('.progress-text').textContent = 'Update ready to install';
                modal.querySelector('[data-action="download-update"]').textContent = 'Install Now';
                modal.querySelector('[data-action="download-update"]').disabled = false;
                modal.querySelector('[data-action="download-update"]').onclick = () => this.installUpdate();
                
            } catch (error) {
                this.app.showToast('Failed to download update', 'error');
                closeModal();
            }
        });
    }

    async downloadUpdate(progressCallback) {
        if (!this.pendingUpdate) {
            throw new Error('No update available');
        }
        
        try {
            const updatePath = await window.__TAURI__.invoke('download_update', {
                updateInfo: this.pendingUpdate
            });
            
            this.pendingUpdate.downloadPath = updatePath;
            
            if (this.settings.autoInstall) {
                await this.installUpdate();
            }
            
            return updatePath;
        } catch (error) {
            console.error('Download failed:', error);
            throw error;
        }
    }

    async installUpdate() {
        if (!this.pendingUpdate || !this.pendingUpdate.downloadPath) {
            throw new Error('No update downloaded');
        }
        
        try {
            await window.__TAURI__.invoke('install_update', {
                updatePath: this.pendingUpdate.downloadPath
            });
            
            // Update will trigger restart event
        } catch (error) {
            console.error('Installation failed:', error);
            this.app.showToast('Failed to install update', 'error');
        }
    }

    showRestartPrompt() {
        const modal = document.createElement('div');
        modal.className = 'modal active';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Restart Required</h2>
                </div>
                <div class="modal-body">
                    <p>VibeSafe has been updated. Please restart the application to use the new version.</p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" data-action="restart-later">Later</button>
                    <button class="btn btn-primary" data-action="restart-now">Restart Now</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        modal.querySelector('[data-action="restart-later"]').addEventListener('click', () => {
            modal.remove();
        });
        
        modal.querySelector('[data-action="restart-now"]').addEventListener('click', async () => {
            await window.__TAURI__.invoke('restart_app');
        });
    }

    formatBytes(bytes) {
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;
        
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        
        return `${size.toFixed(1)} ${units[unitIndex]}`;
    }

    formatReleaseNotes(notes) {
        // Convert markdown to HTML
        return notes
            .replace(/## (.*)/g, '<h5>$1</h5>')
            .replace(/### (.*)/g, '<h6>$1</h6>')
            .replace(/- (.*)/g, '<li>$1</li>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/^/, '<p>')
            .replace(/$/, '</p>')
            .replace(/<li>/g, '<ul><li>')
            .replace(/<\/li>(?!<li>)/g, '</li></ul>');
    }

    // Settings UI
    renderSettingsUI() {
        return `
            <div class="settings-section">
                <h3>Update Settings</h3>
                
                <div class="setting-item">
                    <label class="toggle-switch">
                        <input type="checkbox" id="auto-check" ${this.settings.autoCheck ? 'checked' : ''}>
                        <span class="toggle-slider"></span>
                    </label>
                    <div class="setting-info">
                        <h4>Automatic Update Checks</h4>
                        <p>Check for updates automatically every 6 hours</p>
                    </div>
                </div>
                
                <div class="setting-item">
                    <label class="toggle-switch">
                        <input type="checkbox" id="auto-download" ${this.settings.autoDownload ? 'checked' : ''}>
                        <span class="toggle-slider"></span>
                    </label>
                    <div class="setting-info">
                        <h4>Automatic Downloads</h4>
                        <p>Download updates automatically when available</p>
                    </div>
                </div>
                
                <div class="setting-item">
                    <label class="toggle-switch">
                        <input type="checkbox" id="notifications" ${this.settings.notifications ? 'checked' : ''}>
                        <span class="toggle-slider"></span>
                    </label>
                    <div class="setting-info">
                        <h4>Update Notifications</h4>
                        <p>Show notifications when updates are available</p>
                    </div>
                </div>
                
                <div class="setting-item">
                    <div class="setting-info">
                        <h4>Update Channel</h4>
                        <select id="update-channel" class="form-select">
                            <option value="stable" ${this.settings.channel === 'stable' ? 'selected' : ''}>Stable</option>
                            <option value="beta" ${this.settings.channel === 'beta' ? 'selected' : ''}>Beta</option>
                        </select>
                    </div>
                </div>
                
                <div class="setting-actions">
                    <button class="btn btn-secondary" data-action="check-updates">Check for Updates</button>
                </div>
            </div>
        `;
    }

    attachSettingsListeners(container) {
        container.querySelector('#auto-check').addEventListener('change', (e) => {
            this.settings.autoCheck = e.target.checked;
            this.saveSettings();
            this.startPeriodicChecks();
        });
        
        container.querySelector('#auto-download').addEventListener('change', (e) => {
            this.settings.autoDownload = e.target.checked;
            this.saveSettings();
        });
        
        container.querySelector('#notifications').addEventListener('change', (e) => {
            this.settings.notifications = e.target.checked;
            this.saveSettings();
        });
        
        container.querySelector('#update-channel').addEventListener('change', (e) => {
            this.settings.channel = e.target.value;
            this.saveSettings();
        });
        
        container.querySelector('[data-action="check-updates"]').addEventListener('click', () => {
            this.checkForUpdates(false);
        });
    }
}

// Export for use in main app
window.UpdateManager = UpdateManager;