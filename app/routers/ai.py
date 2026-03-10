from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, AIImageLog, Order, OrderStatus, Attendance, AttendanceStatus, Inventory
from app.schemas import AIImageResponse
from app.auth import get_current_user
from openai import OpenAI, AzureOpenAI
import os
import base64
import requests
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()

router = APIRouter()

# Create static images directory (use /tmp on Vercel - ephemeral)
STATIC_IMAGES_DIR = Path("/tmp/static/images/ai-generated") if os.getenv("VERCEL") else Path("static/images/ai-generated")
STATIC_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

def get_azure_gpt_image_config():
    """Get Azure OpenAI GPT Image 1 API configuration"""
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-image-1")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
    
    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
        return None
    
    return {
        "endpoint": AZURE_OPENAI_ENDPOINT.rstrip("/"),
        "api_key": AZURE_OPENAI_API_KEY,
        "deployment": AZURE_OPENAI_DEPLOYMENT,
        "api_version": AZURE_OPENAI_API_VERSION
    }

# Lazy initialization of OpenAI client (supports both standard OpenAI and Azure OpenAI)
def get_openai_client():
    """Get OpenAI client (lazy initialization to avoid startup errors)
    Note: This is for DALL-E fallback, not GPT Image 1 API
    """
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    # Use a separate deployment for DALL-E (if you have one)
    AZURE_DALLE_DEPLOYMENT = os.getenv("AZURE_DALLE_DEPLOYMENT", "dall-e-3")
    
    if not OPENAI_API_KEY:
        return None, False, None
    
    try:
        if AZURE_OPENAI_ENDPOINT:
            # Only use Azure OpenAI SDK if we have a DALL-E deployment
            # Don't use GPT Image 1 deployment for SDK calls
            # For now, skip Azure OpenAI SDK and use standard OpenAI if available
            # This prevents the DeploymentNotFound error
            pass
        
        # Standard OpenAI (preferred for fallback)
        client = OpenAI(api_key=OPENAI_API_KEY)
        return client, False, "dall-e-2"
    except Exception as e:
        print(f"Warning: Failed to initialize OpenAI client: {e}")
        return None, False, None

def generate_azure_gpt_image(prompt: str, config: dict) -> str:
    """Generate image using Azure OpenAI GPT Image 1 API (returns base64)"""
    url = f"{config['endpoint']}/openai/deployments/{config['deployment']}/images/generations"
    params = {"api-version": config['api_version']}
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}",
    }
    
    payload = {
        "prompt": prompt,
        "size": "1024x1024",
        "quality": "medium",
        "output_compression": 100,
        "output_format": "png",
        "n": 1,
    }
    
    response = requests.post(url, headers=headers, params=params, json=payload)
    response.raise_for_status()
    
    result = response.json()
    
    # Azure GPT Image 1 returns base64 in b64_json field
    if "data" in result and len(result["data"]) > 0:
        if "b64_json" in result["data"][0]:
            return result["data"][0]["b64_json"]
        elif "url" in result["data"][0]:
            return result["data"][0]["url"]
    
    raise ValueError("Invalid response format from Azure GPT Image API")

def save_base64_image(base64_data: str, user_id: int) -> str:
    """Save base64 image to disk and return the relative URL"""
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ai_image_{user_id}_{timestamp}.png"
    filepath = STATIC_IMAGES_DIR / filename
    
    # Decode and save
    image_bytes = base64.b64decode(base64_data)
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    
    # Return relative URL path (frontend will prepend API base URL)
    return f"/static/images/ai-generated/{filename}"

def get_full_image_url(relative_url: str) -> str:
    """Convert relative URL to full URL if needed"""
    # If it's already a full URL (starts with http), return as is
    if relative_url.startswith("http://") or relative_url.startswith("https://"):
        return relative_url
    
    # Otherwise, return relative URL (frontend will handle prepending API base URL)
    return relative_url


