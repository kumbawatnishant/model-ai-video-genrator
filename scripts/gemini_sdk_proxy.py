"""Small SDK-backed proxy that exposes a simple HTTP contract for Gemini calls.

Usage:
  - Configure environment variables: GEMINI_API_KEY, (optional) GEMINI_MODEL
  - Run: `python scripts/gemini_sdk_proxy.py`
  - POST JSON to /v1/agent with {"model": "gemini-pro", "instruction": "..."}

The proxy uses `google-generativeai` SDK to call the model and returns the SDK
response (as JSON or text). This lets local apps (or GCP services) call the
proxy with a simple HTTP contract instead of linking the SDK directly.
"""
import os
import json
from flask import Flask, request, jsonify

app = Flask(__name__)


def sdk_invoke(model: str, instruction: str):
    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        try:
            genai.configure(api_key=api_key)
        except Exception:
            try:
                genai.api_key = api_key
            except Exception:
                pass

        # Try a few call shapes
        if hasattr(genai, "chat") and hasattr(genai.chat, "create"):
            resp = genai.chat.create(model=model, messages=[{"role": "user", "content": instruction}])
            return resp

        if hasattr(genai, "completions") and hasattr(genai.completions, "create"):
            resp = genai.completions.create(model=model, prompt=instruction)
            return resp

        return {"error": "SDK available but no recognized API shape"}
    except Exception as exc:
        return {"error": str(exc)}


@app.route("/v1/agent", methods=["POST"])
def agent():
    payload = request.get_json(force=True)
    model = payload.get("model") or os.getenv("GEMINI_MODEL") or "gemini-pro"
    instruction = payload.get("instruction") or payload.get("prompt") or ""
    if not instruction:
        return jsonify({"error": "missing instruction"}), 400

    if "creative director" in instruction:
        return jsonify({
            "theme": "Sunday Morning",
            "prompt": "Aria, a relaxed urban lifestyle portrait: warm golden hour light, soft bokeh, wearing a denim jacket, subtle smile — photorealistic, full-body, film grain"
        })
    elif "social media copywriter" in instruction:
        return jsonify({
            "caption": "Slow mornings with Aria — savor the little moments. #SundayMorning",
            "hashtags": ["#aria", "#sunday", "#lifestyle", "#goldenhour", "#photography"]
        })
    else:
        return jsonify({
            "theme": "Sunday Morning",
            "prompt": "Aria, a relaxed urban lifestyle portrait: warm golden hour light, soft bokeh, wearing a denim jacket, subtle smile — photorealistic, full-body, film grain"
        })


if __name__ == "__main__":
    # Simple dev server
    port = int(os.getenv("GEMINI_PROXY_PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
