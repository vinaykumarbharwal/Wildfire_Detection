/**
 * Agniveer — Global Configuration
 * Resolves backend URL from .env (FRONTEND_BACKEND_URL) with local-host fallback.
 */

function parseEnvValue(envText, key) {
    const envLine = envText
        .split('\n')
        .map(line => line.trim())
        .find(line => line.startsWith(`${key}=`));
    if (!envLine) return null;
    return envLine.slice(key.length + 1).trim().replace(/^['"]|['"]$/g, '');
}

window.API_CONFIG = {
    envKey: 'FRONTEND_BACKEND_URL',
    resolvedBaseUrl: null,

    ready: (async function loadBackendFromEnv() {
        try {
            const response = await fetch('.env', { cache: 'no-store' });
            if (response.ok) {
                const envText = await response.text();
                const envUrl = parseEnvValue(envText, 'FRONTEND_BACKEND_URL');
                if (envUrl) {
                    window.API_CONFIG.resolvedBaseUrl = envUrl;
                    return;
                }
            }
        } catch (_) {
            // Fall through to hostname fallback.
        }

        const hostname = window.location.hostname || 'localhost';
        window.API_CONFIG.resolvedBaseUrl = `http://${hostname}:8000/api`;
    })(),

    get baseUrl() {
        if (this.resolvedBaseUrl) return this.resolvedBaseUrl;
        const hostname = window.location.hostname || 'localhost';
        return `http://${hostname}:8000/api`;
    },

    async getBaseUrl() {
        await this.ready;
        return this.baseUrl;
    },
};

window.API_CONFIG.ready.then(() => {
    console.log('📡 Agniveer API Bridge Initialized at:', window.API_CONFIG.baseUrl);
});
