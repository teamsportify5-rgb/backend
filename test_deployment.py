"""
Quick test to verify the deployment works with the correct name
"""
import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
api_key = os.getenv("AZURE_OPENAI_API_KEY", "")

if not all([endpoint, deployment, api_key]):
    print("ERROR: Missing required environment variables")
    print(f"Endpoint: {endpoint}")
    print(f"Deployment: {deployment}")
    print(f"API Key: {'SET' if api_key else 'MISSING'}")
    exit(1)

print(f"Testing deployment: {deployment}")
print(f"Endpoint: {endpoint}")
print(f"API Version: {api_version}\n")

url = f"{endpoint}/openai/deployments/{deployment}/images/generations"
params = {"api-version": api_version}

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}",
}

payload = {
    "prompt": "A simple test image of a red circle",
    "size": "1024x1024",
    "quality": "medium",
    "output_compression": 100,
    "output_format": "png",
    "n": 1,
}

try:
    print("Making request...")
    response = requests.post(url, headers=headers, params=params, json=payload, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    
    if "data" in result and len(result["data"]) > 0:
        if "b64_json" in result["data"][0]:
            print("SUCCESS! Image generated successfully!")
            print(f"Response contains base64 image data")
            
            # Save test image
            image_base64 = result["data"][0]["b64_json"]
            image_bytes = base64.b64decode(image_base64)
            with open("test_generated_image.png", "wb") as f:
                f.write(image_bytes)
            print("Test image saved as: test_generated_image.png")
        else:
            print("SUCCESS! But response format is different:")
            print(result["data"][0].keys())
    else:
        print("ERROR: Unexpected response format")
        print(result)
        
except requests.exceptions.HTTPError as e:
    print(f"HTTP Error: {e}")
    if hasattr(e.response, 'text'):
        print(f"Response: {e.response.text}")
except Exception as e:
    print(f"Error: {e}")
