"""Small Flask proxy example for a hypothetical 'gork' image provider.

This proxy simulates or wraps a real SDK. POST JSON to /v1/generate with
{ "prompt": "...", "cref": "..." } and it returns a JSON response with
an image URL in `data[0].url` similar to many image providers.

Run locally for development:
    python scripts/gork_image_proxy.py

Then point IMAGE_API_URL to http://localhost:9090/v1/generate
"""
import os
import json
import time
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/v1/generate", methods=["POST"])
def generate():
    payload = request.get_json(force=True)
    prompt = payload.get("prompt") or ""
    cref = payload.get("cref")

    # Simulate some processing time
    time.sleep(0.2)

    # Simulate generating a stable URL path based on a hash of prompt + cref
    key = (prompt + (cref or "")).encode("utf-8")
    import hashlib

    h = hashlib.sha1(key).hexdigest()[:10]
    image_url = f"https://gork.example/content/{h}.png"

    # Return a response shape similar to provider APIs: data: [{ url: ... }]
    return jsonify({"data": [{"url": image_url, "meta": {"provider": "gork"}}]})


if __name__ == "__main__":
    port = int(os.getenv("GORK_PROXY_PORT", "9090"))
    app.run(host="0.0.0.0", port=port)
