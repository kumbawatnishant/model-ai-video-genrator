
import os
import time
import json
import base64
import logging
from typing import Tuple, List, Optional

import requests


logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini client wrapper.

    Behavior:
    - In `dry_run=True` mode the client returns deterministic placeholders.
    - In production mode (`dry_run=False`) the client issues an HTTP POST to
      `GEMINI_API_URL` with a Bearer token from `GEMINI_API_KEY` and expects a
      textual response containing JSON (or an API JSON response). Set `GEMINI_API_URL`
      to the vendor's Gemini Pro endpoint or proxy that you use.

    Notes:
    - This module intentionally keeps the HTTP contract generic so you can point
      it at the SDK-backed proxy or vendor URL you use for Gemini Pro.
    """

    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None, dry_run: bool = True, model: str = None, use_sdk: Optional[bool] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.api_url = api_url or os.getenv("GEMINI_API_URL")
        self.dry_run = dry_run
        self.model = model or os.getenv("GEMINI_MODEL") or "gemini-2.0-flash"
        
        # OpenRouter config
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.use_openrouter = os.getenv("USE_OPENROUTER", "false").lower() in ("1", "true", "yes")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL") or f"google/{self.model}"
        self.use_openrouter_for_images = os.getenv("USE_OPENROUTER_FOR_IMAGES", "false").lower() in ("1", "true", "yes")
        self.openrouter_image_model = os.getenv("OPENROUTER_IMAGE_MODEL") or "google/imagen-3"

        self.image_model = os.getenv("GEMINI_IMAGE_MODEL") or "gemini-2.0-flash"

        self.image_provider = os.getenv("IMAGE_PROVIDER", "gemini")
        self.stability_api_key = os.getenv("STABILITY_API_KEY")
        self.image_aspect_ratio = os.getenv("IMAGE_ASPECT_RATIO", "9:16")

        # allow enabling SDK usage via parameter or env var GEMINI_USE_SDK
        env_use_sdk = os.getenv("GEMINI_USE_SDK", "true").lower() in ("1", "true", "yes")
        self.use_sdk = use_sdk if use_sdk is not None else env_use_sdk
        self._genai = None

        if self.use_sdk and not self.dry_run:
            try:
                import google.generativeai as genai

                # configure SDK with provided api key
                try:
                    # some SDK versions use genai.configure
                    genai.configure(api_key=self.api_key)
                except Exception:
                    # fallback to attribute assignment if SDK differs
                    try:
                        genai.api_key = self.api_key
                    except Exception:
                        pass

                self._genai = genai
            except Exception as exc:  # ImportError or runtime errors
                raise RuntimeError(
                    "Requested SDK-backed Gemini use but `google-generativeai` import/config failed: %s. Try: pip install google-generativeai" % exc
                )

    def _download_fallback_image(self, output_file: str) -> str:
        url = "https://images.unsplash.com/photo-1620641788421-7a1c342ea42e?q=80&w=1974&auto=format&fit=crop"
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            with open(output_file, "wb") as f:
                f.write(resp.content)
            return os.path.abspath(output_file)
        except Exception as e:
            print(f"Warning: Failed to download fallback image: {e}")
            return url

    def _call_api(self, instruction: str, timeout: int = 60) -> str:
        """Generic POST caller to the configured Gemini API URL.

        Expects the endpoint to return either JSON or plain text. On success it
        returns the textual content for downstream parsing.
        """
        # 1. OpenRouter Path (High Priority)
        if self.use_openrouter:
            if not self.openrouter_api_key:
                raise RuntimeError("OPENROUTER_API_KEY is required when USE_OPENROUTER is true")
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/iqbalsdigra/model-ai-video",
                "X-Title": "Model AI Video Generator"
            }
            payload = {
                "model": self.openrouter_model,
                "messages": [{"role": "user", "content": instruction}]
            }
            last_exc = None
            for attempt in range(3):
                try:
                    resp = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=timeout)
                    if not resp.ok:
                        if resp.status_code >= 500 and attempt < 2:
                            time.sleep(2)
                            continue
                        try:
                            error_info = resp.json()
                        except Exception:
                            error_info = resp.text
                        raise RuntimeError(f"OpenRouter API returned {resp.status_code}: {error_info}")
                    return resp.json()["choices"][0]["message"]["content"]
                except Exception as e:
                    last_exc = e
                    if attempt < 2: time.sleep(2)
            raise RuntimeError(f"OpenRouter API call failed: {last_exc}")

        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY must be set for non-dry runs")

        if not self.use_sdk and not self.api_url:
            raise RuntimeError("GEMINI_API_URL must be set when not using the SDK")

        # If SDK usage was requested, prefer the SDK path
        if self.use_sdk and self._genai is not None:
            for attempt in range(3):
                try:
                    # Try a few common SDK call shapes; SDKs may evolve so we defensively try variations
                    # Modern google-generativeai SDK (v0.3+)
                    if hasattr(self._genai, "GenerativeModel"):
                        model_instance = self._genai.GenerativeModel(self.model)
                        resp = model_instance.generate_content(instruction)
                        return resp.text

                    # Preferred (newer) style: genai.chat.create or genai.chat.completions.create
                    if hasattr(self._genai, "chat") and hasattr(self._genai.chat, "create"):
                        resp = self._genai.chat.create(model=self.model, messages=[{"role": "user", "content": instruction}])
                        # multiple SDK shapes: try to fetch textual content
                        try:
                            return getattr(resp, "output_text") or str(resp)
                        except Exception:
                            try:
                                return resp.choices[0].message.content
                            except Exception:
                                return str(resp)
                    # Older style: genai.chat.completions.create
                    if hasattr(self._genai, "chat") and hasattr(self._genai.chat, "completions") and hasattr(self._genai.chat.completions, "create"):
                        resp = self._genai.chat.completions.create(model=self.model, messages=[{"role": "user", "content": instruction}])
                        try:
                            return resp.choices[0].message.content
                        except Exception:
                            return str(resp)

                    # If SDK doesn't expose chat, try a generic text_completion entrypoint
                    if hasattr(self._genai, "completions") and hasattr(self._genai.completions, "create"):
                        resp = self._genai.completions.create(model=self.model, prompt=instruction)
                        try:
                            return resp.choices[0].text
                        except Exception:
                            return str(resp)

                    # If unknown SDK shape, fall back to HTTP path (below)
                except Exception as exc:
                    # Check for ResourceExhausted (429)
                    is_quota = "429" in str(exc) or "ResourceExhausted" in str(type(exc).__name__)
                    if is_quota and attempt < 2:
                        sleep_time = 30 * (attempt + 1)
                        print(f"Gemini quota exceeded (429). Retrying in {sleep_time}s...")
                        time.sleep(sleep_time)
                        continue

                    # If we don't have a valid remote fallback URL, raise the SDK error directly
                    if not self.api_url or "localhost" in self.api_url:
                        # Help debug 404s by listing available models
                        if "404" in str(exc):
                            print(f"\nDEBUG: Model '{self.model}' not found. Listing available models for your key:")
                            try:
                                for m in self._genai.list_models():
                                    if "generateContent" in m.supported_generation_methods:
                                        print(f" - {m.name}")
                            except Exception:
                                pass
                        raise exc
                    logger.exception("SDK call to Gemini failed, falling back to HTTP: %s", exc)
                    break

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "instruction": instruction}

        # Basic retry logic for HTTP path
        last_exc = None
        for attempt in range(3):
            try:
                resp = requests.post(self.api_url, json=payload, headers=headers, timeout=timeout)
                resp.raise_for_status()
                # Prefer JSON if available
                try:
                    return json.dumps(resp.json())
                except Exception:
                    return resp.text
            except Exception as exc:  # requests.exceptions.RequestException covers network issues
                last_exc = exc
                backoff = 2 ** attempt
                logger.warning("Gemini API call failed (attempt %s): %s — retrying in %s s", attempt + 1, exc, backoff)
                time.sleep(backoff)

        raise RuntimeError("Gemini API call failed after retries") from last_exc

    def generate_concept(self) -> Tuple[str, str]:
        """Return (theme, image_prompt).

        The instruction asks the model to return a small JSON object with keys
        `theme` and `prompt`. The function attempts to parse the model output as
        JSON and falls back to simple heuristics.
        """
        if self.dry_run:
            theme = "Sunday Morning"
            prompt = (
                "Aria, a relaxed urban lifestyle portrait: warm golden hour light, soft bokeh, "
                "wearing a denim jacket, subtle smile — photorealistic, full-body, film grain"
            )
            return theme, prompt

        style = os.getenv("CONTENT_STYLE", "cinematic")
        instruction = (
            "You are a creative director for short-form social content.\n"
            "Produce a concise JSON object with two fields: `theme` (short title) and `prompt` (an image-generation prompt).\n"
            f"The visual style must be: {style}.\n"
            "Keep values short. Example output: {\"theme\": \"Sunday Morning\", \"prompt\": \"Aria, ...\"}\n"
        )

        raw = self._call_api(instruction)

        # Try to parse JSON directly
        try:
            data = json.loads(raw)
            theme = data.get("theme")
            prompt = data.get("prompt")
            if theme and prompt:
                return theme, prompt
        except Exception:
            pass

        # Fallback: scan for JSON in the text
        try:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                snippet = raw[start : end + 1]
                data = json.loads(snippet)
                return data.get("theme"), data.get("prompt")
        except Exception:
            logger.exception("Failed to parse JSON snippet from Gemini response")

        # Last resort: return the raw text as 'prompt' and a generic theme
        return "Untitled", raw[:1000]

    def draft_caption_and_hashtags(self, theme: str, image_prompt: str) -> Tuple[str, List[str]]:
        if self.dry_run:
            caption = f"Slow mornings with Aria — savor the little moments. #SundayMorning"
            hashtags = ["#aria", "#sunday", "#lifestyle", "#goldenhour", "#photography"]
            return caption, hashtags

        instruction = (
            f"You are a social media copywriter. Given the theme `{theme}` and the image prompt below, write a short engaging Instagram caption (2-3 sentences) and a list of 10-15 relevant hashtags as JSON with keys `caption` and `hashtags`.\n\nPrompt:\n{image_prompt}"
        )

        raw = self._call_api(instruction)

        try:
            data = json.loads(raw)
            caption = data.get("caption")
            hashtags = data.get("hashtags") or []
            return caption, hashtags
        except Exception:
            # Try to find JSON substring
            try:
                start = raw.find("{")
                end = raw.rfind("}")
                if start != -1 and end != -1 and end > start:
                    snippet = raw[start : end + 1]
                    data = json.loads(snippet)
                    return data.get("caption"), data.get("hashtags") or []
            except Exception:
                logger.exception("Failed to parse caption/hashtags from Gemini response")

        # Last resort: return raw text as caption and empty hashtags
        return raw.strip(), []

    def generate_image(self, prompt: str, output_file: str = "generated_image.png") -> str:
        """Generate an image using Gemini (Imagen 3) and save it locally."""
        if self.dry_run:
            return "https://images.unsplash.com/photo-1503264116251-35a269479413"

        if self.use_openrouter_for_images:
            print("Generating image with OpenRouter...")
            if not self.openrouter_api_key:
                raise RuntimeError("OPENROUTER_API_KEY is required when USE_OPENROUTER_FOR_IMAGES is true")
            
            headers = {"Authorization": f"Bearer {self.openrouter_api_key}"}
            payload = {"model": self.openrouter_image_model, "prompt": prompt, "n": 1}
            try:
                resp = requests.post("https://openrouter.ai/api/v1/images/generations", json=payload, headers=headers, timeout=120)
                resp.raise_for_status()
                data = resp.json()
                b64_data = data['data'][0]['b64_json']
                with open(output_file, "wb") as f:
                    f.write(base64.b64decode(b64_data))
                return os.path.abspath(output_file)
            except Exception as e:
                logger.exception("OpenRouter image generation failed")
                print(f"Warning: OpenRouter image generation failed ({e}). Falling back to Gemini...")
                # Do not return; let execution continue to the Gemini block below

        if self.image_provider == "stability":
            print("Generating image with Stability AI (Ultra)...")
            if not self.stability_api_key:
                raise RuntimeError("STABILITY_API_KEY is required for Stability AI.")
            
            # Use Stability AI Ultra endpoint
            url = "https://api.stability.ai/v2beta/stable-image/generate/ultra"
            headers = {
                "Authorization": f"Bearer {self.stability_api_key}",
                "Accept": "image/*"
            }
            # Stability API requires multipart/form-data
            payload = {"prompt": prompt, "output_format": "png", "aspect_ratio": self.image_aspect_ratio}
            try:
                # files={"none": ''} forces requests to send multipart/form-data even without a file
                resp = requests.post(url, headers=headers, files={"none": ''}, data=payload, timeout=60)
                if resp.status_code == 200:
                    with open(output_file, "wb") as f:
                        f.write(resp.content)
                    return os.path.abspath(output_file)
                else:
                    raise RuntimeError(f"Stability AI Error: {resp.text}")
            except Exception as e:
                logger.exception("Stability AI image generation failed")
                print(f"Warning: Stability AI image generation failed ({e}). Falling back to Gemini...")
                # Fall through to Gemini

        print("Generating image with Gemini...")
        # Determine endpoint and payload based on model name
        # Imagen models use the :predict endpoint
        # Gemini models (2.0+) use the :generateContent endpoint
        is_imagen = "imagen" in self.image_model.lower()

        if is_imagen:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.image_model}:predict"
            payload = {
                "instances": [{"prompt": prompt}],
                "parameters": {"sampleCount": 1}
            }
        else:
            # Assume Gemini 2.0 Flash or similar
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.image_model}:generateContent"
            payload = {
                "contents": [{
                    "parts": [{"text": f"Generate an image of {prompt}"}]
                }],
                "generationConfig": {
                    "responseMimeType": "image/jpeg",
                    "aspectRatio": self.image_aspect_ratio
                }
            }

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }

        last_exc = None
        for attempt in range(5):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=60)
                resp.raise_for_status()
                data = resp.json()

                b64_data = None
                if is_imagen:
                    if "predictions" in data and len(data["predictions"]) > 0:
                        b64_data = data["predictions"][0].get("bytesBase64Encoded")
                else:
                    try:
                        parts = data.get("candidates", [])[0].get("content", {}).get("parts", [])
                        for part in parts:
                            if "inlineData" in part:
                                b64_data = part["inlineData"]["data"]
                                break
                    except (IndexError, AttributeError):
                        pass

                if b64_data:
                    with open(output_file, "wb") as f:
                        f.write(base64.b64decode(b64_data))
                    return os.path.abspath(output_file)

                raise RuntimeError(f"No image data in response: {data}")

            except requests.exceptions.HTTPError as e:
                last_exc = e
                if e.response.status_code == 429 and attempt < 4:
                    sleep_time = 30 * (attempt + 1)
                    print(f"Gemini image generation quota exceeded (429). Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                    continue
                break  # Stop retrying on other errors or max attempts
            except Exception as e:
                last_exc = e
                break

        print(f"Warning: Gemini image generation failed ({last_exc}). Using fallback image.")
        return self._download_fallback_image(output_file)
