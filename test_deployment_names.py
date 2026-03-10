"""
Test different deployment names to find the correct one
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")

if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
    print("ERROR: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set in .env file")
    exit(1)

# Common deployment names to test
deployment_names = [
    "gpt-image-1",
    "dall-e-3",
    "dall-e-2",
    "gpt-image",
    "image-generation",
    "dalle3",
    "dalle2"
]

print(f"Testing deployment names at: {AZURE_OPENAI_ENDPOINT}")
print(f"API Version: {AZURE_OPENAI_API_VERSION}\n")
print("Testing common deployment names...\n")

for deployment_name in deployment_names:
    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{deployment_name}/images/generations"
    params = {"api-version": AZURE_OPENAI_API_VERSION}
    
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_API_KEY,
    }
    
    payload = {
        "prompt": "test",
        "size": "1024x1024",
        "n": 1,
    }
    
    try:
        response = requests.post(url, headers=headers, params=params, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"SUCCESS! Deployment name '{deployment_name}' works!")
            print(f"  -> Update your .env: AZURE_OPENAI_DEPLOYMENT={deployment_name}")
            break
        elif response.status_code == 404:
            print(f"  {deployment_name}: Not found (404)")
        elif response.status_code == 401:
            print(f"  {deployment_name}: Unauthorized (401) - Check API key")
            break
        else:
            print(f"  {deployment_name}: Status {response.status_code}")
    except requests.exceptions.Timeout:
        print(f"  {deployment_name}: Timeout")
    except Exception as e:
        print(f"  {deployment_name}: Error - {str(e)[:50]}")

print("\n" + "="*60)
print("If none worked, you need to:")
print("1. Check Azure Portal for your deployment name")
print("2. Or create a new deployment in Azure Portal")
print("="*60)
