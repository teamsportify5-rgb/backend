# Database Connection Fix

## Error: Access denied for user 'user'@'localhost'

This error means your `.env` file has incorrect MySQL credentials.

## Solution:

### Step 1: Create/Update `.env` file

Create a `.env` file in the `backend` directory with the correct MySQL credentials:

```env
DATABASE_URL=mysql+pymysql://root:YOUR_MYSQL_PASSWORD@localhost:3306/factory_management
SECRET_KEY=your-secret-key-change-this-in-production-min-32-characters-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Important**: 
- Replace `YOUR_MYSQL_PASSWORD` with your actual MySQL root password.
- **SECRET_KEY**: This is used for JWT token encryption. You can generate one using:
  
  **Option 1: Using Python (Recommended)**
  ```powershell
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
  
  **Option 2: Using OpenSSL**
  ```powershell
  openssl rand -hex 32
  ```
  
  **Option 3: Use any random string** (at least 32 characters long)
  - Example: `my-super-secret-factory-management-key-2024-production`
  
  **Note**: Keep this secret! Don't share it or commit it to version control.

### Step 2: Verify MySQL is Running

Check if MySQL service is running:

```powershell
Get-Service -Name MySQL*
```

If not running, start it:
```powershell
Start-Service -Name MySQL*
```

Or if using XAMPP, start MySQL from XAMPP Control Panel.

### Step 3: Test MySQL Connection

Test if you can connect to MySQL:

```powershell
mysql -u root -p
# Enter your password when prompted
```

If this works, your credentials are correct.

### Step 4: Verify Database Exists

Make sure the database exists:

```sql
-- Connect to MySQL
mysql -u root -p

-- Check if database exists
SHOW DATABASES;

-- If factory_management doesn't exist, create it:
CREATE DATABASE factory_management;

-- Exit
EXIT;
```

### Step 5: Common Issues

**Issue 1: Wrong Username**
- Make sure you're using `root` (or your MySQL username)
- Not `user` or `admin`

**Issue 2: Wrong Password**
- Use the password you set during MySQL installation
- If you forgot it, you may need to reset MySQL root password

**Issue 3: Database doesn't exist**
- Create it: `CREATE DATABASE factory_management;`

**Issue 4: MySQL not running**
- Start MySQL service or XAMPP

### Example .env file:

```env
# Database Configuration
DATABASE_URL=mysql+pymysql://root:mypassword123@localhost:3306/factory_management

# JWT Configuration
SECRET_KEY=my-super-secret-key-that-is-at-least-32-characters-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Note**: 
- No spaces around the `=` sign
- No quotes needed around values
- Replace `mypassword123` with your actual MySQL password

