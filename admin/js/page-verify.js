// Check if page loaded correctly after 3 seconds
setTimeout(function() {
    // Check if main initialization happened
    if (!window.currentUser && !document.querySelector('.tab-content.active')) {
        console.warn('Page may not have loaded correctly. Checking for common issues...');

        // Check if CSS is loaded
        var sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            var computedStyle = window.getComputedStyle(sidebar);
            if (computedStyle.width === 'auto' || computedStyle.width === '0px') {
                console.error('CSS may not be loaded correctly. Try clearing your browser cache:');
                console.error('  - Press Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)');
                console.error('  - See BROWSER_CACHE_FIX.md for detailed instructions');

                // Show visual alert
                var alertDiv = document.createElement('div');
                alertDiv.className = 'page-load-alert';
                alertDiv.innerHTML =
                    '<strong class="page-load-alert-title">⚠️ Page Loading Issue</strong>' +
                    '<p>The admin panel may not be displaying correctly due to cached files.</p>' +
                    '<p class="page-load-alert-action">' +
                        'Press <code>Ctrl+Shift+R</code> ' +
                        '(or <code>Cmd+Shift+R</code> on Mac) ' +
                        'to reload without cache' +
                    '</p>';

                var dismissBtn = document.createElement('button');
                dismissBtn.className = 'page-load-alert-dismiss';
                dismissBtn.textContent = 'Dismiss';
                dismissBtn.addEventListener('click', function() { alertDiv.remove(); });
                alertDiv.appendChild(dismissBtn);

                document.body.appendChild(alertDiv);
            }
        }
    } else {
        console.log('Page loaded successfully at', new Date().toISOString());
    }
}, 3000);