def download_image_to_static(url: str, user_id: int) -> str:
    """Download image from URL to static folder and return relative URL."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ai_image_{user_id}_{timestamp}.png"
    filepath = STATIC_IMAGES_DIR / filename
    with open(filepath, "wb") as f:
        f.write(resp.content)
    return f"/static/images/ai-generated/{filename}"


def overlay_logo_on_image(base_image_path: Path, logo_bytes: bytes, user_id: int) -> str:
    """
    Overlay logo on top-center of the base image. Logo is scaled to max 25% of base width.
    Returns relative URL of the new image.
    """
    base_img = Image.open(base_image_path).convert("RGBA")
    logo_img = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    w, h = base_img.size
    # Scale logo to max 25% of base width, preserving aspect ratio
    max_logo_w = int(w * 0.25)
    ratio = min(max_logo_w / logo_img.width, 1.0)
    new_lw = int(logo_img.width * ratio)
    new_lh = int(logo_img.height * ratio)
    logo_resized = logo_img.resize((new_lw, new_lh), Image.Resampling.LANCZOS)
    # Position: top-center with a small margin
    margin = int(min(w, h) * 0.02)
    x = (w - new_lw) // 2
    y = margin
    base_img.paste(logo_resized, (x, y), logo_resized)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ai_image_{user_id}_{timestamp}_with_logo.png"
    out_path = STATIC_IMAGES_DIR / filename
    base_img.convert("RGB").save(out_path, "PNG")
    return f"/static/images/ai-generated/{filename}"


@router.post("/image", response_model=AIImageResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_image(
    prompt: str = Form(...),
    logo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate an AI image and optionally overlay an uploaded logo on top."""
    image_url = None
    
    try:
        # Priority 1: Try Azure OpenAI GPT Image 1 API (new API)
        azure_gpt_config = get_azure_gpt_image_config()
        if azure_gpt_config:
            try:
                base64_image = generate_azure_gpt_image(prompt, azure_gpt_config)
                # Save base64 image to disk
                image_url = save_base64_image(base64_image, current_user.id)
            except requests.exceptions.HTTPError as e:
                error_detail = str(e)
                if hasattr(e.response, 'text'):
                    error_detail = e.response.text
                print(f"Azure GPT Image 1 API failed: {error_detail}")
            except Exception as e:
                print(f"Azure GPT Image 1 API failed: {e}")
        
        # Priority 2: Try standard OpenAI SDK (DALL-E via SDK) - only if no Azure endpoint conflict
        if not image_url:
            OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
            # Only use standard OpenAI if we have the key and no Azure endpoint to avoid conflicts
            if OPENAI_API_KEY and not os.getenv("AZURE_OPENAI_ENDPOINT"):
                try:
                    client = OpenAI(api_key=OPENAI_API_KEY)
                    response = client.images.generate(
                        model="dall-e-2",
                        prompt=prompt,
                        n=1,
                        size="1024x1024"
                    )
                    if hasattr(response.data[0], 'url') and response.data[0].url:
                        image_url = response.data[0].url
                    elif hasattr(response.data[0], 'b64_json') and response.data[0].b64_json:
                        image_url = save_base64_image(response.data[0].b64_json, current_user.id)
                except Exception as e:
                    print(f"OpenAI SDK fallback failed: {e}")
        
        if not image_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No AI image generation service configured. Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY for GPT Image 1, or OPENAI_API_KEY for DALL-E."
            )
        
        # If user uploaded a logo, overlay it on the generated image
        if logo and logo.filename and logo.content_type and logo.content_type.startswith("image/"):
            logo_bytes = await logo.read()
            if logo_bytes:
                # If image_url is a remote URL, download to static first
                if image_url.startswith("http://") or image_url.startswith("https://"):
                    image_url = download_image_to_static(image_url, current_user.id)
                # Resolve path: image_url is like /static/images/ai-generated/xxx.png
                base_filename = image_url.split("/")[-1]
                base_path = STATIC_IMAGES_DIR / base_filename
                if base_path.exists():
                    image_url = overlay_logo_on_image(base_path, logo_bytes, current_user.id)
        
        # Ensure we have a valid image URL
        final_image_url = get_full_image_url(image_url)
        
        # Save to database
        image_log = AIImageLog(
            user_id=current_user.id,
            prompt_text=prompt,
            generated_image_url=final_image_url
        )
        db.add(image_log)
        db.commit()
        db.refresh(image_log)
        
        return image_log
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating image: {str(e)}"
        )


