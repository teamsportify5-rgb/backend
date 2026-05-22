"""
Persist AI-generated images to Vercel Blob, Supabase Storage, or local static (dev).
Set IMAGE_STORAGE_PROVIDER=vercel|supabase|local, or leave unset for auto-detect.
"""
from __future__ import annotations

import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# Local fallback (ephemeral on Vercel — only used when no cloud storage is configured)
_STATIC_IMAGES_DIR = (
    Path("/tmp/static/images/ai-generated")
    if os.getenv("VERCEL")
    else Path("static/images/ai-generated")
)


def _provider() -> str:
    explicit = (os.getenv("IMAGE_STORAGE_PROVIDER") or "").strip().lower()
    if explicit in ("vercel", "supabase", "local"):
        return explicit
    if os.getenv("BLOB_READ_WRITE_TOKEN"):
        return "vercel"
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        return "supabase"
    return "local"


def _object_path(user_id: int, suffix: str = "") -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extra = f"_{suffix}" if suffix else ""
    return f"ai-generated/ai_image_{user_id}_{timestamp}{extra}.png"


def _upload_vercel(pathname: str, data: bytes) -> str:
    import vercel_blob

    resp = vercel_blob.put(
        pathname,
        data,
        {
            "access": "public",
            "contentType": "image/png",
            "addRandomSuffix": "false",
        },
    )
    url = resp.get("url") if isinstance(resp, dict) else None
    if not url:
        raise RuntimeError(f"Vercel Blob upload did not return a URL: {resp}")
    return url


def _get_supabase_client():
    from supabase import create_client

    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for Supabase storage")
    return create_client(url, key)


def _upload_supabase(path: str, data: bytes) -> str:
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "ai-images")
    client = _get_supabase_client()
    storage = client.storage.from_(bucket)
    storage.upload(
        path,
        data,
        file_options={"content-type": "image/png", "upsert": "true"},
    )
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    return f"{base}/storage/v1/object/public/{bucket}/{path}"


def _upload_local(filename: str, data: bytes) -> str:
    _STATIC_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    filepath = _STATIC_IMAGES_DIR / filename
    filepath.write_bytes(data)
    relative = f"/static/images/ai-generated/{filename}"
    api_base = (os.getenv("API_PUBLIC_BASE_URL") or "").rstrip("/")
    if api_base:
        return f"{api_base}{relative}"
    return relative


def persist_image_bytes(image_bytes: bytes, user_id: int, suffix: str = "") -> str:
    """Upload image bytes and return a public URL (or local path for dev fallback)."""
    provider = _provider()
    path = _object_path(user_id, suffix)

    if provider == "vercel":
        return _upload_vercel(path, image_bytes)
    if provider == "supabase":
        return _upload_supabase(path, image_bytes)

    filename = path.split("/")[-1]
    return _upload_local(filename, image_bytes)


def persist_image_from_base64(base64_data: str, user_id: int, suffix: str = "") -> str:
    return persist_image_bytes(base64.b64decode(base64_data), user_id, suffix)


def persist_image_from_url(url: str, user_id: int, suffix: str = "") -> str:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return persist_image_bytes(resp.content, user_id, suffix)


def persist_generation_result(result: str, user_id: int, suffix: str = "") -> str:
    """Persist Azure/OpenAI output: base64 string or temporary https URL."""
    if result.startswith("http://") or result.startswith("https://"):
        return persist_image_from_url(result, user_id, suffix)
    return persist_image_from_base64(result, user_id, suffix)


def local_static_dir() -> Path:
    """Directory used for in-memory logo overlay before upload (local temp file)."""
    return _STATIC_IMAGES_DIR
