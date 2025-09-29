// 🔍 Clean Backend Debug Script - DATABASE SETUP TEST
// Copy this to browser console for debugging

console.log('🚀 Testing Backend with New Database Setup');

// Your production URL
const BASE_URL = 'https://gui-backend-eab8.onrender.com';

async function testDatabaseSetup() {
    console.log('🏥 Health Check...');
    try {
        const response = await fetch(`${BASE_URL}/api/health/`);
        const data = await response.json();
        console.log('✅ Health:', data);
    } catch (error) {
        console.error('❌ Health failed:', error);
        return;
    }

    console.log('�️ Testing database connection...');
    try {
        // Test an endpoint that requires database access
        const response = await fetch(`${BASE_URL}/api/files/`, {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer dummy_token' // Will fail but shows database status
            }
        });
        
        if (response.status === 401) {
            console.log('✅ Database connected - authentication working');
        } else if (response.status === 500) {
            console.log('❌ Database connection issue');
        }
        
        const data = await response.json();
        console.log('📊 Response:', data);
    } catch (error) {
        console.error('❌ Database test failed:', error);
    }

    console.log('🔬 Testing evaluation endpoint...');
    try {
        const response = await fetch(`${BASE_URL}/api/evaluate/1/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer dummy_token'
            },
            body: JSON.stringify({
                analysis_type: 'periodicity'
            })
        });
        
        const data = await response.json();
        console.log('✅ Evaluation result:', data);
        
        if (data.metadata?.status === 'mock_data') {
            console.log('🎯 Using mock data (expected with dummy token)');
        } else {
            console.log('📈 Real data processing working!');
        }
    } catch (error) {
        console.error('❌ Evaluation failed:', error);
    }

    console.log('\n� Next Steps:');
    console.log('1. Set up your PostgreSQL database (Supabase recommended)');
    console.log('2. Update DATABASE_URL in Render environment variables');
    console.log('3. Run migrations: python manage.py migrate');
    console.log('4. Test with real authentication tokens');
}

testDatabaseSetup();
