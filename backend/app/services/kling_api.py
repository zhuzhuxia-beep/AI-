"""
Kling AI (可灵) video generation API integration.

API documentation: https://www.klingai.com/api
Base URL: https://www.klingai.com/api
Authentication: Bearer token
"""

import requests
import json
import time
import os
import subprocess
from typing import Optional


API_BASE = "https://www.klingai.com/api"
API_KEY = os.environ.get("KLING_API_KEY", "")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def text_to_video(prompt: str, duration: int = 5, model: str = "kling-3.0") -> dict:
    """
    Create a text-to-video generation task.

    Args:
        prompt: Text description of the video to generate
        duration: Video duration in seconds (default: 5)
        model: Model name (default: kling-3.0)

    Returns:
        Task response with task_id for status polling
    """
    url = f"{API_BASE}/v1/videos/text2video"
    payload = {
        "model_name": model,
        "prompt": prompt,
        "duration": duration,
    }

    resp = requests.post(url, headers=HEADERS, json=payload, timeout=30)
    data = resp.json()

    if resp.status_code != 200 or data.get("status") != 0:
        error = data.get("error", {})
        raise Exception(
            f"Kling API error: {error.get('type', 'unknown')} - "
            f"{error.get('detail', data.get('message', 'unknown'))}"
        )

    return data.get("data", {})


def image_to_video(image_url: str, prompt: str = "", duration: int = 5) -> dict:
    """
    Create an image-to-video generation task (image as first frame).

    Args:
        image_url: Publicly accessible URL of the image
        prompt: Optional text description for motion guidance
        duration: Video duration in seconds

    Returns:
        Task response with task_id
    """
    url = f"{API_BASE}/v1/videos/image2video"
    payload = {
        "image_url": image_url,
        "prompt": prompt,
        "duration": duration,
    }

    resp = requests.post(url, headers=HEADERS, json=payload, timeout=30)
    data = resp.json()

    if resp.status_code != 200 or data.get("status") != 0:
        error = data.get("error", {})
        raise Exception(
            f"Kling image2video error: {error.get('type', 'unknown')} - "
            f"{error.get('detail', data.get('message', 'unknown'))}"
        )

    return data.get("data", {})


def query_task(task_id: str) -> dict:
    """
    Query the status and result of a generation task.

    Args:
        task_id: Task ID from text_to_video() or image_to_video()

    Returns:
        Task status data including video_url when complete
    """
    url = f"{API_BASE}/v1/videos/{task_id}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    data = resp.json()

    if resp.status_code != 200:
        raise Exception(f"Kling query error: {data.get('message', 'unknown')}")

    return data.get("data", {})


def wait_for_completion(task_id: str, poll_interval: int = 5, timeout: int = 300) -> dict:
    """
    Poll task status until complete or failed.

    Args:
        task_id: Task ID to poll
        poll_interval: Seconds between polls
        timeout: Max seconds to wait

    Returns:
        Completed task data with video_url
    """
    start = time.time()
    last_status = None

    while time.time() - start < timeout:
        data = query_task(task_id)
        task_status = data.get("task_status", {})

        status_code = task_status.get("status")
        status_desc = task_status.get("status_desc", "unknown")

        if status_code == 2:  # Success
            return data
        elif status_code == 3:  # Failed
            raise Exception(f"Kling task failed: {status_desc}")
        elif status_code == 4:  # Expired
            raise Exception("Kling task expired")

        if status_desc != last_status:
            print(f"  Kling task status: {status_desc}")
            last_status = status_desc

        time.sleep(poll_interval)

    raise TimeoutError(f"Kling task {task_id} timed out after {timeout}s")


def download_video(video_url: str, output_path: str) -> str:
    """
    Download generated video from Kling to local file.

    Args:
        video_url: URL from completed task data
        output_path: Local file path to save video

    Returns:
        Output file path
    """
    resp = requests.get(video_url, stream=True, timeout=120)
    resp.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return output_path


def combine_audio_video(video_path: str, audio_path: str, output_path: str) -> str:
    """
    Replace/overlay audio on generated video.

    Uses FFmpeg to combine Kling-generated video with TTS narration audio.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg audio overlay failed: {result.stderr[:200]}")

    return output_path


def generate_video_from_story(story_text: str, image_path: str, audio_path: str,
                               output_path: str, duration: float = None) -> str:
    """
    Full pipeline: generate AI video from story + combine with audio.

    1. Use story text as prompt for Kling text-to-video
    2. Download the generated video
    3. Overlay TTS narration audio
    4. Return final video path

    Args:
        story_text: User's story about the photo
        image_path: Path to restored photo (used for prompt enhancement)
        audio_path: Path to TTS narration audio
        output_path: Final output MP4 path
        duration: Target video duration (auto from audio)
    """
    if duration is None:
        # Get audio duration
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                capture_output=True, text=True
            )
            duration = float(result.stdout.strip()) if result.returncode == 0 else 10.0
        except:
            duration = 10.0

    # Build a rich prompt from the story
    prompt = build_prompt(story_text, image_path)

    print(f"  Kling prompt: {prompt[:100]}...")
    print(f"  Duration: {duration}s")

    # Step 1: Create video generation task
    task_data = text_to_video(prompt=prompt, duration=min(int(duration), 10))
    task_id = task_data.get("task_id") or task_data.get("id")
    print(f"  Task ID: {task_id}")

    # Step 2: Wait for completion
    result = wait_for_completion(task_id)
    video_url = (
        result.get("videos", [{}])[0].get("url")
        or result.get("video_url")
        or result.get("url")
    )
    if not video_url:
        raise Exception(f"No video URL in result: {json.dumps(result, ensure_ascii=False)[:200]}")

    # Step 3: Download video
    temp_video = output_path.replace(".mp4", "_raw_kling.mp4")
    download_video(video_url, temp_video)
    print(f"  Downloaded: {os.path.getsize(temp_video) / 1024:.0f}KB")

    # Step 4: Overlay audio
    combine_audio_video(temp_video, audio_path, output_path)

    # Cleanup
    os.remove(temp_video)

    return output_path


def build_prompt(story_text: str, image_path: str = None) -> str:
    """
    Build a rich video generation prompt from the user's story.
    Adds cinematic context based on story mood.
    """
    # Detect mood for style guidance
    warm_kw = ["快乐", "幸福", "开心", "美好", "温暖", "甜蜜", "喜悦", "感动", "笑容", "爱"]
    nostalgic_kw = ["当年", "那年", "曾经", "过去", "岁月", "时光", "青春", "少年", "以前", "回忆"]

    has_warm = any(w in story_text for w in warm_kw)
    has_nostalgic = any(w in story_text for w in nostalgic_kw)

    # Build style prefix
    if has_nostalgic and not has_warm:
        style = "怀旧复古风格，暖色调，胶片质感，缓缓推进的镜头"
    elif has_warm:
        style = "温馨感人风格，柔光暖色调，温情氛围，缓慢细腻的运镜"
    else:
        style = "电影感叙事风格，自然光效，细腻质感"

    # Limit prompt length
    full_prompt = f"{style}。{story_text}"
    if len(full_prompt) > 500:
        full_prompt = full_prompt[:497] + "..."

    return full_prompt
