from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from app.routers import upload, restore, story, video
from app.services.video_composer import FFMPEG
import os, sys, subprocess, pathlib

app = FastAPI(title="AI 老照片时光机", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
os.makedirs("outputs", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

# Serve uploaded photos and generated outputs
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# API routers
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(restore.router, prefix="/api", tags=["restore"])
app.include_router(story.router, prefix="/api", tags=["story"])
app.include_router(video.router, prefix="/api", tags=["video"])


@app.get("/api/health")
async def health():
    ffmpeg_ok = False
    try:
        cmd = [FFMPEG, "-version"] if FFMPEG != "ffmpeg" else ["ffmpeg", "-version"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        ffmpeg_ok = r.returncode == 0
    except:
        pass
    return {
        "status": "ok",
        "service": "AI 老照片时光机",
        "ffmpeg": ffmpeg_ok,
        "ffmpeg_path": FFMPEG,
    }


# ---- Production: serve frontend static files ----
# In production (Docker), frontend is built into backend/static/
STATIC_DIR = pathlib.Path(__file__).parent.parent / "static"

if STATIC_DIR.exists():
    # Serve assets (JS, CSS, images)
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """
        SPA fallback: serve index.html for all non-API, non-file routes.
        This enables React Router to handle client-side routing.
        """
        # Don't intercept API routes
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)

        # Try to serve a real file first
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))

        # Fallback to index.html for SPA routing
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return JSONResponse({"detail": "Not Found"}, status_code=404)