@router.get("/images", response_model=List[AIImageResponse])
async def get_user_images(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all AI images generated by the current user."""
    images = db.query(AIImageLog).filter(
        AIImageLog.user_id == current_user.id
    ).order_by(AIImageLog.created_at.desc()).offset(skip).limit(limit).all()
    
    return images


@router.get("/images/all", response_model=List[AIImageResponse])
async def get_all_images(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all AI images (admin only)."""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can view all images"
        )
    
    images = db.query(AIImageLog).order_by(
        AIImageLog.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return images


@router.post("/generate/performance-summary", response_model=AIImageResponse, status_code=status.HTTP_201_CREATED)
async def generate_performance_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Auto-generate a visual summary of Sportify performance (orders, attendance, etc.)."""
    if current_user.role.value not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin and manager can generate performance summaries"
        )
    
    try:
        # Fetch Sportify performance data
        all_orders = db.query(Order).all()
        today_attendance = db.query(Attendance).filter(Attendance.date == date.today()).all()
        
        # Calculate metrics
        total_orders = len(all_orders)
        pending_orders = len([o for o in all_orders if o.status == OrderStatus.PENDING])
        in_progress_orders = len([o for o in all_orders if o.status == OrderStatus.IN_PROGRESS])
        completed_orders = len([o for o in all_orders if o.status == OrderStatus.COMPLETED])
        delayed_orders = len([o for o in all_orders if o.status == OrderStatus.DELAYED])
        
        total_attendance = len(today_attendance)
        present_count = len([a for a in today_attendance if a.status == AttendanceStatus.PRESENT])
        absent_count = len([a for a in today_attendance if a.status == AttendanceStatus.ABSENT])
        late_count = len([a for a in today_attendance if a.status == AttendanceStatus.LATE])
        
        attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0
        completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0
        
        # Construct intelligent prompt
        prompt = f"""Create a professional Sportify performance summary infographic with the following data:
        
Sportify Performance Dashboard:
- Total Orders: {total_orders}
  * Pending: {pending_orders}
  * In Progress: {in_progress_orders}
  * Completed: {completed_orders}
  * Delayed: {delayed_orders}
- Order Completion Rate: {completion_rate:.1f}%

Today's Attendance:
- Total Employees: {total_attendance}
  * Present: {present_count}
  * Absent: {absent_count}
  * Late: {late_count}
- Attendance Rate: {attendance_rate:.1f}%

Design a modern, clean infographic with charts, icons, and visual elements showing these Sportify performance metrics. Use a professional color scheme with clear labels and numbers."""
        
        # Generate image using existing function
        image_url = None
        
        # Try Azure GPT Image 1 API first
        azure_gpt_config = get_azure_gpt_image_config()
        if azure_gpt_config:
            try:
                base64_image = generate_azure_gpt_image(prompt, azure_gpt_config)
                image_url = save_base64_image(base64_image, current_user.id)
            except Exception as e:
                print(f"Azure GPT Image 1 API failed: {e}")
        
        # Fallback to OpenAI SDK
        if not image_url:
            openai_client, use_azure, model_name = get_openai_client()
            if openai_client:
                try:
                    response = openai_client.images.generate(
                        model=model_name,
                        prompt=prompt,
                        n=1,
                        size="1024x1024"
                    )
                    if hasattr(response.data[0], 'url') and response.data[0].url:
                        image_url = response.data[0].url
                    elif hasattr(response.data[0], 'b64_json') and response.data[0].b64_json:
                        image_url = save_base64_image(response.data[0].b64_json, current_user.id)
                except Exception as e:
                    print(f"OpenAI SDK failed: {e}")
        
        if not image_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No AI image generation service configured."
            )
        
        # Save to database
        image_log = AIImageLog(
            user_id=current_user.id,
            prompt_text=prompt,
            generated_image_url=image_url
        )
        db.add(image_log)
        db.commit()
        db.refresh(image_log)
        
        return image_log
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating performance summary: {str(e)}"
        )


@router.post("/generate/stock-summary", response_model=AIImageResponse, status_code=status.HTTP_201_CREATED)
async def generate_stock_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Auto-generate a visual summary of stock/inventory levels."""
    if current_user.role.value not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin and manager can generate stock summaries"
        )
    
    try:
        # Fetch inventory data
        all_items = db.query(Inventory).all()
        low_stock_items = db.query(Inventory).filter(
            Inventory.quantity <= Inventory.threshold
        ).all()
        
        # Calculate metrics
        total_items = len(all_items)
        low_stock_count = len(low_stock_items)
        
        # Group by category
        category_counts = {}
        category_totals = {}
        for item in all_items:
            cat = item.category or "Uncategorized"
            category_counts[cat] = category_counts.get(cat, 0) + 1
            category_totals[cat] = category_totals.get(cat, 0) + item.quantity
        
        # Get top categories
        top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Get low stock items details
        low_stock_details = []
        for item in low_stock_items[:10]:  # Top 10 low stock items
            low_stock_details.append(f"{item.item}: {item.quantity}{item.unit} (threshold: {item.threshold}{item.unit})")
        
        # Calculate total inventory value (simplified - assuming all items have value)
        total_quantity = sum(item.quantity for item in all_items)
        
        # Construct intelligent prompt
        prompt = f"""Create a professional stock and inventory summary infographic with the following data:
        
Inventory Overview:
- Total Items: {total_items}
- Total Quantity: {total_quantity} units
- Low Stock Items: {low_stock_count} items need restocking

Top Categories:
{chr(10).join([f"- {cat}: {count} items, {category_totals[cat]} total units" for cat, count in top_categories])}

Low Stock Alert Items:
{chr(10).join([f"- {item}" for item in low_stock_details[:5]])}

Design a modern, clean infographic with charts, icons, and visual elements showing these inventory and stock metrics. Include warning indicators for low stock items. Use a professional color scheme with clear labels and numbers."""
        
        # Generate image using existing function
        image_url = None
        
        # Try Azure GPT Image 1 API first
        azure_gpt_config = get_azure_gpt_image_config()
        if azure_gpt_config:
            try:
                base64_image = generate_azure_gpt_image(prompt, azure_gpt_config)
                image_url = save_base64_image(base64_image, current_user.id)
            except Exception as e:
                print(f"Azure GPT Image 1 API failed: {e}")
        
        # Fallback to OpenAI SDK
        if not image_url:
            openai_client, use_azure, model_name = get_openai_client()
            if openai_client:
                try:
                    response = openai_client.images.generate(
                        model=model_name,
                        prompt=prompt,
                        n=1,
                        size="1024x1024"
                    )
                    if hasattr(response.data[0], 'url') and response.data[0].url:
                        image_url = response.data[0].url
                    elif hasattr(response.data[0], 'b64_json') and response.data[0].b64_json:
                        image_url = save_base64_image(response.data[0].b64_json, current_user.id)
                except Exception as e:
                    print(f"OpenAI SDK failed: {e}")
        
        if not image_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No AI image generation service configured."
            )
        
        # Save to database
        image_log = AIImageLog(
            user_id=current_user.id,
            prompt_text=prompt,
            generated_image_url=image_url
        )
        db.add(image_log)
        db.commit()
        db.refresh(image_log)
        
        return image_log
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating stock summary: {str(e)}"
        )



