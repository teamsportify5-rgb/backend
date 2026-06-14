from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, AIImageLog, Order, OrderStatus, Attendance, AttendanceStatus, Inventory
from app.schemas import AIImageResponse
from app.auth import get_current_user
from app.image_storage import (
    persist_generation_result,
    persist_image_bytes,
    persist_image_from_url,
    local_static_dir,
    delete_stored_image,
)
from app.garment_prompt import validate_garment_prompt, wrap_garment_prompt
import os
import requests
from datetime import date
from dotenv import load_dotenv
from PIL import Image
import io

load_dotenv()

router = APIRouter()

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

def _load_image_bytes(image_url: str) -> bytes:
    if image_url.startswith("http://") or image_url.startswith("https://"):
        resp = requests.get(image_url, timeout=60)
        resp.raise_for_status()
        return resp.content
    filename = image_url.split("/")[-1]
    return (local_static_dir() / filename).read_bytes()


def overlay_logo_on_bytes(base_bytes: bytes, logo_bytes: bytes) -> bytes:
    """Overlay logo on top-center; returns PNG bytes."""
    base_img = Image.open(io.BytesIO(base_bytes)).convert("RGBA")
    logo_img = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    w, h = base_img.size
    max_logo_w = int(w * 0.25)
    ratio = min(max_logo_w / logo_img.width, 1.0)
    new_lw = int(logo_img.width * ratio)
    new_lh = int(logo_img.height * ratio)
    logo_resized = logo_img.resize((new_lw, new_lh), Image.Resampling.LANCZOS)
    margin = int(min(w, h) * 0.02)
    x = (w - new_lw) // 2
    y = margin
    base_img.paste(logo_resized, (x, y), logo_resized)
    out = io.BytesIO()
    base_img.convert("RGB").save(out, "PNG")
    return out.getvalue()


def generate_image_for_prompt(prompt: str, user_id: int, *, skip_validation: bool = False) -> str:
    """Generate via Azure GPT Image 1 or OpenAI DALL-E; persist to configured storage."""
    garment_prompt = wrap_garment_prompt(prompt, skip_validation=skip_validation)
    azure_gpt_config = get_azure_gpt_image_config()
    if azure_gpt_config:
        try:
            result = generate_azure_gpt_image(garment_prompt, azure_gpt_config)
            return persist_generation_result(result, user_id)
        except requests.exceptions.HTTPError as e:
            error_detail = e.response.text if hasattr(e, "response") and e.response is not None else str(e)
            print(f"Azure GPT Image 1 API failed: {error_detail}")
        except Exception as e:
            print(f"Azure GPT Image 1 API failed: {e}")

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key and not os.getenv("AZURE_OPENAI_ENDPOINT"):
        try:
            client = OpenAI(api_key=openai_api_key)
            response = client.images.generate(
                model="dall-e-2",
                prompt=garment_prompt,
                n=1,
                size="1024x1024",
            )
            item = response.data[0]
            if getattr(item, "url", None):
                return persist_image_from_url(item.url, user_id)
            if getattr(item, "b64_json", None):
                return persist_generation_result(item.b64_json, user_id)
        except Exception as e:
            print(f"OpenAI SDK fallback failed: {e}")

    openai_client, _, model_name = get_openai_client()
    if openai_client:
        try:
            response = openai_client.images.generate(
                model=model_name,
                prompt=garment_prompt,
                n=1,
                size="1024x1024",
            )
            item = response.data[0]
            if getattr(item, "url", None):
                return persist_image_from_url(item.url, user_id)
            if getattr(item, "b64_json", None):
                return persist_generation_result(item.b64_json, user_id)
        except Exception as e:
            print(f"OpenAI SDK failed: {e}")

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="No AI image generation service configured. Set Azure OpenAI or OPENAI_API_KEY.",
    )


@router.post("/image", response_model=AIImageResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_image(
    prompt: str = Form(...),
    logo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate an AI image and optionally overlay an uploaded logo on top."""
    try:
        validate_garment_prompt(prompt)
        image_url = generate_image_for_prompt(prompt, current_user.id)

        if logo and logo.filename and logo.content_type and logo.content_type.startswith("image/"):
            logo_bytes = await logo.read()
            if logo_bytes:
                merged = overlay_logo_on_bytes(_load_image_bytes(image_url), logo_bytes)
                image_url = persist_image_bytes(merged, current_user.id, suffix="with_logo")

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


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an AI image. Owners only; admins may delete any user's image."""
    image_log = db.query(AIImageLog).filter(AIImageLog.image_id == image_id).first()
    if not image_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    is_admin = current_user.role.value == "admin"
    if image_log.user_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to delete this image",
        )

    delete_stored_image(image_log.generated_image_url)
    db.delete(image_log)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
        prompt = f"""Create a professional garment manufacturing factory performance infographic with the following data:
        
Garment Factory Performance Dashboard:
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

Design a modern, clean garment/apparel factory infographic with charts, clothing icons, fabric rolls, and stitching visuals showing these metrics. Use a professional color scheme with clear labels and numbers. Garments and textile manufacturing theme only."""
        
        image_url = generate_image_for_prompt(prompt, current_user.id, skip_validation=True)
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
        prompt = f"""Create a professional garment factory stock and textile inventory summary infographic with the following data:
        
Garment Inventory Overview:
- Total Items: {total_items}
- Total Quantity: {total_quantity} units
- Low Stock Items: {low_stock_count} items need restocking

Top Categories:
{chr(10).join([f"- {cat}: {count} items, {category_totals[cat]} total units" for cat, count in top_categories])}

Low Stock Alert Items:
{chr(10).join([f"- {item}" for item in low_stock_details[:5]])}

Design a modern, clean garment manufacturing infographic with fabric rolls, apparel boxes, clothing tags, and inventory charts. Include warning indicators for low stock textile/garment materials. Garments and textile theme only. Use a professional color scheme with clear labels and numbers."""
        
        image_url = generate_image_for_prompt(prompt, current_user.id, skip_validation=True)
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



