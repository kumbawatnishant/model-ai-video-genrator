import os
import math
import requests
from typing import Optional


class InstagramPoster:
    """Poster for Instagram using the Facebook Graph API.

    This class provides two flows:
    - post_video(video_url=...): post a public video URL (existing behavior)
    - upload_video_file(file_path=...): resumable/chunked upload of a local file

    The resumable upload follows the Graph API `upload_phase` protocol (start,
    transfer, finish) and then creates a media object and publishes it. The
    exact parameter names used are compatible with the Facebook/Graph resumable
    upload pattern; the tests mock the network calls.
    """

    def __init__(self, ig_user_id: str = None, access_token: str = None, dry_run: bool = True, api_version: str = "v16.0"):
        self.ig_user_id = ig_user_id or os.getenv("INSTAGRAM_ACCOUNT_ID") or os.getenv("IG_USER_ID")
        self.access_token = access_token or os.getenv("IG_ACCESS_TOKEN")
        self.dry_run = dry_run
        self.graph_url = f"https://graph.facebook.com/{api_version}"

    def post_video(self, video_url: str, caption: str, share_to_feed: bool = True) -> dict:
        """Post a video by URL. Returns the publish result dict.

        In dry_run mode the call is not made and a simulated response is returned.
        """
        if self.dry_run:
            print("[DRY RUN] Would post to Instagram:")
            print(" video_url:", video_url)
            print(" caption:", caption)
            return {"id": "dryrun_12345", "status": "dry_run"}

        # 1) Create media object
        media_endpoint = f"{self.graph_url}/{self.ig_user_id}/media"
        params = {
            "media_type": "VIDEO",
            "video_url": video_url,
            "caption": caption,
            "access_token": self.access_token,
        }
        resp = requests.post(media_endpoint, data=params, timeout=60)
        resp.raise_for_status()
        media = resp.json()

        creation_id = media.get("id")
        if not creation_id:
            raise RuntimeError("Failed to create media object: %s" % media)

        # 2) Publish
        publish_endpoint = f"{self.graph_url}/{self.ig_user_id}/media_publish"
        publish_resp = requests.post(publish_endpoint, data={"creation_id": creation_id, "access_token": self.access_token}, timeout=60)
        publish_resp.raise_for_status()
        return publish_resp.json()

    def upload_video_file(self, file_path: str, caption: str, chunk_size: int = 4 * 1024 * 1024) -> dict:
        """Upload a local video file using the Graph API resumable upload flow.

        Steps:
        1. POST upload_phase=start with file_size -> receive upload_session_id, video_id, offsets
        2. POST upload_phase=transfer with each chunk until finished
        3. POST upload_phase=finish to complete upload
        4. Create media object and publish

        Returns the publish response dict.
        """
        if self.dry_run:
            print(f"[DRY RUN] Would upload file: {file_path} (chunk_size={chunk_size}) and publish with caption: {caption}")
            return {"id": "dryrun_upload_123", "status": "dry_run"}

        file_size = os.path.getsize(file_path)

        # 1) Start
        start_endpoint = f"{self.graph_url}/{self.ig_user_id}/videos"
        start_params = {"upload_phase": "start", "file_size": str(file_size), "access_token": self.access_token}
        start_resp = requests.post(start_endpoint, data=start_params, timeout=60)
        start_resp.raise_for_status()
        start_json = start_resp.json()

        upload_session_id = start_json.get("upload_session_id")
        video_id = start_json.get("video_id") or start_json.get("id") or start_json.get("fb_id")
        start_offset = int(start_json.get("start_offset", 0))
        end_offset = int(start_json.get("end_offset", 0))

        if not upload_session_id:
            raise RuntimeError(f"Failed to start upload: {start_json}")

        # 2) Transfer chunks
        with open(file_path, "rb") as f:
            while start_offset < file_size:
                # compute bytes to read
                f.seek(start_offset)
                to_read = min(chunk_size, file_size - start_offset)
                chunk = f.read(to_read)

                files = {"video_file_chunk": (os.path.basename(file_path), chunk)}
                transfer_params = {
                    "upload_phase": "transfer",
                    "start_offset": str(start_offset),
                    "upload_session_id": upload_session_id,
                    "access_token": self.access_token,
                }
                transfer_resp = requests.post(start_endpoint, data=transfer_params, files=files, timeout=120)
                transfer_resp.raise_for_status()
                tjson = transfer_resp.json()
                # update offsets
                start_offset = int(tjson.get("start_offset", start_offset + to_read))
                end_offset = int(tjson.get("end_offset", end_offset))

        # 3) Finish
        finish_params = {"upload_phase": "finish", "upload_session_id": upload_session_id, "access_token": self.access_token}
        finish_resp = requests.post(start_endpoint, data=finish_params, timeout=60)
        finish_resp.raise_for_status()
        finish_json = finish_resp.json()

        # some flows return video_id earlier; try to resolve it
        published_video_id = video_id or finish_json.get("video_id") or finish_json.get("id")

        # 4) Create media object via the /media endpoint using the uploaded video id
        if not published_video_id:
            # sometimes the API returns the video id under different keys
            raise RuntimeError(f"Unable to determine uploaded video id: {finish_json}")

        media_endpoint = f"{self.graph_url}/{self.ig_user_id}/media"
        media_params = {
            "media_type": "VIDEO",
            "video_id": published_video_id,
            "caption": caption,
            "access_token": self.access_token,
        }
        media_resp = requests.post(media_endpoint, data=media_params, timeout=60)
        media_resp.raise_for_status()
        media_json = media_resp.json()
        creation_id = media_json.get("id")
        if not creation_id:
            raise RuntimeError(f"Failed to create media object: {media_json}")

        # Publish
        publish_endpoint = f"{self.graph_url}/{self.ig_user_id}/media_publish"
        publish_resp = requests.post(publish_endpoint, data={"creation_id": creation_id, "access_token": self.access_token}, timeout=60)
        publish_resp.raise_for_status()
        return publish_resp.json()
