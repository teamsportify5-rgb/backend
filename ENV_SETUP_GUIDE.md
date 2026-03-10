# Environment Variables Setup Guide

## Error: "No AI image generation service configured"

This error means your `.env` file is missing the Azure OpenAI configuration.

## Quick Fix

Add these lines to your `backend/.env` file:

```env
# Azure OpenAI GPT Image 1 API Configuration (REQUIRED)
AZURE_OPENAI_ENDPOINT=https://husna-me2w8aow-swedencentral.cognitiveservices.azure.com
AZURE_OPENAI_API_KEY=your-azure-openai-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-image-1
AZURE_OPENAI_API_VERSION=2025-04-01-preview
```

## Step-by-Step Instructions

1. **Open your `.env` file** in the `backend/` directory
   - Location: `D:\Projects\FYP Project\backend\.env`

2. **Add or update these variables:**
   ```env
   AZURE_OPENAI_ENDPOINT=https://husna-me2w8aow-swedencentral.cognitiveservices.azure.com
   AZURE_OPENAI_API_KEY=your-azure-openai-api-key-here
   AZURE_OPENAI_DEPLOYMENT=gpt-image-1
   AZURE_OPENAI_API_VERSION=2025-04-01-preview
   ```

3. **Save the file**

4. **Restart your FastAPI server** (stop and start again)

5. **Try generating an image again**

## Complete .env File Example

Your `.env` file should look like this:

```env
# Database Configuration
DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/factory_management

# JWT Authentication
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Azure OpenAI GPT Image 1 API (REQUIRED for AI Image Generation)
AZURE_OPENAI_ENDPOINT=https://husna-me2w8aow-swedencentral.cognitiveservices.azure.com
AZURE_OPENAI_API_KEY=your-azure-openai-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-image-1
AZURE_OPENAI_API_VERSION=2025-04-01-preview
```

## Verification

After adding the variables, restart your server and check:

1. The server should start without errors
2. When you try to generate an image, it should work
3. Check the server console for any error messages

## Troubleshooting

### Still getting the error?
1. Make sure the `.env` file is in the `backend/` directory (not root)
2. Make sure there are no spaces around the `=` sign
3. Make sure the values are correct (no extra quotes)
4. Restart the server after making changes

### Check if variables are loaded:
Add this temporary test endpoint to see if variables are loaded:
```python
@router.get("/test-config")
async def test_config():
    return {
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "has_key": bool(os.getenv("AZURE_OPENAI_API_KEY")),
        "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT")
    }
```
