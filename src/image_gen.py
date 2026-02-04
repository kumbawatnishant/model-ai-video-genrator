import os
import json
import requests
from typing import Optional

from .cref_store import CrefStore


class ImageGenerator:
    """Wrapper for multiple image generation providers with `cref` support.

    Behavior:
    - Use env `IMAGE_PROVIDER` to select provider (default: `leonardo`).
    - For `leonardo`, send a JSON request to `IMAGE_API_URL` with `prompt` and optional
      `cref` and expect a JSON response containing an `image_url` or `result_url`.
    - For `midjourney`, a direct integration usually requires a Discord bot; a
      simple HTTP proxy is recommended. This client exposes a placeholder path
      for `midjourney` which you can replace with your bot/proxy endpoint.

    The implementation below is intentionally generic so you can point `IMAGE_API_URL`
    to the vendor endpoint or a proxy that adapts SDK calls to the same contract.
    """

    def __init__(self, api_key: str = None, api_url: str = None, dry_run: bool = True, provider: Optional[str] = None):
        self.api_key = api_key or os.getenv("IMAGE_API_KEY")
        self.api_url = api_url or os.getenv("IMAGE_API_URL")
        self.dry_run = dry_run
        self.provider = (provider or os.getenv("IMAGE_PROVIDER") or "leonardo").lower()
        # character key used to persist/retrieve cref (default 'aria')
        self.character_key = os.getenv("CHARACTER_KEY") or "aria"
        self.cref_store = CrefStore()

    def generate_from_prompt(self, prompt: str, cref: Optional[str] = None, width: int = 1024, height: int = 1024) -> str:
        """Generate image and return an image URL (or local path).

        cref: optional character reference id to keep character consistent.
        """
        # if no explicit cref provided, try to load from store
        if not cref:
            stored = self.cref_store.get(self.character_key)
            if stored:
                cref = stored

        if self.dry_run:
            # Return a stable placeholder image URL — replace with real generated result
            return "https://images.unsplash.com/photo-1503264116251-35a269479413"

        if self.provider == "leonardo":
            return self._generate_leonardo(prompt, cref=cref, width=width, height=height)

        if self.provider == "midjourney":
            return self._generate_midjourney(prompt, cref=cref)

        if self.provider == "gork":
            return self._generate_gork(prompt, cref=cref, width=width, height=height)

        # Generic provider: POST to IMAGE_API_URL with prompt/cref
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"prompt": prompt, "width": width, "height": height}
        if cref:
            payload["cref"] = cref

        resp = requests.post(self.api_url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        # Persist cref if provider returned one (common keys)
        try:
            # top-level cref
            if isinstance(data, dict) and data.get("cref"):
                self.cref_store.set(self.character_key, data.get("cref"))
        except Exception:
            pass

        return data.get("image_url") or data.get("result_url") or data.get("url") or json.dumps(data)

    def _generate_leonardo(self, prompt: str, cref: Optional[str] = None, width: int = 1024, height: int = 1024) -> str:
        """Example Leonardo integration. Adjust the payload to match the provider's API.

        This function assumes `IMAGE_API_URL` is the Leonardo endpoint that accepts
        a JSON payload with `prompt`, `width`, `height`, and optional `cref`.
        """
        if not self.api_url:
            raise RuntimeError("IMAGE_API_URL must be set for Leonardo provider")

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "prompt": prompt,
            "width": width,
            "height": height,
        }
        if cref:
            payload["cref"] = cref

        resp = requests.post(self.api_url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        # Leonardo-like responses vary; try common fields
        # if the provider includes a reference id in the response, persist it
        try:
            # common: data[0].cref or data[0].reference_id or top-level 'cref'
            if isinstance(data, dict):
                if data.get("cref"):
                    self.cref_store.set(self.character_key, data.get("cref"))
                if data.get("data") and isinstance(data.get("data"), list):
                    first = data.get("data")[0]
                    if isinstance(first, dict):
                        for k in ("cref", "reference_id", "ref_id", "character_id"):
                            if first.get(k):
                                self.cref_store.set(self.character_key, first.get(k))
                                break
        except Exception:
            pass

        return data.get("image_url") or data.get("result_url") or (data.get("data") and data["data"][0].get("url")) or json.dumps(data)

    def _generate_midjourney(self, prompt: str, cref: Optional[str] = None) -> str:
        """Placeholder for Midjourney integration.

        Midjourney commonly runs via Discord bots. For a programmatic flow you
        can either run a Discord bot that receives prompts and returns generated
        image URLs, or use a hosted Midjourney API if available. This method
        assumes you have a proxy endpoint at `IMAGE_API_URL` that accepts the
        same JSON contract used above.
        """
        if not self.api_url:
            raise NotImplementedError(
                "Midjourney integration requires a proxy or Discord bot. Set IMAGE_API_URL to your proxy endpoint."
            )

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"prompt": prompt}
        if cref:
            payload["cref"] = cref

        resp = requests.post(self.api_url, json=payload, headers=headers, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        try:
            if isinstance(data, dict) and data.get("data") and isinstance(data.get("data"), list):
                first = data.get("data")[0]
                if isinstance(first, dict) and first.get("cref"):
                    self.cref_store.set(self.character_key, first.get("cref"))
        except Exception:
            pass

        return data.get("image_url") or data.get("result_url") or json.dumps(data)

    def _generate_gork(self, prompt: str, cref: Optional[str] = None, width: int = 1024, height: int = 1024) -> str:
        """Integration for the `gork` provider (proxy-compatible).

        This expects `IMAGE_API_URL` to accept the same JSON contract and to
        respond with `data: [{ 'url': ... }]` which is what our proxy returns.
        """
        if not self.api_url:
            raise RuntimeError("IMAGE_API_URL must be set for gork provider")

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"prompt": prompt, "width": width, "height": height}
        if cref:
            payload["cref"] = cref

        resp = requests.post(self.api_url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        # persist cref if present in response
        try:
            if isinstance(data, dict) and data.get("data") and isinstance(data.get("data"), list):
                first = data.get("data")[0]
                if isinstance(first, dict):
                    if first.get("cref"):
                        self.cref_store.set(self.character_key, first.get("cref"))
                    for k in ("cref", "reference_id", "ref_id", "character_id"):
                        if first.get(k):
                            self.cref_store.set(self.character_key, first.get(k))
                            break
        except Exception:
            pass

        # prefer data[0].url
        try:
            return data.get("data")[0].get("url")
        except Exception:
            return data.get("image_url") or data.get("result_url") or json.dumps(data)
