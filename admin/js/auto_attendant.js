// ============================================================================
// Auto Attendant Management Functions
// ============================================================================

async function loadAutoAttendantConfig() {
    try {
        // Load general configuration
        const configResponse = await fetch(`${API_BASE}/api/auto-attendant/config`);
        if (configResponse.ok) {
            const config = await configResponse.json();

            document.getElementById('aa-enabled').checked = config.enabled ?? false;
            document.getElementById('aa-extension').value = config.extension ?? '0';
            document.getElementById('aa-timeout').value = config.timeout ?? 10;
            document.getElementById('aa-max-retries').value = config.max_retries ?? 3;
        }

        // Load available menus first
        await loadAvailableMenus();

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
        const prompts = data.prompts ?? {};
        const companyName = data.company_name ?? '';

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
        // Load menu items for current menu (default: main)
        const response = await fetch(`${API_BASE}/api/auto-attendant/menus/${currentMenuId}/items`);
        
        // Only fall back to legacy API if endpoint doesn't exist (404)
        if (response.status === 404) {
            console.warn(`Menu items endpoint returned 404 for menu '${currentMenuId}', trying legacy API...`);
            return await loadLegacyMenuOptions();
        }
        
        if (!response.ok) {
            const errorData = await parseErrorResponse(response);
            throw new Error(`Failed to load menu options: ${response.status} - ${errorData.error || response.statusText}`);
        }

        const data = await response.json();
        const tbody = document.getElementById('aa-menu-options-table-body');

        // Update breadcrumb
        updateMenuBreadcrumb();

        if (!data.items || data.items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="no-data">No menu options configured. Click "Add Menu Option" to get started.</td></tr>';
            return;
        }

        // Sort by digit for consistent display
        const sortedOptions = data.items.sort((a, b) => {
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

            // Digit column
            const digitCell = document.createElement('td');
            digitCell.innerHTML = `<strong>${escapeHtml(option.digit)}</strong>`;
            row.appendChild(digitCell);

            // Type column with icon
            const typeCell = document.createElement('td');
            const typeIcon = getDestinationTypeIcon(option.destination_type);
            typeCell.innerHTML = `${typeIcon} ${option.destination_type}`;
            row.appendChild(typeCell);

            // Destination column
            const destCell = document.createElement('td');
            if (option.destination_type === 'submenu') {
                destCell.innerHTML = `<span style="color: #4CAF50; font-weight: bold;">${escapeHtml(option.destination_value)}</span>`;
            } else {
                destCell.textContent = option.destination_value;
            }
            row.appendChild(destCell);

            // Description column
            const descCell = document.createElement('td');
            descCell.textContent = option.description;
            row.appendChild(descCell);

            // Actions column
            const actionsCell = document.createElement('td');
            
            // Navigate button for submenus
            if (option.destination_type === 'submenu') {
                const navBtn = document.createElement('button');
                navBtn.className = 'btn btn-secondary';
                navBtn.textContent = '➡️ Open';
                navBtn.onclick = () => navigateToMenu(option.destination_value);
                actionsCell.appendChild(navBtn);
            }
            
            const editBtn = document.createElement('button');
            editBtn.className = 'btn btn-primary';
            editBtn.textContent = '✏️ Edit';
            editBtn.onclick = () => editMenuOption(option.digit, option.destination_type, option.destination_value, option.description);
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

// Load legacy menu options (backward compatibility)
async function loadLegacyMenuOptions() {
    try {
        const response = await fetch(`${API_BASE}/api/auto-attendant/menu-options`);
        if (!response.ok) {
            throw new Error('Failed to load menu options');
        }

        const data = await response.json();
        const tbody = document.getElementById('aa-menu-options-table-body');

        if (!data.menu_options || data.menu_options.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="no-data">No menu options configured.</td></tr>';
            return;
        }

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

            const typeCell = document.createElement('td');
            typeCell.innerHTML = '📞 extension';
            row.appendChild(typeCell);

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
            editBtn.onclick = () => editMenuOption(option.digit, 'extension', option.destination, option.description);
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
        console.error('Error loading legacy menu options:', error);
        throw error;
    }
}

// Get icon for destination type
function getDestinationTypeIcon(type) {
    const icons = {
        'extension': '📞',
        'submenu': '📁',
        'queue': '👥',
        'voicemail': '📧',
        'operator': '🎧'
    };
    return icons[type] || '❓';
}

// Navigate to a different menu
async function navigateToMenu(menuId) {
    currentMenuId = menuId;
    await loadAutoAttendantMenuOptions();
}

// Update breadcrumb display
async function updateMenuBreadcrumb() {
    try {
        const response = await fetch(`${API_BASE}/api/auto-attendant/menus/${currentMenuId}`);
        if (response.ok) {
            const data = await response.json();
            const breadcrumb = document.getElementById('breadcrumb-path');
            if (breadcrumb) {
                let path = data.menu.menu_name;
                
                // Build breadcrumb path
                if (currentMenuId !== 'main') {
                    // Add back button
                    path = `<button class="btn btn-secondary" onclick="navigateToMenu('main')" style="margin-right: 10px;">⬅️ Back to Main</button> ${path}`;
                }
                
                breadcrumb.innerHTML = path;
            }
        }
    } catch (error) {
        console.error('Error updating breadcrumb:', error);
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

function editMenuOption(digit, destination_type, destination_value, description) {
    document.getElementById('edit-menu-digit').value = digit;
    document.getElementById('edit-menu-digit-display').textContent = digit;
    document.getElementById('edit-menu-dest-type').value = destination_type || 'extension';
    document.getElementById('edit-menu-description').value = description;
    
    // Update field visibility based on type
    updateDestinationFieldVisibility('edit');
    
    // Set the appropriate destination field
    if (destination_type === 'submenu') {
        document.getElementById('edit-menu-submenu').value = destination_value;
    } else {
        document.getElementById('edit-menu-destination').value = destination_value;
    }
    
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
        const response = await fetch(`${API_BASE}/api/auto-attendant/menus/${currentMenuId}/items/${digit}`, {
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

            const destType = document.getElementById('new-menu-dest-type').value;
            let destValue;
            
            if (destType === 'submenu') {
                destValue = document.getElementById('new-menu-submenu').value;
            } else {
                destValue = document.getElementById('new-menu-destination').value;
            }

            const menuData = {
                digit: document.getElementById('new-menu-digit').value,
                destination_type: destType,
                destination_value: destValue,
                description: document.getElementById('new-menu-description').value
            };

            try {
                const response = await fetch(`${API_BASE}/api/auto-attendant/menus/${currentMenuId}/items`, {
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
            const destType = document.getElementById('edit-menu-dest-type').value;
            let destValue;
            
            if (destType === 'submenu') {
                destValue = document.getElementById('edit-menu-submenu').value;
            } else {
                destValue = document.getElementById('edit-menu-destination').value;
            }

            const menuData = {
                destination_type: destType,
                destination_value: destValue,
                description: document.getElementById('edit-menu-description').value
            };

            try {
                const response = await fetch(`${API_BASE}/api/auto-attendant/menus/${currentMenuId}/items/${digit}`, {
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

// ============================================================================
// Submenu Management Functions
// ============================================================================

let currentMenuId = 'main';  // Track current menu being viewed
let availableMenus = [];  // Cache of available menus

// Helper function to safely parse error response JSON
async function parseErrorResponse(response) {
    try {
        const data = await response.json();
        return data;
    } catch (error) {
        // If reading/parsing the response fails, try to classify the error using
        // its type first, and only then fall back to best-effort message checks.
        const errorMsg = error?.message || String(error);

        // JSON parsing error - response likely not in JSON format
        if (error instanceof SyntaxError || /JSON|Unexpected token/i.test(errorMsg)) {
            return { error: 'Server returned an invalid response format' };
        }

        // Network-related or stream-related error typically surfaced as TypeError by fetch
        if (error instanceof TypeError || /network|NetworkError|fetch/i.test(errorMsg)) {
            return { error: 'Network error while reading server response' };
        }

        // Generic fallback if we cannot determine a more specific cause.
        // This is a best-effort categorization when no reliable type information is available.
        console.warn('Unexpected error parsing response:', error);
        return { error: 'Unable to read server response' };
    }
}

// Load all menus for submenu selection
async function loadAvailableMenus() {
    try {
        const response = await fetch(`${API_BASE}/api/auto-attendant/menus`);
        if (response.ok) {
            const data = await response.json();
            availableMenus = data.menus || [];
            console.log(`Loaded ${availableMenus.length} menu(s) for submenu selection`);
            return availableMenus;
        } else {
            const errorData = await parseErrorResponse(response);
            console.error(`Failed to load menus: ${response.status} ${response.statusText}`, errorData);
            // Provide context-specific error message based on status code
            let errorMsg = errorData.error || response.statusText;
            if (response.status === 404) {
                errorMsg += '. API endpoint not found - check server version.';
            } else if (response.status >= 500) {
                errorMsg += '. Server error occurred.';
            }
            showNotification(`Failed to load menus: ${errorMsg}`, 'error');
        }
    } catch (error) {
        console.error('Error loading menus:', error);
        showNotification(`Unable to connect to API: ${error.message}. Please check your connection.`, 'error');
    }
    return [];
}

// Update submenu dropdowns
async function updateSubmenuDropdowns() {
    const menus = await loadAvailableMenus();
    
    // Update add modal submenu dropdown
    const newSubmenuSelect = document.getElementById('new-menu-submenu');
    if (newSubmenuSelect) {
        newSubmenuSelect.innerHTML = '<option value="">Select a submenu</option>';
        if (menus.length === 0) {
            const noMenusOption = document.createElement('option');
            noMenusOption.value = '';
            noMenusOption.textContent = 'No menus available - create one first';
            noMenusOption.disabled = true;
            newSubmenuSelect.appendChild(noMenusOption);
            newSubmenuSelect.disabled = true;
        } else {
            menus.forEach(menu => {
                if (menu.menu_id !== currentMenuId) {  // Don't include current menu
                    const option = document.createElement('option');
                    option.value = menu.menu_id;
                    option.textContent = `${menu.menu_name} (${menu.menu_id})`;
                    newSubmenuSelect.appendChild(option);
                }
            });
            newSubmenuSelect.disabled = false;
        }
    }
    
    // Update edit modal submenu dropdown
    const editSubmenuSelect = document.getElementById('edit-menu-submenu');
    if (editSubmenuSelect) {
        editSubmenuSelect.innerHTML = '<option value="">Select a submenu</option>';
        if (menus.length === 0) {
            const noMenusOption = document.createElement('option');
            noMenusOption.value = '';
            noMenusOption.textContent = 'No menus available - create one first';
            noMenusOption.disabled = true;
            editSubmenuSelect.appendChild(noMenusOption);
            editSubmenuSelect.disabled = true;
        } else {
            menus.forEach(menu => {
                if (menu.menu_id !== currentMenuId) {
                    const option = document.createElement('option');
                    option.value = menu.menu_id;
                    option.textContent = `${menu.menu_name} (${menu.menu_id})`;
                    editSubmenuSelect.appendChild(option);
                }
            });
            editSubmenuSelect.disabled = false;
        }
    }
    
    // Update parent menu dropdown in create submenu modal
    const parentSelect = document.getElementById('submenu-parent');
    if (parentSelect) {
        parentSelect.innerHTML = '';
        if (menus.length === 0) {
            const noMenusOption = document.createElement('option');
            noMenusOption.value = '';
            noMenusOption.textContent = 'No parent menus available - check API connection or server status';
            noMenusOption.disabled = true;
            noMenusOption.selected = true;
            parentSelect.appendChild(noMenusOption);
            console.warn('No menus loaded for parent dropdown');
        } else {
            menus.forEach(menu => {
                const option = document.createElement('option');
                option.value = menu.menu_id;
                option.textContent = `${menu.menu_name} (${menu.menu_id})`;
                if (menu.menu_id === 'main') {
                    option.selected = true;
                }
                parentSelect.appendChild(option);
            });
            console.log(`Populated parent menu dropdown with ${menus.length} menu(s)`);
        }
    }
}

// Update destination field visibility based on type selection
function updateDestinationFieldVisibility(prefix) {
    const typeSelect = document.getElementById(`${prefix}-menu-dest-type`);
    const extensionGroup = document.getElementById(`${prefix}-dest-extension-group`);
    const submenuGroup = document.getElementById(`${prefix}-dest-submenu-group`);
    const destInput = document.getElementById(`${prefix}-menu-destination`);
    const submenuSelect = document.getElementById(`${prefix}-menu-submenu`);
    const destLabel = document.getElementById(`${prefix}-dest-label`);
    const destHelp = document.getElementById(`${prefix}-dest-help`);
    
    if (!typeSelect) return;
    
    const selectedType = typeSelect.value;
    
    if (selectedType === 'submenu') {
        // Show submenu selector, hide extension input
        if (extensionGroup) extensionGroup.style.display = 'none';
        if (submenuGroup) submenuGroup.style.display = 'block';
        if (destInput) destInput.required = false;
        if (submenuSelect) submenuSelect.required = true;
        updateSubmenuDropdowns();
    } else {
        // Show extension input, hide submenu selector
        if (extensionGroup) extensionGroup.style.display = 'block';
        if (submenuGroup) submenuGroup.style.display = 'none';
        if (destInput) destInput.required = true;
        if (submenuSelect) submenuSelect.required = false;
        
        // Update label and help text based on type
        if (destLabel) {
            switch (selectedType) {
                case 'extension':
                    destLabel.textContent = 'Extension';
                    if (destHelp) destHelp.textContent = 'Extension number to transfer to';
                    break;
                case 'queue':
                    destLabel.textContent = 'Queue';
                    if (destHelp) destHelp.textContent = 'Queue extension number';
                    break;
                case 'voicemail':
                    destLabel.textContent = 'Voicemail Box';
                    if (destHelp) destHelp.textContent = 'Voicemail box extension';
                    break;
                case 'operator':
                    destLabel.textContent = 'Operator Extension';
                    if (destHelp) destHelp.textContent = 'Operator extension number';
                    break;
            }
        }
    }
}

// Show create submenu modal
function showCreateSubmenuModal() {
    updateSubmenuDropdowns();
    document.getElementById('create-submenu-modal').classList.add('active');
    document.getElementById('create-submenu-form').reset();
}

// Close create submenu modal
function closeCreateSubmenuModal() {
    document.getElementById('create-submenu-modal').classList.remove('active');
}

// Toggle menu tree view
async function toggleMenuTreeView() {
    const container = document.getElementById('menu-tree-container');
    if (container.style.display === 'none') {
        container.style.display = 'block';
        await loadMenuTree();
    } else {
        container.style.display = 'none';
    }
}

// Load and display menu tree
async function loadMenuTree() {
    try {
        const response = await fetch(`${API_BASE}/api/auto-attendant/menu-tree`);
        if (!response.ok) {
            const errorData = await parseErrorResponse(response);
            console.error(`Failed to load menu tree: ${response.status} ${response.statusText}`, errorData);
            
            // Provide helpful error message based on status code
            if (response.status === 404) {
                throw new Error('Menu tree endpoint not found. The server may need to be restarted to load new API routes.');
            } else if (response.status === 500) {
                throw new Error(`Server error: ${errorData.error || 'Internal server error'}`);
            } else {
                throw new Error(`Failed to load menu tree: ${errorData.error || response.statusText}`);
            }
        }
        
        const data = await response.json();
        const treeView = document.getElementById('menu-tree-view');
        
        if (data.menu_tree) {
            treeView.innerHTML = renderMenuTree(data.menu_tree, 0);
            console.log('Menu tree loaded successfully');
        } else {
            treeView.innerHTML = '<p style="color: #666;">No menu structure available</p>';
            console.warn('Menu tree data is empty');
        }
    } catch (error) {
        console.error('Error loading menu tree:', error);
        showNotification(`Failed to load menu tree: ${error.message}`, 'error');
        
        const treeView = document.getElementById('menu-tree-view');
        if (treeView) {
            treeView.innerHTML = `<p class="error-message">
                <strong>Error:</strong> ${error.message}<br>
                <small>Check the browser console for more details.</small>
            </p>`;
        }
    }
}

// Render menu tree recursively
function renderMenuTree(menu, level) {
    const indent = '  '.repeat(level);
    let html = `<div style="margin-left: ${level * 20}px; margin-top: 5px;">`;
    html += `<strong>${escapeHtml(menu.menu_name || menu.menu_id)}</strong>`;
    
    if (menu.items && menu.items.length > 0) {
        menu.items.forEach(item => {
            html += `<div style="margin-left: ${(level + 1) * 20}px; margin-top: 3px;">`;
            html += `📌 ${escapeHtml(item.digit)}: ${escapeHtml(item.description || 'No description')} `;
            
            if (item.destination_type === 'submenu' && item.submenu) {
                html += `<span style="color: #4CAF50;">[Submenu]</span>`;
                html += '</div>';
                html += renderMenuTree(item.submenu, level + 2);
            } else {
                html += `<span style="color: #666;">(${escapeHtml(item.destination_type)}: ${escapeHtml(item.destination_value)})</span>`;
                html += '</div>';
            }
        });
    }
    
    html += '</div>';
    return html;
}

// Initialize create submenu form
document.addEventListener('DOMContentLoaded', function() {
    const createSubmenuForm = document.getElementById('create-submenu-form');
    if (createSubmenuForm) {
        createSubmenuForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const submenuData = {
                menu_id: document.getElementById('submenu-id').value,
                parent_menu_id: document.getElementById('submenu-parent').value,
                menu_name: document.getElementById('submenu-name').value,
                prompt_text: document.getElementById('submenu-prompt').value
            };
            
            try {
                const response = await fetch(`${API_BASE}/api/auto-attendant/menus`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(submenuData)
                });
                
                if (response.ok) {
                    showNotification('Submenu created successfully and voice generated!', 'success');
                    closeCreateSubmenuModal();
                    await loadAvailableMenus();  // Refresh menu list
                    await loadAutoAttendantMenuOptions();  // Refresh display
                } else {
                    const error = await response.json();
                    showNotification(error.error || 'Failed to create submenu', 'error');
                }
            } catch (error) {
                console.error('Error creating submenu:', error);
                showNotification('Failed to create submenu', 'error');
            }
        });
    }
});
