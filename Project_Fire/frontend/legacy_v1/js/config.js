/**
 * Agniveer — Global Configuration
 * Dynamically resolves the backend IP based on how the user accesses the dashboard.
 */

window.API_CONFIG = {
    // Automatically use the same hostname as the browser is currently using.
    // This ensures connectivity even if the user accesses via 127.0.0.1, localhost, or a LAN IP (10.60.1.7).
    get baseUrl() {
        const hostname = window.location.hostname || 'localhost';
        return `http://${hostname}:8000/api`;
    }
};

console.log('📡 Agniveer API Bridge Initialized at:', window.API_CONFIG.baseUrl);
