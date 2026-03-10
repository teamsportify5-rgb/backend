"""
Script to check available Azure OpenAI deployments
Run this to find the correct deployment name for GPT Image 1
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")

if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
    print("ERROR: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set in .env file")
    exit(1)

print(f"Checking deployments at: {AZURE_OPENAI_ENDPOINT}\n")

# Try different API versions
api_versions = ["2024-02-15-preview", "2024-03-01-preview", "2023-12-01-preview", "2023-05-15"]

headers = {
    "api-key": AZURE_OPENAI_API_KEY,
}

deployments_found = False

for api_version in api_versions:
    print(f"Trying API version: {api_version}...")
    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments"
    params = {"api-version": api_version}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        deployments = response.json()
        
        if "data" in deployments and len(deployments["data"]) > 0:
            print(f"SUCCESS: Found {len(deployments['data'])} deployment(s) with API version {api_version}:\n")
            for deployment in deployments["data"]:
                model = deployment.get("model", "unknown")
                deployment_id = deployment.get("id", "unknown")
                status = deployment.get("status", "unknown")
                print(f"  Deployment ID: {deployment_id}")
                print(f"     Model: {model}")
                print(f"     Status: {status}")
                print()
            
            # Check for image generation models
            print("\nLooking for image generation deployments...")
            image_deployments = [d for d in deployments["data"] if "image" in d.get("model", "").lower() or "dall" in d.get("model", "").lower() or "gpt" in d.get("model", "").lower()]
            
            if image_deployments:
                print(f"SUCCESS: Found {len(image_deployments)} image generation deployment(s):")
                for dep in image_deployments:
                    print(f"  IMAGE DEPLOYMENT: {dep.get('id')} - {dep.get('model')}")
                    print(f"  -> Use this in your .env: AZURE_OPENAI_DEPLOYMENT={dep.get('id')}")
            else:
                print("WARNING: No image generation deployments found")
                print("Available deployments:")
                for dep in deployments["data"]:
                    print(f"  - {dep.get('id')} ({dep.get('model')})")
            
            deployments_found = True
            break
        else:
            print(f"  No deployments found with this API version")
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"  404 - This API version doesn't support listing deployments")
        else:
            print(f"  HTTP Error {e.response.status_code}: {e}")
    except Exception as e:
        print(f"  Error: {e}")

if not deployments_found:
    print("\n" + "="*60)
    print("COULD NOT LIST DEPLOYMENTS")
    print("="*60)
    print("\nThis might mean:")
    print("1. The API endpoint doesn't support listing deployments")
    print("2. You need to check Azure Portal for deployment names")
    print("\nSOLUTION: Check Azure Portal for your deployment name")
    print("1. Go to https://portal.azure.com")
    print("2. Navigate to your Azure OpenAI resource")
    print("3. Go to 'Deployments' section")
    print("4. Find your image generation deployment name")
    print("5. Update .env with: AZURE_OPENAI_DEPLOYMENT=your-deployment-name")
    print("\nAlternatively, try testing with common deployment names:")
    print("  - gpt-image-1")
    print("  - dall-e-3")
    print("  - dall-e-2")
