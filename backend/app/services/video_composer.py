"""
Video composer: Ken Burns effect photo + story subtitles + mood color grading + background music.

Robust multi-stage pipeline with graceful degradation:
  1. Try full pipeline: BGM + Ken Burns + subtitles
  2. If BGM fails: Ken Burns + narration + subtitles
  3. If subtitles fail: Ken Burns + narration only
  4. If Ken Burns fails: simple video from image + narration
"""

import subprocess, os, re, shutil, sys, logging

logger = logging.getLogger(__name__)


def _find_ffmpeg():
    """Find a full-featured FFmpeg binary."""
    if sys.platform != "win32":
        path = shutil.which("ffmpeg")
        return path if path else "ffmpeg"

    candidates = []
    winget_base = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Microsoft", "WinGet", "Packages"
    )
    if os.path.isdir(winget_base):
        for d in os.listdir(winget_base):
            if "Gyan.FFmpeg" in d or "ffmpeg" in d.lower():
                base = os.path.join(winget_base, d)
                for root, dirs, files in os.walk(base):
                    if "ffmpeg.exe" in files:
                        candidates.append(os.path.join(root, "ffmpeg.exe"))

    choco = shutil.which("ffmpeg")
    if choco and "TRAE" not in choco and "trae" not in choco:
        candidates.append(choco)

    for p in os.environ.get("PATH", "").split(os.pathsep):
        exe = os.path.join(p, "ffmpeg.exe")
        if os.path.isfile(exe) and "TRAE" not in p and "trae" not in p.lower():
            candidates.append(exe)

    for exe in candidates:
        try:
            r = subprocess.run([exe, "-filters"], capture_output=True, text=True, timeout=5)
            combined = r.stdout + r.stderr
            if r.returncode == 0 and "zoompan" in combined:
                return exe
        except Exception:
            continue

    return "ffmpeg"


def _find_ffprobe(ffmpeg_path):
    """Find ffprobe next to the discovered ffmpeg."""
    if ffmpeg_path and ffmpeg_path != "ffmpeg":
        d = os.path.dirname(ffmpeg_path)
        for name in ("ffprobe.exe", "ffprobe"):
            probe = os.path.join(d, name)
            if os.path.isfile(probe):
                return probe
    probe = shutil.which("ffprobe")
    return probe if probe else "ffprobe"


FFMPEG = _find_ffmpeg()
FFPROBE = _find_ffprobe(FFMPEG)


