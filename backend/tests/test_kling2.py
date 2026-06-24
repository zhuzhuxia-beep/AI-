"""Test Kling API endpoints."""
import requests, json

API_KEY="0ZO53nMi3FHWEeHl6R5V9Fj6_vKiIMTd_eefg0TkG0s"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
BASE = "https://www.klingai.com/api"

# Test text2video
payload = {"prompt": "夕阳下的老照片，温馨怀旧风格，暖色调，画面中出现一位慈祥的老奶奶", "duration": 5}
r = requests.post(f"{BASE}/v1/videos/text2video", headers=HEADERS, json=payload, timeout=30)
print(f"Status: {r.status_code}")
data = r.json()
print(f"Response: {json.dumps(data, ensure_ascii=False)[:500]}")
