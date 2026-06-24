import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.routers.upload import photos_db, OUTPUT_DIR, _save_db
from app.services.tts import text_to_speech

router = APIRouter()


class StoryRequest(BaseModel):
    story: str


@router.post("/story/{photo_id}")
async def generate_story_narration(photo_id: str, req: StoryRequest):
    photo = photos_db.get(photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")

    if not req.story.strip():
        raise HTTPException(400, "故事内容不能为空")

    try:
        audio_filename = f"{photo_id}_narration.mp3"
        audio_path = os.path.join(OUTPUT_DIR, audio_filename)

        # Generate TTS
        await text_to_speech(req.story, audio_path)

        # Update metadata
        photo["story"] = req.story
        photo["audio_path"] = audio_filename
        photo["status"] = "narrated"
        _save_db()

        return {
            "id": photo_id,
            "status": "narrated",
            "audio_url": f"/outputs/{audio_filename}",
        }
    except Exception as e:
        raise HTTPException(500, f"配音生成失败: {str(e)}")
