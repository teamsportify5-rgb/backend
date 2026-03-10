# Azure OpenAI GPT Image 1 API Integration

This document explains how the Azure OpenAI GPT Image 1 API has been integrated into the Factory Management System.

## Overview

The AI image generation feature now supports:
1. **Azure OpenAI GPT Image 1 API** (Primary - New API)
2. **OpenAI DALL-E via SDK** (Fallback)
3. **Azure OpenAI DALL-E via SDK** (Fallback)

## Environment Variables

Add the following environment variables to your `.env` file in the `backend/` directory:

```env
# Azure OpenAI GPT Image 1 API Configuration (Primary)
AZURE_OPENAI_ENDPOINT=https://husna-me2w8aow-swedencentral.cognitiveservices.azure.com
AZURE_OPENAI_API_KEY=your-azure-openai-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-image-1
AZURE_OPENAI_API_VERSION=2025-04-01-preview

# Optional: Fallback to OpenAI SDK (DALL-E)
# OPENAI_API_KEY=your-openai-api-key
# OPENAI_API_KEY is used for standard OpenAI or Azure OpenAI DALL-E via SDK
```

## How It Works

### Priority Order

1. **Azure GPT Image 1 API** (Highest Priority)
   - Uses direct HTTP requests to Azure OpenAI endpoint
   - Returns base64-encoded images
   - Images are saved to `backend/static/images/ai-generated/`
   - Served via FastAPI static file serving

2. **OpenAI SDK** (Fallback)
   - Uses OpenAI Python SDK
   - Supports both standard OpenAI and Azure OpenAI DALL-E
   - Returns image URLs or base64 data

### Image Storage

- Generated images are saved to: `backend/static/images/ai-generated/`
- Filename format: `ai_image_{user_id}_{timestamp}.png`
- Images are accessible via: `http://localhost:8000/static/images/ai-generated/{filename}`
- Frontend automatically prepends the API base URL for relative paths

## API Endpoints

### Generate Image
```
POST /ai/image
Authorization: Bearer {token}
Body: {
  "prompt": "A photograph of a red fox in an autumn forest"
}
```

### Get User Images
```
GET /ai/images
Authorization: Bearer {token}
```

### Get All Images (Admin Only)
```
GET /ai/images/all
Authorization: Bearer {token}
```

## Testing

1. Make sure your `.env` file has the correct Azure OpenAI credentials
2. Install dependencies: `pip install -r requirements.txt`
3. Start the backend server: `uvicorn app.main:app --reload`
4. Test the endpoint using the frontend or API client

## Troubleshooting

### Images Not Loading
- Check that the `static/images/ai-generated/` directory exists
- Verify static file mounting in `app/main.py`
- Check CORS settings if accessing from frontend

### API Errors
- Verify environment variables are set correctly
- Check Azure OpenAI endpoint and API key
- Ensure the deployment name matches your Azure resource

### Base64 Decoding Errors
- Verify the API response format
- Check that the `b64_json` field exists in the response

## Notes

- The system automatically falls back to other methods if Azure GPT Image 1 fails
- Images are stored locally on the server
- For production, consider using cloud storage (S3, Azure Blob, etc.)
- The static file serving is suitable for development; use a CDN or cloud storage for production
