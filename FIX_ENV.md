# Fix Your .env File

## Issues Found in Your .env File:

1. ❌ **Missing**: `AZURE_OPENAI_API_KEY` 
2. ❌ **Wrong**: `AZURE_OPENAI_DEPLOYMENT=dall-e-3` (should be `gpt-image-1`)
3. ❌ **Wrong**: `AZURE_OPENAI_API_VERSION=2024-12-01-preview` (should be `2025-04-01-preview`)
4. ⚠️ **Trailing slash**: `AZURE_OPENAI_ENDPOINT` has a trailing `/` (will be auto-fixed)

## What You Need to Do:

### Option 1: Manual Fix (Recommended)

1. Open `backend/.env` file
2. Find these lines and **UPDATE** them:

**Change this:**
```env
AZURE_OPENAI_ENDPOINT=https://husna-me2w8aow-swedencentral.cognitiveservices.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT=dall-e-3
```

**To this:**
```env
AZURE_OPENAI_ENDPOINT=https://husna-me2w8aow-swedencentral.cognitiveservices.azure.com
AZURE_OPENAI_API_KEY=your-azure-openai-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-image-1
AZURE_OPENAI_API_VERSION=2025-04-01-preview
```

3. **Save the file**
4. **Restart your FastAPI server**

### Option 2: Quick Copy-Paste

Add these lines to your `.env` file (replace the old ones):

```env
# Azure OpenAI GPT Image 1 API Configuration
AZURE_OPENAI_ENDPOINT=https://husna-me2w8aow-swedencentral.cognitiveservices.azure.com
AZURE_OPENAI_API_KEY=your-azure-openai-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-image-1
AZURE_OPENAI_API_VERSION=2025-04-01-preview
```

## After Fixing:

1. ✅ Save the `.env` file
2. ✅ Restart your FastAPI server (stop and start again)
3. ✅ Try generating an image again

The error should be fixed!
