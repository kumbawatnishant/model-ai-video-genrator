"""Small Flask proxy example that simulates a video provider (Luma-like).

POST JSON { "image_url": "...", "duration": 5 } to /v1/animate and it returns
{ "video_url": "https://videos.example/...mp4" }.

Run locally for development:
    python scripts/luma_video_proxy.py
"""
import os
import time
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/v1/animate', methods=['POST'])
def animate():
    payload = request.get_json(force=True)
    image_url = payload.get('image_url') or payload.get('image') or ''
    duration = int(payload.get('duration', 5))

    # Simulate work
    time.sleep(0.2)

    # Create deterministic video URL from image_url
    key = (image_url + str(duration)).encode('utf-8')
    h = hashlib.sha1(key).hexdigest()[:12]
    video_url = f"https://videos.example/{h}.mp4"

    return jsonify({"video_url": video_url})


if __name__ == '__main__':
    port = int(os.getenv('LUMA_PROXY_PORT', '9091'))
    app.run(host='0.0.0.0', port=port)
