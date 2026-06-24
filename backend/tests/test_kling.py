"""Quick test of Kling API endpoints."""
import requests, json

API_KEY = "0ZO53nMi3FHWEeHl6R5V9Fj6_vKiIMTd_eefg0TkG0s"

urls = [
    "https://www.klingai.com/api/v1/videos/text2video",
    "https://klingapi.com/api/v1/video/generate",
]

for url in urls:
    try:
        if "klingai.com" in url:
            headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
            r = requests.post(url, headers=headers,
                            json={"model_name": "kling-v1", "prompt": "test", "duration": 5}, timeout=15)
        else:
            r = requests.post(url, json={"prompt": "test", "key": API_KEY}, timeout=15)
        print(f"{url}: {r.status_code}")
        print(f"  {r.text[:200]}")
    except Exception as e:
        print(f"{url}: error - {e}")
