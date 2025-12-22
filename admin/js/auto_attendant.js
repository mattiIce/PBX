// ============================================================================
// Auto Attendant Management Functions
// ============================================================================

async function loadAutoAttendantConfig() {
    try {
        // Load general configuration
        const configResponse = await fetch(`${API_BASE}/api/auto-attendant/config`);
        if (configResponse.ok) {
            const config = await configResponse.json();

            document.getElementById('aa-enabled').checked = config.enabled || false;
            document.getElementById('aa-extension').value = config.extension || '0';
            document.getElementById('aa-timeout').value = config.timeout || 10;
            document.getElementById('aa-max-retries').value = config.max_retries || 3;
        }

        // Load menu options
        await loadAutoAttendantMenuOptions();

        // Load prompts
        await loadAutoAttendantPrompts();
    } catch (error) {
        console.error('Error loading auto attendant config:', error);
        showNotification('Failed to load auto attendant configuration', 'error');
    }
}

async function loadAutoAttendantPrompts() {
    try {
        const response = await fetch(`${API_BASE}/api/auto-attendant/prompts`);
        if (!response.ok) {
            console.warn('Failed to load prompts, using defaults');
            return;
        }

        const data = await response.json();
        const prompts = data.prompts || {};
        const companyName = data.company_name || '';

        // Set company name
        const companyNameField = document.getElementById('aa-company-name');
        if (companyNameField) {
            companyNameField.value = companyName;
        }

        // Set prompt texts
        if (prompts.welcome) {
            document.getElementById('aa-prompt-welcome').value = prompts.welcome;
        }
        if (prompts.main_menu) {
            document.getElementById('aa-prompt-main-menu').value = prompts.main_menu;
        }
        if (prompts.invalid) {
            document.getElementById('aa-prompt-invalid').value = prompts.invalid;
        }
        if (prompts.timeout) {
            document.getElementById('aa-prompt-timeout').value = prompts.timeout;
        }
        if (prompts.transferring) {
            document.getElementById('aa-prompt-transferring').value = prompts.transferring;
        }
    } catch (error) {
        console.error('Error loading prompts:', error);
    }
}

async function loadAutoAttendantMenuOptions() {
    try {
        const response = await fetch(`${API_BASE}/api/auto-attendant/menu-options`);
        if (!response.ok) {
            throw new Error('Failed to load menu options');
        }

        const data = await response.json();
        const tbody = document.getElementById('aa-menu-options-table-body');

        if (!data.menu_options || data.menu_options.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="no-data">No menu options configured. Click "Add Menu Option" to get started.</td></tr>';
            return;
        }

        // Sort by digit for consistent display
        const sortedOptions = data.menu_options.sort((a, b) => {
            if (a.digit === b.digit) return 0;
            if (a.digit === '*') return 1;
            if (b.digit === '*') return -1;
            if (a.digit === '#') return 1;
            if (b.digit === '#') return -1;
            return a.digit.localeCompare(b.digit);
        });

        tbody.innerHTML = '';
        sortedOptions.forEach(option => {
            const row = document.createElement('tr');

            const digitCell = document.createElement('td');
            digitCell.innerHTML = `<strong>${escapeHtml(option.digit)}</strong>`;
            row.appendChild(digitCell);

            const destCell = document.createElement('td');
            destCell.textContent = option.destination;
            row.appendChild(destCell);

            const descCell = document.createElement('td');
            descCell.textContent = option.description;
            row.appendChild(descCell);

            const actionsCell = document.createElement('td');
            const editBtn = document.createElement('button');
            editBtn.className = 'btn btn-primary';
            editBtn.textContent = '✏️ Edit';
            editBtn.onclick = () => editMenuOption(option.digit, option.destination, option.description);
            actionsCell.appendChild(editBtn);

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn btn-danger';
            deleteBtn.textContent = '🗑️ Delete';
            deleteBtn.onclick = () => deleteMenuOption(option.digit);
            actionsCell.appendChild(deleteBtn);

            row.appendChild(actionsCell);
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading menu options:', error);
        showNotification('Failed to load menu options', 'error');
    }
}

// Initialize auto attendant config form
document.addEventListener('DOMContentLoaded', function() {
    const aaConfigForm = document.getElementById('auto-attendant-config-form');
    if (aaConfigForm) {
        aaConfigForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const configData = {
                enabled: document.getElementById('aa-enabled').checked,
                extension: document.getElementById('aa-extension').value,
                timeout: parseInt(document.getElementById('aa-timeout').value, 10),
                max_retries: parseInt(document.getElementById('aa-max-retries').value, 10)
            };

            try {
                const response = await fetch(`${API_BASE}/api/auto-attendant/config`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(configData)
                });

                if (response.ok) {
                    showNotification('Auto attendant configuration saved successfully', 'success');
                } else {
                    const error = await response.json();
                    showNotification(error.error || 'Failed to save configuration', 'error');
                }
            } catch (error) {
                console.error('Error saving auto attendant config:', error);
                showNotification('Failed to save configuration', 'error');
            }
        });
    }
});

