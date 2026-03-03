/** Global API base URL for vanilla JS modules */
var API_BASE = (function() {
    var port = window.location.port;
    if (port === '9000' || port === '' || port === '80' || port === '443') {
        return window.location.origin;
    }
    return window.location.protocol + '//' + (window.location.hostname || 'localhost') + ':9000';
})();

/** Global auth header helper for vanilla JS modules */
function pbxAuthHeaders() {
    var headers = {'Content-Type': 'application/json'};
    var token = localStorage.getItem('pbx_token');
    if (token) { headers['Authorization'] = 'Bearer ' + token; }
    return headers;
}
