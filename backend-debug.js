// 🔍 Clean Backend Debug Script - PRODUCTION TEST
// Copy this to browser console for debugging

console.log('� FIXED: Testing POST /api/evaluate/1/ endpoint');

// Your production URL
const BASE_URL = 'https://gui-backend-eab8.onrender.com';

async function testFixedEndpoint() {
    console.log('🏥 Health Check...');
    try {
        const response = await fetch(`${BASE_URL}/api/health/`);
        const data = await response.json();
        console.log('✅ Health:', data);
    } catch (error) {
        console.error('❌ Health failed:', error);
    }

    console.log('🔬 Testing FIXED POST endpoint...');
    try {
        const response = await fetch(`${BASE_URL}/api/evaluate/1/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // 'Authorization': 'Bearer YOUR_TOKEN_HERE'  // Add your token
            },
            body: JSON.stringify({
                analysis_type: 'periodicity',
                data: {}
            })
        });
        
        if (response.status === 401) {
            console.log('� Authentication required - expected for protected endpoint');
        } else {
            const data = await response.json();
            console.log('✅ POST Evaluation result:', data);
        }
    } catch (error) {
        console.error('❌ POST Evaluation failed:', error);
    }

    console.log('📊 Your frontend should now receive real data instead of fallback mock data!');
}

testFixedEndpoint();