def _run_ffmpeg(cmd, label="ffmpeg"):
    """Run an FFmpeg command and return (success, stderr_tail)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            err_tail = result.stderr[-800:] if result.stderr else "(no stderr)"
            logger.warning(f"{label} failed: {err_tail}")
            return False, err_tail
        return True, ""
    except subprocess.TimeoutExpired:
        return False, f"{label} timed out after 120s"
    except Exception as e:
        return False, str(e)


def compose_video(image_path, audio_path, output_path, duration=None, story_text=""):
    """
    Compose a memory video with graceful degradation.
    Each stage has a fallback so the video is always produced if possible.
    """
    if duration is None:
        duration = get_audio_duration(audio_path) or 15.0
    duration = max(3.0, min(duration, 120.0))  # clamp to reasonable range

    mood = analyze_mood(story_text)
    phrases = split_into_phrases(story_text)
    fps = 30
    total_frames = int(duration * fps)
    color_filter = mood["ffmpeg_color"]

    # --- Stage 1: Prepare audio (narration + optional BGM) ---
    mixed_audio = output_path.replace(".mp4", "_mixed.aac")
    bgm_ok = try_make_mixed_audio(audio_path, mixed_audio, duration, mood)
    final_audio = mixed_audio if bgm_ok else audio_path

    # --- Stage 2: Ken Burns video with audio ---
    temp_video = output_path.replace(".mp4", "_temp.mp4")
    kb_ok = try_ken_burns(image_path, final_audio, temp_video, duration, fps, total_frames, color_filter)

    if not kb_ok:
        # Fallback: simple video without Ken Burns effect
        kb_ok = try_simple_video(image_path, final_audio, temp_video, duration)

    if not kb_ok:
        raise RuntimeError("All video generation strategies failed. Check FFmpeg installation.")

    # Clean up mixed audio
    if bgm_ok and os.path.exists(mixed_audio):
        os.remove(mixed_audio)

    # --- Stage 3: Burn subtitles (optional, has fallback) ---
    if phrases:
        srt_path = output_path.replace(".mp4", ".srt")
        create_srt(phrases, duration, srt_path)
        sub_ok = try_burn_subtitles(temp_video, srt_path, output_path)
        if not sub_ok:
            shutil.copy2(temp_video, output_path)
        if os.path.exists(srt_path):
            os.remove(srt_path)
    else:
        shutil.copy2(temp_video, output_path)

    if os.path.exists(temp_video):
        os.remove(temp_video)

    return output_path


def try_make_mixed_audio(narration_path, output_path, duration, mood):
    """Generate background music and mix with narration. Returns True on success."""
    bgm_path = output_path.replace(".aac", "_bgm.aac")
    base_freq = mood["bgm_freq"]

    # Generate ambient BGM
    bgm_cmd = [
        FFMPEG, "-y",
        "-f", "lavfi", "-i",
        f"anoisesrc=d={duration}:c=pink:a=0.3,"
        f"lowpass=f={int(base_freq + 200)}:p=1,"
        f"highpass=f={max(20, int(base_freq - 100))}:p=1,"
        f"volume=0.08",
        "-f", "lavfi", "-i",
        f"sine=f={int(base_freq)}:d={duration}:r=44100,volume=0.04",
        "-f", "lavfi", "-i",
        f"sine=f={int(base_freq * 1.25)}:d={duration}:r=44100,volume=0.03",
        "-filter_complex",
        f"[0:a][1:a][2:a]amix=inputs=3:duration=first:weights=1 0.5 0.3[a]",
        "-map", "[a]",
        "-c:a", "aac", "-b:a", "64k",
        bgm_path,
    ]

    ok, err = _run_ffmpeg(bgm_cmd, "BGM generation")
    if not ok:
        # BGM failed — not fatal, narration alone is fine
        return False

    # Mix narration with BGM
    mix_cmd = [
        FFMPEG, "-y",
        "-i", narration_path,
        "-i", bgm_path,
        "-filter_complex",
        "[0:a][1:a]amix=inputs=2:duration=first:weights=1 0.3[a]",
        "-map", "[a]",
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ]

    ok, err = _run_ffmpeg(mix_cmd, "audio mixing")
    if os.path.exists(bgm_path):
        os.remove(bgm_path)

    if not ok:
        return False
    return True


def try_ken_burns(image_path, audio_path, output_path, duration, fps, total_frames, color_filter):
    """Create Ken Burns zoom/pan video. Returns True on success."""
    ken_burns = (
        f"[0:v]scale=2560:-1,"
        f"zoompan=z='min(zoom+0.0008,1.5)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={total_frames}:s=1920x1080:fps={fps},"
        f"{color_filter}[vo]"
    )

    cmd = [
        FFMPEG, "-y",
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-filter_complex", ken_burns,
        "-map", "[vo]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        output_path,
    ]

    ok, err = _run_ffmpeg(cmd, "Ken Burns video")
    return ok


def try_simple_video(image_path, audio_path, output_path, duration):
    """Fallback: simple video with static image + audio. Returns True on success."""
    cmd = [
        FFMPEG, "-y",
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        output_path,
    ]

    ok, err = _run_ffmpeg(cmd, "simple video fallback")
    return ok


def try_burn_subtitles(input_video, srt_path, output_path):
    """Burn SRT subtitles into video. Returns True on success."""
    # On Linux, paths don't need colon escaping; on Windows they do
    if sys.platform == "win32":
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
    else:
        srt_escaped = srt_path

    cmd = [
        FFMPEG, "-y",
        "-i", input_video,
        "-vf", f"subtitles={srt_escaped}",
        "-c:a", "copy",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        output_path,
    ]

    ok, err = _run_ffmpeg(cmd, "subtitle burning")
    return ok


def create_srt(phrases, duration, srt_path):
    """Create SRT subtitle file."""
    n = len(phrases)
    if n == 0:
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("")
        return

    char_counts = [len(p) for p in phrases]
    total_chars = max(sum(char_counts), 1)
    lines = []

    def fmt(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    cum_chars = 0
    for i, phrase in enumerate(phrases):
        if not phrase.strip():
            continue
        cum_chars += char_counts[i]
        start = (cum_chars - char_counts[i]) / total_chars * duration
        end = cum_chars / total_chars * duration
        if end - start < 1.0:
            end = min(start + 1.0, duration)
        lines.append(str(i + 1))
        lines.append(f"{fmt(start)} --> {fmt(end)}")
        lines.append(phrase.strip())
        lines.append("")

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def analyze_mood(story):
    """Analyze story mood and return visual/audio parameters."""
    warm_kw = ["快乐", "幸福", "开心", "美好", "温暖", "甜蜜", "喜悦", "感动", "笑容", "爱"]
    sad_kw = ["思念", "想念", "怀念", "离别", "泪", "伤感", "遗憾", "失去"]
    scores = {"warm": sum(1 for w in warm_kw if w in story),
              "sad": sum(1 for w in sad_kw if w in story)}

    if scores["sad"] > scores["warm"]:
        mood = "nostalgic"
    elif scores["warm"] >= scores["sad"]:
        mood = "warm"
    else:
        mood = "neutral"

    colors = {
        "warm": "eq=brightness=0.03:contrast=1.03:saturation=1.05:gamma=1.05",
        "nostalgic": "eq=brightness=-0.02:contrast=1.08:saturation=0.80:gamma=0.95",
        "neutral": "eq=brightness=0.0:contrast=1.0:saturation=1.0",
    }

    bgm_freqs = {
        "warm": 262,
        "nostalgic": 220,
        "neutral": 247,
    }

    return {
        "mood": mood,
        "ffmpeg_color": colors.get(mood, colors["neutral"]),
        "bgm_freq": bgm_freqs.get(mood, bgm_freqs["neutral"]),
    }


def split_into_phrases(text, max_phrases=5):
    if not text or not text.strip():
        return []
    parts = re.split(r"[。，！？；、\n]", text)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) > max_phrases:
        merged = [parts[0]]
        chunk_size = max(1, (len(parts) - 2) // (max_phrases - 2))
        for i in range(1, len(parts) - 1, chunk_size):
            chunk = "".join(parts[i:i + chunk_size]).strip()
            if chunk:
                merged.append(chunk)
        merged.append(parts[-1])
        parts = merged[:max_phrases]
    return parts


def get_audio_duration(audio_path):
    try:
        cmd = [FFPROBE, "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return float(r.stdout.strip())
    except:
        pass
    return None
