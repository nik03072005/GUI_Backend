# 🗄️ Database Setup Guide for ISRO Backend

## Step 1: Create Supabase Database (Recommended)

1. **Go to [supabase.com](https://supabase.com)**
2. **Sign up/login** with GitHub
3. **Create new project**:
   - Name: `isro-backend-db`
   - Database Password: Generate a strong password (save it!)
   - Region: Choose closest to your location
4. **Wait for setup** (2-3 minutes)

## Step 2: Get Your Database URL

After setup, go to **Settings > Database** and copy your connection string:
```
postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
```

## Step 3: Update Render Environment Variables

1. **Go to Render Dashboard**
2. **Select your `GUI_Backend` service**
3. **Go to Environment tab**
4. **Add new environment variable**:
   - **Key**: `DATABASE_URL`
   - **Value**: Your Supabase connection string
5. **Click "Save Changes"**

## Step 4: Run Database Migrations

After updating the environment variable, Render will redeploy. The migrations should run automatically, but you can also trigger them manually:

1. **Go to Render Dashboard**
2. **Select your service**
3. **Go to Shell tab**
4. **Run**:
   ```bash
   python manage.py migrate
   ```

## Step 5: Create Superuser (Optional)

To access Django admin:
```bash
python manage.py createsuperuser
```

## Step 6: Test Your Setup

Run the updated `backend-debug.js` script in your browser console to verify everything works!

## Alternative: Neon Database

If you prefer Neon:
1. Go to [neon.tech](https://neon.tech)
2. Create project: `isro-backend`
3. Copy connection string from dashboard
4. Follow steps 3-6 above

## Database Schema

Your backend expects these main tables:
- `auth_user` (CustomUser model)
- `analyzer_uploadedlog` (File uploads)
- Django's built-in tables (sessions, admin, etc.)

The migrations will create everything automatically!

## Troubleshooting

**Connection Issues:**
- Verify the DATABASE_URL is correct
- Check if database allows external connections
- Ensure password doesn't contain special characters that need encoding

**Migration Issues:**
- Check Render logs for detailed error messages
- Ensure all required packages are in requirements.txt

**SSL Issues:**
- Supabase requires SSL by default (our settings handle this)
- If issues persist, try adding `?sslmode=require` to connection string
