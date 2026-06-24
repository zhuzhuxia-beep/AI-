import os
from fastapi import APIRouter, HTTPException
from app.routers.upload import photos_db, OUTPUT_DIR, _save_db
from app.services.video_composer import compose_video

router = APIRouter()


@router.post("/video/{photo_id}")
async def generate_video(photo_id: str):
    photo = photos_db.get(photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")

    if not photo.get("restored_path"):
        raise HTTPException(400, "请先完成照片修复")

    if not photo.get("audio_path"):
        raise HTTPException(400, "请先生成故事配音")

    try:
        video_filename = f"{photo_id}_memory.mp4"
        video_path = os.path.join(OUTPUT_DIR, video_filename)
        story_text = photo.get("story", "")

        # FFmpeg video generation with Ken Burns zoom
        compose_video(
            image_path=os.path.join(OUTPUT_DIR, photo["restored_path"]),
            audio_path=os.path.join(OUTPUT_DIR, photo["audio_path"]),
            output_path=video_path,
            story_text=story_text,
        )

        # Update metadata
        photo["video_path"] = video_filename
        photo["status"] = "completed"
        _save_db()

        return {
            "id": photo_id,
            "status": "completed",
            "video_url": f"/outputs/{video_filename}",
        }
    except Exception as e:
        raise HTTPException(500, f"视频生成失败: {str(e)}")
