// Display timestamp
document.getElementById('timestamp').textContent = new Date().toLocaleString();

// Display browser info (using textContent for security)
var browserInfo = document.getElementById('browser-info');
var infoLines = [
    'User Agent: ' + navigator.userAgent,
    'Platform: ' + navigator.platform,
    'Language: ' + navigator.language,
    'Screen: ' + window.screen.width + 'x' + window.screen.height,
    'Cookies Enabled: ' + (navigator.cookieEnabled ? 'Yes' : 'No')
];

// Build info display safely (no innerHTML with user-controlled data)
infoLines.forEach(function(line) {
    var parts = line.split(': ');
    var strong = document.createElement('strong');
    strong.textContent = parts[0] + ': ';
    browserInfo.appendChild(strong);
    browserInfo.appendChild(document.createTextNode(parts.slice(1).join(': ')));
    browserInfo.appendChild(document.createElement('br'));
});

// Check if admin files are accessible
var filesToCheck = [
    { url: 'css/admin.css?v=20231223', name: 'CSS File' },
    { url: 'js/main.js', name: 'JavaScript File' }
];

var checksCompleted = 0;
var results = [];

filesToCheck.forEach(function(file) {
    fetch(file.url, { method: 'HEAD' })
        .then(function(response) {
            if (response.ok) {
                results.push({ ok: true, text: file.name + ' (' + file.url + ') - OK' });
            } else {
                results.push({ ok: false, text: file.name + ' (' + file.url + ') - Error ' + response.status });
            }
        })
        .catch(function(error) {
            results.push({ ok: false, text: file.name + ' (' + file.url + ') - Failed to load: ' + error.message });
        })
        .finally(function() {
            checksCompleted++;
            if (checksCompleted === filesToCheck.length) {
                var statusEl = document.getElementById('file-check-status');
                statusEl.textContent = '';
                results.forEach(function(r, i) {
                    var prefix = r.ok ? '\u2713 ' : '\u2717 ';
                    statusEl.appendChild(document.createTextNode(prefix + r.text));
                    if (i < results.length - 1) {
                        statusEl.appendChild(document.createElement('br'));
                    }
                });
            }
        });
});

// Log to console
console.log('PBX Status Check Page loaded successfully');
console.log('Timestamp:', new Date().toISOString());
console.log('If you are seeing errors in the admin panel, clear your browser cache:');
console.log('  - Press Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)');
console.log('  - See BROWSER_CACHE_FIX.md for detailed instructions');