function showAddMenuOptionModal() {
    document.getElementById('add-menu-option-modal').classList.add('active');
    document.getElementById('add-menu-option-form').reset();
}

function closeAddMenuOptionModal() {
    document.getElementById('add-menu-option-modal').classList.remove('active');
}

function editMenuOption(digit, destination, description) {
    document.getElementById('edit-menu-digit').value = digit;
    document.getElementById('edit-menu-digit-display').textContent = digit;
    document.getElementById('edit-menu-destination').value = destination;
    document.getElementById('edit-menu-description').value = description;
    document.getElementById('edit-menu-option-modal').classList.add('active');
}

function closeEditMenuOptionModal() {
    document.getElementById('edit-menu-option-modal').classList.remove('active');
}

async function deleteMenuOption(digit) {
    if (!confirm(`Are you sure you want to delete menu option for digit "${digit}"?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/auto-attendant/menu-options/${digit}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showNotification('Menu option deleted successfully', 'success');
            loadAutoAttendantMenuOptions();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to delete menu option', 'error');
        }
    } catch (error) {
        console.error('Error deleting menu option:', error);
        showNotification('Failed to delete menu option', 'error');
    }
}

// Initialize add menu option form
document.addEventListener('DOMContentLoaded', function() {
    const addMenuForm = document.getElementById('add-menu-option-form');
    if (addMenuForm) {
        addMenuForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const menuData = {
                digit: document.getElementById('new-menu-digit').value,
                destination: document.getElementById('new-menu-destination').value,
                description: document.getElementById('new-menu-description').value
            };

            try {
                const response = await fetch(`${API_BASE}/api/auto-attendant/menu-options`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(menuData)
                });

                if (response.ok) {
                    showNotification('Menu option added successfully', 'success');
                    closeAddMenuOptionModal();
                    loadAutoAttendantMenuOptions();
                } else {
                    const error = await response.json();
                    showNotification(error.error || 'Failed to add menu option', 'error');
                }
            } catch (error) {
                console.error('Error adding menu option:', error);
                showNotification('Failed to add menu option', 'error');
            }
        });
    }
});

// Initialize edit menu option form
document.addEventListener('DOMContentLoaded', function() {
    const editMenuForm = document.getElementById('edit-menu-option-form');
    if (editMenuForm) {
        editMenuForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const digit = document.getElementById('edit-menu-digit').value;
            const menuData = {
                destination: document.getElementById('edit-menu-destination').value,
                description: document.getElementById('edit-menu-description').value
            };

            try {
                const response = await fetch(`${API_BASE}/api/auto-attendant/menu-options/${digit}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(menuData)
                });

                if (response.ok) {
                    showNotification('Menu option updated successfully', 'success');
                    closeEditMenuOptionModal();
                    loadAutoAttendantMenuOptions();
                } else {
                    const error = await response.json();
                    showNotification(error.error || 'Failed to update menu option', 'error');
                }
            } catch (error) {
                console.error('Error updating menu option:', error);
                showNotification('Failed to update menu option', 'error');
            }
        });
    }
});

// Initialize prompts form
document.addEventListener('DOMContentLoaded', function() {
    const promptsForm = document.getElementById('auto-attendant-prompts-form');
    if (promptsForm) {
        promptsForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const statusDiv = document.getElementById('voice-generation-status');
            const statusMessage = document.getElementById('voice-generation-message');

            // Show status
            if (statusDiv) {
                statusDiv.style.display = 'block';
                statusMessage.textContent = '⏳ Saving prompts and regenerating voices using gTTS...';
            }

            const promptsData = {
                company_name: document.getElementById('aa-company-name').value,
                prompts: {
                    welcome: document.getElementById('aa-prompt-welcome').value,
                    main_menu: document.getElementById('aa-prompt-main-menu').value,
                    invalid: document.getElementById('aa-prompt-invalid').value,
                    timeout: document.getElementById('aa-prompt-timeout').value,
                    transferring: document.getElementById('aa-prompt-transferring').value
                }
            };

            try {
                const response = await fetch(`${API_BASE}/api/auto-attendant/prompts`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(promptsData)
                });

                if (response.ok) {
                    showNotification('Prompts saved and voices regenerated successfully!', 'success');
                    if (statusDiv) {
                        statusMessage.textContent = '✅ Voice prompts regenerated successfully using gTTS!';
                        setTimeout(() => {
                            statusDiv.style.display = 'none';
                        }, 3000);
                    }
                } else {
                    const error = await response.json();
                    showNotification(error.error || 'Failed to save prompts', 'error');
                    if (statusDiv) {
                        statusMessage.textContent = '❌ Failed to regenerate voices';
                        setTimeout(() => {
                            statusDiv.style.display = 'none';
                        }, 3000);
                    }
                }
            } catch (error) {
                console.error('Error saving prompts:', error);
                showNotification('Failed to save prompts', 'error');
                if (statusDiv) {
                    statusMessage.textContent = '❌ Error: ' + error.message;
                    setTimeout(() => {
                        statusDiv.style.display = 'none';
                    }, 3000);
                }
            }
        });
    }
});

// Helper function to escape HTML (already in admin.js but included here for completeness)
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
