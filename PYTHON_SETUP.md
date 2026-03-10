# Python Setup Guide

## Current Issue
Python 3.14 is too new and `pydantic-core` doesn't have pre-built wheels for it, requiring Rust compilation.

## Solution: Install Python 3.12

### Step 1: Download Python 3.12
1. Go to: https://www.python.org/downloads/release/python-31211/
2. Download "Windows installer (64-bit)" for Python 3.12.11
3. Run the installer
4. **IMPORTANT**: Check "Add Python 3.12 to PATH" during installation

### Step 2: Verify Installation
```powershell
py -3.12 --version
# Should show: Python 3.12.11
```

### Step 3: Create Virtual Environment with Python 3.12
```powershell
cd backend
py -3.12 -m venv venv
```

### Step 4: Activate Virtual Environment
```powershell
venv\Scripts\activate
```

### Step 5: Upgrade pip
```powershell
python -m pip install --upgrade pip
```

### Step 6: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 7: Verify Installation
```powershell
python -c "import fastapi; print('FastAPI installed successfully!')"
```

## Alternative: Use winget (Windows Package Manager)
```powershell
winget install Python.Python.3.12
```

Then follow steps 3-7 above.




