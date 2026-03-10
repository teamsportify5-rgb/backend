# MySQL Database Setup Guide

## Step 1: Install MySQL (if not already installed)

### Option A: Using MySQL Installer (Recommended for Windows)
1. Download MySQL Installer from: https://dev.mysql.com/downloads/installer/
2. Choose "MySQL Installer for Windows"
3. Download the full installer (recommended) or web installer
4. Run the installer and follow these steps:
   - Choose "Developer Default" setup type
   - Click "Execute" to install required components
   - Configure MySQL Server:
     - Set root password (remember this password!)
     - Add MySQL to Windows PATH (recommended)
     - Configure as Windows Service (recommended)
   - Complete the installation

### Option B: Using XAMPP (Easier for beginners)
1. Download XAMPP from: https://www.apachefriends.org/
2. Install XAMPP (includes MySQL)
3. Start MySQL from XAMPP Control Panel

### Option C: Using winget (Windows Package Manager)
```powershell
winget install Oracle.MySQL
```

## Step 2: Start MySQL Server

### If installed as Windows Service:
- MySQL should start automatically
- Check if it's running:
  ```powershell
  Get-Service -Name MySQL*
  ```
- If not running, start it:
  ```powershell
  Start-Service -Name MySQL*
  ```

### If using XAMPP:
1. Open XAMPP Control Panel
2. Click "Start" next to MySQL

### Manual Start (if needed):
```powershell
# Navigate to MySQL bin directory (usually):
cd "C:\Program Files\MySQL\MySQL Server 8.0\bin"
# Start MySQL
.\mysqld.exe
```

## Step 3: Verify MySQL is Running

Open a new terminal and test the connection:
```powershell
mysql --version
```

If you get "command not found", add MySQL to PATH:
1. Find MySQL installation (usually `C:\Program Files\MySQL\MySQL Server 8.0\bin`)
2. Add to System PATH:
   - Right-click "This PC" → Properties
   - Advanced System Settings → Environment Variables
   - Edit "Path" under System Variables
   - Add MySQL bin directory path
   - Restart terminal

## Step 4: Access MySQL

### Using Command Line:
```powershell
mysql -u root -p
# Enter your root password when prompted
```

### Using MySQL Workbench (GUI - Recommended):
1. Download MySQL Workbench: https://dev.mysql.com/downloads/workbench/
2. Install and open MySQL Workbench
3. Click on "Local instance MySQL" or create a new connection:
   - Hostname: `localhost`
   - Port: `3306`
   - Username: `root`
   - Password: (your root password)
4. Click "Test Connection" then "OK"

## Step 5: Create the Database

### Using Command Line:
```sql
-- Connect to MySQL
mysql -u root -p

-- Create the database
CREATE DATABASE factory_management;

-- Verify it was created
SHOW DATABASES;

-- Exit MySQL
EXIT;
```

### Using MySQL Workbench:
1. Open MySQL Workbench
2. Connect to your MySQL server
3. Click the "SQL" icon (or press Ctrl+Shift+Enter)
4. Type the following SQL:
   ```sql
   CREATE DATABASE factory_management;
   ```
5. Click the execute button (lightning bolt icon) or press Ctrl+Enter
6. Verify in the left sidebar - you should see `factory_management` database

## Step 6: Update .env File

Create or edit `.env` file in the `backend` directory:

```env
DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/factory_management
SECRET_KEY=your-secret-key-change-this-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Important**: Replace `YOUR_PASSWORD` with your MySQL root password.

## Step 7: Test Database Connection

After setting up your `.env` file, test the connection:

```powershell
cd backend
python -c "from app.database import engine; engine.connect(); print('Database connection successful!')"
```

## Troubleshooting

### "Access denied" error:
- Make sure you're using the correct root password
- Reset MySQL root password if needed

### "Can't connect to MySQL server":
- Check if MySQL service is running
- Verify MySQL is listening on port 3306:
  ```powershell
  netstat -an | findstr 3306
  ```

### "Command 'mysql' not found":
- Add MySQL bin directory to your PATH
- Or use full path: `"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"`

### Port 3306 already in use:
- Another MySQL instance might be running
- Check running services: `Get-Service | Where-Object {$_.Name -like "*mysql*"}`



