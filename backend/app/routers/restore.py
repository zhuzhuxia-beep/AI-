import os
from fastapi import APIRouter, HTTPException
from app.routers.upload import photos_db, OUTPUT_DIR, _save_db
from app.services.restoration import restore_image

router = APIRouter()


@router.post("/restore/{photo_id}")
async def restore_photo(photo_id: str):
    photo = photos_db.get(photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")

    try:
        input_path = photo["filepath"]
        output_filename = f"{photo_id}_restored.jpg"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        # Run restoration pipeline
        restored_path = restore_image(input_path, output_path)

        # Update metadata
        photo["restored_path"] = output_filename
        photo["status"] = "restored"
        _save_db()

        return {
            "id": photo_id,
            "status": "restored",
            "restored_url": f"/outputs/{output_filename}",
        }
    except Exception as e:
        raise HTTPException(500, f"修复失败: {str(e)}")
