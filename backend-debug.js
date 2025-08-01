// 🔍 Clean Backend Debug Script
// Copy this to browser console for debugging

console.log('🔍 Backend Debug Script Starting...');

// Your production URL - update this
const BASE_URL = 'https://gui-backend-eab8.onrender.com';

async function debugBackend() {
    console.log('🏥 Health Check...');
    try {
        const response = await fetch(`${BASE_URL}/api/health/`);
        const data = await response.json();
        console.log('✅ Health:', data);
    } catch (error) {
        console.error('❌ Health failed:', error);
    }

    console.log('🏠 Home Endpoint...');
    try {
        const response = await fetch(`${BASE_URL}/api/`);
        const data = await response.json();
        console.log('✅ Home:', data);
    } catch (error) {
        console.error('❌ Home failed:', error);
    }

    console.log('🔬 Evaluation Test...');
    try {
        const response = await fetch(`${BASE_URL}/api/evaluate/1/`);
        const data = await response.json();
        console.log('✅ Evaluation:', data);
    } catch (error) {
        console.error('❌ Evaluation failed:', error);
    }
}

debugBackend();
