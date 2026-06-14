"""Garment-only prompt validation for AI image generation."""
import re
from fastapi import HTTPException, status

GARMENT_KEYWORDS = frozenset({
    "garment", "garments", "apparel", "clothing", "clothes", "cloth", "textile",
    "textiles", "fabric", "fabrics", "shirt", "shirts", "t-shirt", "tshirt",
    "polo", "trouser", "trousers", "pant", "pants", "jeans", "jacket", "jackets",
    "coat", "coats", "dress", "dresses", "skirt", "skirts", "suit", "suits",
    "uniform", "uniforms", "hoodie", "sweater", "sweatshirt", "blouse", "kurta",
    "shalwar", "kameez", "dupatta", "stitching", "sewing", "tailoring", "knit",
    "knitted", "woven", "denim", "cotton", "polyester", "linen", "fashion",
    "sportswear", "activewear", "sportify", "factory", "manufacturing", "production",
    "inventory", "stock", "order", "orders", "warehouse", "label", "labels",
    "tag", "tags", "button", "buttons", "zipper", "thread", "yarn", "pattern",
    "patterns", "embroidery", "logo", "brand", "collection", "catalog", "catalogue",
    "wear", "outfit", "outfits", "sport", "jersey", "jerseys", "shorts", "leggings",
})

FORBIDDEN_TOPICS = frozenset({
    "car", "cars", "vehicle", "vehicles", "truck", "motorcycle", "bike", "bicycle",
    "airplane", "plane", "ship", "boat", "train", "rocket", "space", "planet",
    "animal", "animals", "dog", "dogs", "cat", "cats", "horse", "horses", "bird",
    "landscape", "mountain", "mountains", "beach", "ocean", "forest", "tree", "trees",
    "flower", "flowers", "food", "pizza", "burger", "restaurant", "building", "city",
    "house", "home", "castle", "weapon", "gun", "guns", "knife", "war", "soldier",
    "robot", "robots", "anime", "cartoon character", "superhero", "game", "gaming",
    "crypto", "bitcoin", "phone", "smartphone", "laptop", "computer", "electronics",
})

GARMENT_PROMPT_PREFIX = (
    "Professional garment manufacturing and apparel industry image only. "
    "Sportify is a garments/textile factory. Show clothing, fabrics, stitching, "
    "apparel products, or garment production context. No vehicles, animals, food, "
    "landscapes, electronics, or unrelated objects. Subject: "
)


def validate_garment_prompt(prompt: str) -> str:
    """Validate user prompt is garment-related; return trimmed prompt."""
    cleaned = " ".join(prompt.strip().split())
    if len(cleaned) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please describe a garment, apparel, textile, or clothing-related image.",
        )

    lower = cleaned.lower()
    words = set(re.findall(r"[a-z0-9\-]+", lower))

    if words & FORBIDDEN_TOPICS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only garment and apparel-related images are allowed for this factory system. "
                "Please describe clothing, textiles, fabrics, or garment manufacturing."
            ),
        )

    if not (words & GARMENT_KEYWORDS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Prompt must be related to garments, apparel, clothing, textiles, or "
                "garment manufacturing (e.g. cotton shirt, polo uniform, fabric roll, stitching line)."
            ),
        )

    return cleaned


def wrap_garment_prompt(prompt: str, *, skip_validation: bool = False) -> str:
    """Validate (optional) and wrap prompt with garment-only context."""
    subject = validate_garment_prompt(prompt) if not skip_validation else prompt.strip()
    return f"{GARMENT_PROMPT_PREFIX}{subject}"
