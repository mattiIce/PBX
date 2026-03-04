// Debug logger - only outputs in development (non-standard ports or localhost)
window.__DEV__ = ['localhost', '127.0.0.1'].includes(location.hostname) || !['', '80', '443'].includes(location.port);
window.debugLog = window.__DEV__ ? console.log.bind(console) : function() {};
window.debugWarn = window.__DEV__ ? console.warn.bind(console) : function() {};

// Always track errors regardless of environment
window.addEventListener('error', function(e) {
    console.error('JavaScript Error:', e.error || e.message, '\nFile:', e.filename, '\nLine:', e.lineno);
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled Promise Rejection:', e.reason);
});

debugLog('Admin panel loading...', new Date().toISOString());
