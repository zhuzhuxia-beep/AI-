import os
import uuid
import json
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image

router = APIRouter()
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
DB_FILE = "photos_db.json"

# File-backed store (survives restarts)
photos_db = {}


def _load_db():
    """Load photo metadata from JSON file on startup."""
    global photos_db
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                photos_db = json.load(f)
        except (json.JSONDecodeError, IOError):
            photos_db = {}


def _save_db():
    """Persist photo metadata to JSON file."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(photos_db, f, ensure_ascii=False, indent=2)
    except IOError:
        pass


# Load existing data on module import
_load_db()


@router.post("/upload")
async def upload_photo(file: UploadFile = File(...)):
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/bmp"]
    if file.content_type not in allowed_types:
        raise HTTPException(400, f"不支持的文件类型: {file.content_type}")

    # Validate file size (20MB)
    contents = await file.read()
    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(400, "文件大小不能超过 20MB")

    # Generate ID and save
    photo_id = str(uuid.uuid4())[:8]
    ext = file.filename.split(".")[-1] if "." in (file.filename or "") else "jpg"
    filename = f"{photo_id}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(contents)

    # Get image info
    img = Image.open(filepath)
    width, height = img.size

    # Store metadata
    photos_db[photo_id] = {
        "id": photo_id,
        "original_filename": file.filename,
        "filename": filename,
        "filepath": filepath,
        "width": width,
        "height": height,
        "status": "uploaded",
        "restored_path": None,
        "story": None,
        "audio_path": None,
        "video_path": None,
    }
    _save_db()

    return {
        "id": photo_id,
        "filename": file.filename,
        "width": width,
        "height": height,
        "status": "uploaded",
    }


@router.get("/photo/{photo_id}")
async def get_photo(photo_id: str):
    photo = photos_db.get(photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")

    return {
        "id": photo["id"],
        "original_filename": photo["original_filename"],
        "width": photo["width"],
        "height": photo["height"],
        "status": photo["status"],
        "original_url": f"/uploads/{photo['filename']}",
        "restored_url": f"/outputs/{photo['restored_path']}" if photo.get("restored_path") else None,
        "audio_url": f"/outputs/{photo['audio_path']}" if photo.get("audio_path") else None,
        "video_url": f"/outputs/{photo['video_path']}" if photo.get("video_path") else None,
    }


@router.get("/gallery")
async def get_gallery(limit: int = 12):
    """Return completed photos for showcase gallery."""
    all_completed = [
        {
            "id": p["id"],
            "original_url": f"/uploads/{p['filename']}",
            "restored_url": f"/outputs/{p['restored_path']}",
            "video_url": f"/outputs/{p['video_path']}",
            "story": p.get("story", ""),
        }
        for p in photos_db.values()
        if p.get("video_path") and p.get("restored_path")
    ]
    return {"photos": all_completed[:limit], "total": len(all_completed)}
