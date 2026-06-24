"""
Text-to-Speech service using Edge TTS (free, no API key required).

For Demo phase, Edge TTS provides natural Chinese voice output.
Production could use: 火山引擎 TTS, Azure TTS, or OpenAI TTS.
"""

import edge_tts


async def text_to_speech(text: str, output_path: str, voice: str = "zh-CN-XiaoxiaoNeural"):
    """
    Convert text to speech and save as MP3.

    Args:
        text: Chinese text to speak
        output_path: Output MP3 file path
        voice: Edge TTS voice name (default: 晓晓 - warm female voice)
    """
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
