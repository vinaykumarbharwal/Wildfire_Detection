/**
 * Firebase Configuration - Agniveer Tactical Command
 * 
 * Uses the Firebase web app configuration for wildfirewatch-8f5b7.
 * This legacy frontend loads Firebase via browser-compatible compat scripts,
 * so the app config is initialized without ES module imports here.
 */
const firebaseConfig = {
    apiKey: "AIzaSyBzuEycFugC88d1MIAUt-zQI9jq-l5uWvI",
    authDomain: "wildfirewatch-8f5b7.firebaseapp.com",
    projectId: "wildfirewatch-8f5b7",
    storageBucket: "wildfirewatch-8f5b7.firebasestorage.app",
    messagingSenderId: "35072394077",
    appId: "1:35072394077:web:e892fdfd9b2ab10ae61eb4"
};

/**
 * Initialize Firebase with a failsafe return for polling fallback
 */
async function initializeFirebase() {
    try {
        if (typeof firebase === 'undefined') return false;
        
        // Failsafe: Check if placeholders are still present
        if (!firebaseConfig.apiKey || firebaseConfig.apiKey.includes('YOUR_API_KEY')) {
            console.warn('⚠️ Firebase API Key missing. Dashboard will use Tactical Polling fallback.');
            return false;
        }

        if (!firebase.apps.length) {
            firebase.initializeApp(firebaseConfig);
        }
        return true;
    } catch (error) {
        console.error('Firebase Initialization Error:', error);
        return false;
    }
}