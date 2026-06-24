"""
Video composer: Ken Burns effect photo + story subtitles + mood color grading + background music.

Two-phase approach:
  1. Mix narration audio with mood-based background music
  2. Create video from photo with Ken Burns zoom/pan effect + mixed audio
  3. Burn SRT subtitles
"""

import subprocess, os, re, shutil, glob


def _find_ffmpeg():
    """
    Find a full-featured FFmpeg binary.

    The TRAE-bundled FFmpeg is extremely stripped down (no zoompan, no audio
    codecs, no image decoders). We search for a full build in common locations:
    winget install path, system PATH (non-TRAE), chocolatey, etc.
    """
    # 1. Check common full-build locations
    candidates = []

    # winget Gyan.FFmpeg full build
    winget_base = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Microsoft", "WinGet", "Packages"
    )
    if os.path.isdir(winget_base):
        for d in os.listdir(winget_base):
            if "Gyan.FFmpeg" in d or "ffmpeg" in d.lower():
                base = os.path.join(winget_base, d)
                # Search for bin/ffmpeg.exe recursively
                for root, dirs, files in os.walk(base):
                    if "ffmpeg.exe" in files:
                        candidates.append(os.path.join(root, "ffmpeg.exe"))

    # chocolatey
    choco = shutil.which("ffmpeg")
    if choco and "TRAE" not in choco and "trae" not in choco:
        candidates.append(choco)

    # System PATH entries (skip TRAE bundled)
    for p in os.environ.get("PATH", "").split(os.pathsep):
        exe = os.path.join(p, "ffmpeg.exe")
        if os.path.isfile(exe) and "TRAE" not in p and "trae" not in p.lower():
            candidates.append(exe)

    # Test each candidate for zoompan support
    for exe in candidates:
        try:
            r = subprocess.run(
                [exe, "-filters"],
                capture_output=True, text=True, timeout=5
            )
            # FFmpeg outputs filters to stderr (version info) + stdout (filter list)
            combined = r.stdout + r.stderr
            if r.returncode == 0 and "zoompan" in combined:
                return exe
        except Exception:
            continue

    # Fallback: return "ffmpeg" and hope for the best
    return "ffmpeg"


def _find_ffprobe(ffmpeg_path):
    """Find ffprobe next to the discovered ffmpeg."""
    if ffmpeg_path and ffmpeg_path != "ffmpeg":
        d = os.path.dirname(ffmpeg_path)
        probe = os.path.join(d, "ffprobe.exe")
        if os.path.isfile(probe):
            return probe
        probe = os.path.join(d, "ffprobe")
        if os.path.isfile(probe):
            return probe
    return "ffprobe"


# Detect full FFmpeg on module load
FFMPEG = _find_ffmpeg()
FFPROBE = _find_ffprobe(FFMPEG)


def compose_video(image_path, audio_path, output_path, duration=None, story_text=""):
    if duration is None:
        duration = get_audio_duration(audio_path) or 15.0

    mood = analyze_mood(story_text)
    phrases = split_into_phrases(story_text)

    # Phase 0: Generate background music and mix with narration
    mixed_audio = output_path.replace(".mp4", "_mixed.mp3")
    add_background_music(audio_path, mixed_audio, duration, mood)

    # Phase 1: Ken Burns effect video with mixed audio
    temp_video = output_path.replace(".mp4", "_temp.mp4")
    fps = 30
    color_filter = mood["ffmpeg_color"]
    total_frames = int(duration * fps)

    # Ken Burns: slow zoom-in with slight pan, gives photos "life"
    # zoompan works on a virtual canvas; we upscale first for quality
    ken_burns = (
        f"[0:v]scale=2560:-1,"
        f"zoompan=z='min(zoom+0.0008,1.5)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={total_frames}:s=1920x1080:fps={fps},"
        f"{color_filter}[vo]"
    )

    cmd1 = [
        FFMPEG, "-y",
        "-loop", "1", "-i", image_path,
        "-i", mixed_audio,
        "-filter_complex", ken_burns,
        "-map", "[vo]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        temp_video,
    ]

    result1 = subprocess.run(cmd1, capture_output=True, text=True)
    if result1.returncode != 0:
        raise RuntimeError(f"Phase 1 (Ken Burns video) failed: ...{result1.stderr[-500:]}")

    # Clean up mixed audio
    if os.path.exists(mixed_audio):
        os.remove(mixed_audio)

    # Phase 2: Burn subtitles
    if phrases:
        srt_path = output_path.replace(".mp4", ".srt")
        create_srt(phrases, duration, srt_path)
        # FFmpeg subtitles filter needs forward slashes and proper escaping on Windows
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

        cmd2 = [
            FFMPEG, "-y",
            "-i", temp_video,
            "-vf", f"subtitles='{srt_escaped}'",
            "-c:a", "copy",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            output_path,
        ]

        result2 = subprocess.run(cmd2, capture_output=True, text=True)
        if result2.returncode != 0:
            # If subtitle burning fails, use video without subtitles
            shutil.copy2(temp_video, output_path)
    else:
        shutil.copy2(temp_video, output_path)

    if os.path.exists(temp_video):
        os.remove(temp_video)
    return output_path


