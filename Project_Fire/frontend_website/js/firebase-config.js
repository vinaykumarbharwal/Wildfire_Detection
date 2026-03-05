async function initializeFirebase() {
    const firebaseConfig = {
        apiKey: "YOUR_API_KEY",
        authDomain: "your-project.firebaseapp.com",
        projectId: "your-project",
        storageBucket: "your-project.appspot.com",
        messagingSenderId: "123456789",
        appId: "YOUR_APP_ID"
    };

    try {
        firebase.initializeApp(firebaseConfig);
        console.log('✅ Firebase initialized');
        return true;
    } catch (error) {
        console.error('❌ Firebase initialization failed:', error);
        return false;
    }
}