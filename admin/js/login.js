// Debug logger - only outputs in development
window.__DEV__ = ['localhost', '127.0.0.1'].includes(location.hostname) || !['', '80', '443'].includes(location.port);
window.debugLog = window.__DEV__ ? console.log.bind(console) : function() {};
window.debugWarn = window.__DEV__ ? console.warn.bind(console) : function() {};

// Constants for API endpoint detection
var STANDARD_HTTP_PORT = '80';
var STANDARD_HTTPS_PORT = '443';
var API_PORT = '9000';

// API Base URL - auto-detect or use configured value
function getAPIBase() {
    // Check for meta tag override first
    var apiMeta = document.querySelector('meta[name="api-base-url"]');
    if (apiMeta && apiMeta.content) {
        debugLog('Using API base URL from meta tag:', apiMeta.content);
        return apiMeta.content;
    }

    // If we're on the API port, use current origin
    if (window.location.port === API_PORT) {
        debugLog('Detected API port in URL, using current origin');
        return window.location.origin;
    }

    // If accessed through reverse proxy or standard HTTP/HTTPS ports,
    // try same origin first (API should be proxied)
    if (window.location.port === '' ||
        window.location.port === STANDARD_HTTP_PORT ||
        window.location.port === STANDARD_HTTPS_PORT) {
        debugLog('Accessed via standard port, will try same origin (reverse proxy)');
        return window.location.origin;
    }

    // Fallback: use current hostname with API port (direct API access)
    var protocol = window.location.protocol;
    var hostname = window.location.hostname || 'localhost';
    var apiBase = protocol + '//' + hostname + ':' + API_PORT;
    debugLog('Using direct API access:', apiBase);
    debugLog('Current location:', window.location.href);
    return apiBase;
}

var API_BASE = getAPIBase();
debugLog('Final API Base URL:', API_BASE);

// Test API connectivity on page load
async function testAPIConnection() {
    try {
        debugLog('Testing API connectivity...');
        var response = await fetch(API_BASE + '/api/status', {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (response.ok) {
            debugLog('API server is reachable');
        } else {
            debugWarn('API server responded with status:', response.status);
            showTroubleshooting('API server responded with status ' + response.status + '. The PBX may be starting up.');
        }
    } catch (error) {
        console.error('Cannot reach API server:', error);
        debugLog('Please verify: PBX server is running, API on port 9000, no firewall blocking, hostname resolves correctly');

        showTroubleshooting(
            'Cannot reach API server at ' + window.location.hostname + ':9000\n' +
            'Please check:\n' +
            '• PBX server is running\n' +
            '• Port 9000 is not blocked by firewall\n' +
            '• Console (F12) for detailed error logs'
        );
    }
}

function showTroubleshooting(message) {
    var troubleshooting = document.getElementById('troubleshooting');
    var details = document.getElementById('troubleshooting-details');

    // Use textContent for security (no HTML injection)
    details.textContent = message;
    troubleshooting.style.display = 'block';
}

// Run API test after a short delay to let the page load
setTimeout(testAPIConnection, 500);

var loginForm = document.getElementById('login-form');
var loginButton = document.getElementById('login-button');
var errorMessage = document.getElementById('error-message');
var extensionInput = document.getElementById('extension');
var passwordInput = document.getElementById('password');

loginForm.addEventListener('submit', async function(e) {
    e.preventDefault();

    var extension = extensionInput.value.trim();
    var password = passwordInput.value;

    if (!extension || !password) {
        showError('Please enter both extension and password');
        return;
    }

    // Show loading state
    loginButton.disabled = true;
    loginButton.classList.add('loading');
    hideError();

    try {
        var response = await fetch(API_BASE + '/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                extension: extension,
                password: password
            })
        });

        // Check if response is JSON before parsing
        var contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            debugWarn('Invalid response type:', contentType, 'status:', response.status);
            throw new Error('Server returned invalid response. Please check if the PBX API server is running on port 9000.');
        }

        var data = await response.json();

        if (response.ok && data.success) {
            // Store authentication data
            localStorage.setItem('pbx_token', data.token);
            localStorage.setItem('pbx_extension', data.extension);
            localStorage.setItem('pbx_is_admin', data.is_admin.toString());
            localStorage.setItem('pbx_name', data.name || 'User');

            // Redirect to admin panel
            window.location.href = '/admin/index.html';
        } else {
            showError(data.error || 'Invalid credentials');
            loginButton.disabled = false;
            loginButton.classList.remove('loading');
        }
    } catch (error) {
        console.error('Login error:', error);

        // Provide more specific error messages (without exposing sensitive data)
        var errorMsg = 'Connection error. ';
        if (error.message && error.message.includes('PBX API server')) {
            // Use a safe, predefined message
            errorMsg = 'Server returned invalid response. Please check if the PBX API server is running on port 9000.';
        } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
            errorMsg += 'Cannot reach API server. Please verify the server is running.';
        } else if (error.name === 'SyntaxError') {
            errorMsg += 'Server returned invalid data. Please contact your administrator.';
        } else {
            errorMsg += 'Please try again or contact your administrator.';
        }

        showError(errorMsg);
        loginButton.disabled = false;
        loginButton.classList.remove('loading');
    }
});

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.add('show');
}

function hideError() {
    errorMessage.classList.remove('show');
}

// Password visibility toggle
var passwordToggle = document.getElementById('password-toggle');
passwordToggle.addEventListener('click', function() {
    var isPassword = passwordInput.type === 'password';
    passwordInput.type = isPassword ? 'text' : 'password';
    passwordToggle.textContent = isPassword ? '🔒' : '👁';
    passwordToggle.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
});

// Remember Me: save/restore extension from localStorage
var rememberMe = document.getElementById('remember-me');
var savedExtension = localStorage.getItem('pbx_remembered_extension');
if (savedExtension) {
    extensionInput.value = savedExtension;
    rememberMe.checked = true;
}

// Save on successful login
loginForm.addEventListener('submit', function() {
    if (rememberMe.checked) {
        localStorage.setItem('pbx_remembered_extension', extensionInput.value.trim());
    } else {
        localStorage.removeItem('pbx_remembered_extension');
    }
}, true);

// Forgot password handler
var forgotLink = document.getElementById('forgot-password-link');
forgotLink.addEventListener('click', function(e) {
    e.preventDefault();
    alert('Please contact your system administrator to reset your password.');
});

// Auto-focus: if extension pre-filled, focus password instead
if (savedExtension) {
    passwordInput.focus();
} else {
    extensionInput.focus();
}
