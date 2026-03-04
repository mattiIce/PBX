// Load Chart.js from CDN with automatic fallback to alternative CDNs
(function() {
    var cdns = [
        'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js',
        'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js',
        'https://unpkg.com/chart.js@4.4.0/dist/chart.umd.min.js'
    ];
    var idx = 0;

    function loadNext() {
        if (idx >= cdns.length) {
            console.error('All Chart.js CDN sources failed');
            window.chartJsLoadFailed = true;
            return;
        }

        var script = document.createElement('script');
        script.src = cdns[idx];
        script.onerror = function() {
            debugWarn('Chart.js CDN ' + (idx + 1) + ' failed, trying next...');
            idx++;
            loadNext();
        };
        script.onload = function() {
            debugLog('Chart.js loaded successfully from CDN ' + (idx + 1));
            window.chartJsLoadFailed = false;
        };
        document.head.appendChild(script);
    }

    loadNext();
})();
