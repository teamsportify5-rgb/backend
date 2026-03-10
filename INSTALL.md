# Backend Installation Guide

## Issue: Rust/Cargo Required for pydantic-core

If you encounter errors about Rust/Cargo not being found when installing dependencies, you have two options:

### Option 1: Install Rust (Recommended for Development)

1. Download and install Rust from: https://rustup.rs/
2. After installation, restart your terminal
3. Verify installation:
   ```bash
   cargo --version
   ```
4. Then install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Option 2: Use Pre-built Wheels (Easier)

If you don't want to install Rust, try installing from pre-built wheels:

```bash
pip install --only-binary :all: -r requirements.txt
```

If that doesn't work, try installing packages individually with pre-built wheels:

```bash
pip install --only-binary :all: fastapi uvicorn sqlalchemy pymysql cryptography python-jose passlib python-multipart pydantic pydantic-settings python-dotenv reportlab PyPDF2
```

### Option 3: Use Python 3.11 or 3.12 (Most Compatible)

Python 3.14 is very new and some packages may not have pre-built wheels yet. Consider using Python 3.11 or 3.12 for better compatibility:

1. Install Python 3.11 or 3.12 from python.org
2. Create a virtual environment:
   ```bash
   python3.11 -m venv venv
   # or
   python3.12 -m venv venv
   ```
3. Activate and install:
   ```bash
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

### Quick Fix: Install Without pydantic-core Compilation

If you just need to get started quickly:

```bash
pip install fastapi uvicorn sqlalchemy pymysql python-jose passlib python-multipart pydantic-settings python-dotenv reportlab PyPDF2
pip install --prefer-binary pydantic
```

This will try to use pre-built wheels when available.