def add_background_music(narration_path, output_path, duration, mood):
    """
    Generate mood-based background music and mix it with narration.

    Uses FFmpeg's audio filters to create atmospheric ambient music
    without requiring any external audio files or APIs.

    - Warm mood: soft piano-like chord pad (C major)
    - Nostalgic mood: gentle minor-key ambient
    - Neutral: subtle soft pad
    """
    mood_type = mood["mood"]
    base_freq = mood["bgm_freq"]

    # Generate ambient background music using FFmpeg
    # Uses a combination of filtered noise and sine tones for a pad-like sound
    bgm_path = output_path.replace(".mp3", "_bgm.mp3")

    # Frame size for stable filtering
    bgm_cmd = [
        FFMPEG, "-y",
        "-f", "lavfi", "-i",
        f"anoisesrc=d={duration}:c=pink:a=0.3,"
        f"lowpass=f={base_freq + 200}:p=1,"
        f"highpass=f={base_freq - 100}:p=1,"
        f"volume=0.08",
        "-f", "lavfi", "-i",
        f"sine=f={base_freq}:d={duration}:r=44100,volume=0.04",
        "-f", "lavfi", "-i",
        f"sine=f={base_freq * 1.25}:d={duration}:r=44100,volume=0.03",
        "-filter_complex",
        f"[0:a][1:a][2:a]amix=inputs=3:duration=first:weights=1 0.5 0.3[a]",
        "-map", "[a]",
        "-c:a", "libmp3lame", "-b:a", "64k",
        bgm_path,
    ]

    bgm_result = subprocess.run(bgm_cmd, capture_output=True, text=True)
    if bgm_result.returncode != 0:
        # If BGM generation fails, just copy narration as-is
        shutil.copy2(narration_path, output_path)
        return

    # Mix narration with background music
    mix_cmd = [
        FFMPEG, "-y",
        "-i", narration_path,
        "-i", bgm_path,
        "-filter_complex",
        "[0:a][1:a]amix=inputs=2:duration=first:weights=1 0.3[a]",
        "-map", "[a]",
        "-c:a", "libmp3lame", "-b:a", "128k",
        output_path,
    ]

    mix_result = subprocess.run(mix_cmd, capture_output=True, text=True)
    if os.path.exists(bgm_path):
        os.remove(bgm_path)

    if mix_result.returncode != 0:
        shutil.copy2(narration_path, output_path)


def create_srt(phrases, duration, srt_path):
    """Create SRT subtitle with timing based on character proportion."""
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

    # Visual: FFmpeg eq filter parameters
    colors = {
        "warm": "eq=brightness=0.03:contrast=1.03:saturation=1.05:gamma=1.05",
        "nostalgic": "eq=brightness=-0.02:contrast=1.08:saturation=0.80:gamma=0.95",
        "neutral": "eq=brightness=0.0:contrast=1.0:saturation=1.0",
    }

    # Audio: background music base frequency (Hz) for each mood
    # Warm = C major (happy, bright), Nostalgic = A minor (melancholic)
    bgm_freqs = {
        "warm": 262,    # Middle C
        "nostalgic": 220,  # A3 (minor feel)
        "neutral": 247,    # B3 (neutral)
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
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return float(r.stdout.strip())
    except:
        pass
    return None
