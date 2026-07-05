import os, subprocess
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.routers.upload import photos_db, OUTPUT_DIR, _save_db
from app.services.video_composer import compose_video, FFMPEG, FFPROBE

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

        compose_video(
            image_path=os.path.join(OUTPUT_DIR, photo["restored_path"]),
            audio_path=os.path.join(OUTPUT_DIR, photo["audio_path"]),
            output_path=video_path,
            story_text=story_text,
        )

        photo["video_path"] = video_filename
        photo["status"] = "completed"
        _save_db()

        return {
            "id": photo_id,
            "status": "completed",
            "video_url": f"/outputs/{video_filename}",
        }
    except Exception as e:
        import traceback
        detail = f"视频生成失败: {str(e)}"
        tb = traceback.format_exc()
        print(f"[VIDEO ERROR] {detail}\n{tb}")
        # Return detailed error so frontend can display it
        return JSONResponse(
            status_code=500,
            content={"detail": detail, "traceback": tb[-800:] if len(tb) > 800 else tb},
        )


@router.get("/debug/{photo_id}")
async def debug_video(photo_id: str):
    """Diagnostic endpoint: check all prerequisites for video generation."""
    photo = photos_db.get(photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")

    info = {"photo_id": photo_id, "checks": {}}

    # Check restored image
    restored_name = photo.get("restored_path", "")
    restored_full = os.path.join(OUTPUT_DIR, restored_name)
    info["checks"]["restored_path"] = {
        "db_value": restored_name,
        "exists": os.path.isfile(restored_full),
        "size": os.path.getsize(restored_full) if os.path.isfile(restored_full) else 0,
    }

    # Check audio file
    audio_name = photo.get("audio_path", "")
    audio_full = os.path.join(OUTPUT_DIR, audio_name)
    info["checks"]["audio_path"] = {
        "db_value": audio_name,
        "exists": os.path.isfile(audio_full),
        "size": os.path.getsize(audio_full) if os.path.isfile(audio_full) else 0,
    }

    # Check FFmpeg
    info["checks"]["ffmpeg"] = {"path": FFMPEG}
    try:
        r = subprocess.run([FFMPEG, "-version"], capture_output=True, text=True, timeout=5)
        info["checks"]["ffmpeg"]["available"] = r.returncode == 0
        info["checks"]["ffmpeg"]["version"] = r.stderr.split("\n")[0] if r.stderr else r.stdout.split("\n")[0]
    except Exception as e:
        info["checks"]["ffmpeg"]["available"] = False
        info["checks"]["ffmpeg"]["error"] = str(e)

    # Check FFmpeg filters
    try:
        r = subprocess.run([FFMPEG, "-filters"], capture_output=True, text=True, timeout=5)
        filters = r.stdout + r.stderr
        info["checks"]["ffmpeg_filters"] = {
            "zoompan": "zoompan" in filters,
            "amix": "amix" in filters,
            "subtitles": "subtitles" in filters,
            "anoisesrc": "anoisesrc" in filters,
            "sine": "sine" in filters,
            "libx264": "libx264" in filters,
        }
    except Exception as e:
        info["checks"]["ffmpeg_filters"] = {"error": str(e)}

    # Check encoders
    try:
        r = subprocess.run([FFMPEG, "-encoders"], capture_output=True, text=True, timeout=5)
        encoders = r.stdout + r.stderr
        info["checks"]["encoders"] = {
            "aac": "aac" in encoders,
            "libx264": "libx264" in encoders,
        }
    except Exception as e:
        info["checks"]["encoders"] = {"error": str(e)}

    # Try a minimal FFmpeg test
    test_out = os.path.join(OUTPUT_DIR, "_test_ffmpeg.mp4")
    try:
        cmd = [FFMPEG, "-y", "-f", "lavfi", "-i", "color=c=red:s=320x240:d=1",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", test_out]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        info["checks"]["test_encode"] = {
            "success": r.returncode == 0,
            "stderr_tail": r.stderr[-300:] if r.returncode != 0 else "",
        }
        if os.path.exists(test_out):
            os.remove(test_out)
    except Exception as e:
        info["checks"]["test_encode"] = {"success": False, "error": str(e)}

    return info
