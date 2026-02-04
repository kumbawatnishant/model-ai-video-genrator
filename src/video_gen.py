import os
import time
import requests
import subprocess
import logging
import shutil
import tempfile

logger = logging.getLogger(__name__)

class VideoGenerator:
    """Video generator client.

    Behavior:
    - If `USE_OPENROUTER_FOR_VIDEOS` is true, it will attempt to generate a video
      using an image-to-video model via OpenRouter.
    - Otherwise, it falls back to using `ffmpeg` to create a simple Ken Burns
      effect video from the input image.
    - In `dry_run=True` mode, it returns a placeholder path.
    """

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.use_openrouter = os.getenv("USE_OPENROUTER_FOR_VIDEOS", "false").lower() in ("1", "true", "yes")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_video_model = os.getenv("OPENROUTER_VIDEO_MODEL", "stabilityai/stable-video-diffusion")
        self.video_provider = os.getenv("VIDEO_PROVIDER", "ffmpeg")
        self.stability_api_key = os.getenv("STABILITY_API_KEY")

    def _ensure_background_music(self) -> str:
        """Ensures a background music file exists. Returns path or None."""
        audio_path = "background_music.mp3"
        if os.path.exists(audio_path):
            return audio_path
        
        print("Downloading default background music...")
        # Using a sample royalty-free track for testing
        url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
        try:
            resp = requests.get(url, stream=True, timeout=60)
            if resp.status_code == 200:
                with open(audio_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        f.write(chunk)
                return audio_path
        except Exception as e:
            logger.warning(f"Failed to download background music: {e}")
        return None

    def _resize_image_for_video(self, input_path: str) -> str:
        """Resizes image to 576x1024 (supported by SVD) using ffmpeg."""
        resized_path = "resized_image_for_video.png"
        try:
            # Scale to 576x1024 (9:16 aspect ratio required by SVD)
            subprocess.run([
                "ffmpeg", "-y", "-i", input_path,
                "-vf", "scale=576:1024",
                resized_path
            ], check=True, capture_output=True)
            return resized_path
        except Exception as e:
            logger.warning(f"Failed to resize image: {e}")
            return input_path

    def animate_image_to_video(self, image_path: str, duration: int = 5, output_local: bool = True) -> str:
        if self.dry_run:
            print("[DRY RUN] Would generate video from image:", image_path)
            # Try to create a tiny valid MP4 using ffmpeg so downstream upload
            # code paths that check for a real video file can be exercised.
            out_path = "/tmp/dry_run_video.mp4"
            if os.path.exists(out_path):
                return out_path

            ffmpeg_path = shutil.which("ffmpeg")
            temp_image = None
            try:
                # Prepare input image: if it's a remote URL, download it to a temp file.
                input_image = image_path
                if isinstance(image_path, str) and image_path.startswith(("http://", "https://")):
                    tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image_path)[1] or '.jpg')
                    temp_image = tmpf.name
                    with tmpf:
                        resp = requests.get(image_path, stream=True, timeout=30)
                        resp.raise_for_status()
                        for chunk in resp.iter_content(chunk_size=1024 * 1024):
                            tmpf.write(chunk)
                    input_image = temp_image

                if ffmpeg_path:
                    # Create a short video from the image using ffmpeg with a
                    # small Ken Burns effect (zoom + fade). Use the requested
                    # duration where possible to exercise the same code paths.
                    dry_duration = max(2, min(int(duration), 10)) if isinstance(duration, int) else 2
                    fade_dur = min(0.5, dry_duration / 4.0)
                    # gentle zoom parameters
                    zoom_inc = 0.003
                    max_zoom = 1.15
                    vf_filter = (
                        f"zoompan=z=min(zoom+{zoom_inc},{max_zoom}):d=1:x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2),"
                        f"fps=25,scale=1080:1920,setsar=1,fade=t=in:st=0:d={fade_dur},fade=t=out:st={dry_duration-fade_dur}:d={fade_dur}"
                    )

                    cmd = [
                        ffmpeg_path,
                        "-y",
                        "-loop", "1",
                        "-i", input_image,
                        "-vf", vf_filter,
                        "-c:v", "libx264",
                        "-t", str(dry_duration),
                        "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart",
                        out_path,
                    ]
                    try:
                        subprocess.run(cmd, check=True, capture_output=True)
                        return out_path
                    except subprocess.CalledProcessError as e:
                        stderr = getattr(e, 'stderr', None)
                        logger.warning(f"ffmpeg dry-run video creation failed: {stderr if stderr else e}")
                # If ffmpeg not available or failed, fall back to a minimal placeholder file
                with open(out_path, "wb") as f:
                    f.write(b"DRY_RUN_PLACEHOLDER_MP4\n")
                return out_path
            except Exception as e:
                logger.warning(f"Failed to create dry-run video: {e}")
                try:
                    with open(out_path, "wb") as f:
                        f.write(b"DRY_RUN_PLACEHOLDER\n")
                except Exception:
                    pass
                return out_path
            finally:
                if temp_image:
                    try:
                        os.unlink(temp_image)
                    except Exception:
                        pass

        if not output_local:
            raise ValueError("VideoGenerator currently only supports local output.")

        output_path = "generated_video.mp4"

        if self.video_provider == "stability":
            print("Generating video with Stability AI...")
            if not self.stability_api_key:
                raise RuntimeError("STABILITY_API_KEY is required for Stability AI video generation.")
            
            # Resize image to 576x1024 to match SVD requirements
            processed_image_path = self._resize_image_for_video(image_path)

            try:
                # 1. Submit generation request
                with open(processed_image_path, "rb") as f:
                    resp = requests.post(
                        "https://api.stability.ai/v2beta/image-to-video",
                        headers={"Authorization": f"Bearer {self.stability_api_key}"},
                        files={"image": ("image.png", f, "image/png")},
                        data={"seed": 0, "cfg_scale": 1.8, "motion_bucket_id": 127},
                        timeout=60
                    )
                    if resp.status_code != 200:
                        raise RuntimeError(f"Stability AI submit failed: {resp.text}")
                    generation_id = resp.json().get("id")
                    print(f"Stability AI generation started. ID: {generation_id}")

                # 2. Poll for result
                for _ in range(60): # Wait up to 60 * 2 = 120 seconds
                    time.sleep(2)
                    resp = requests.get(
                        f"https://api.stability.ai/v2beta/image-to-video/result/{generation_id}",
                        headers={"Authorization": f"Bearer {self.stability_api_key}", "Accept": "video/*"},
                        timeout=30
                    )
                    if resp.status_code == 202:
                        print(".", end="", flush=True)
                        continue # Still processing
                    elif resp.status_code == 200:
                        print("\nVideo generation complete!")
                        with open(output_path, "wb") as f:
                            f.write(resp.content)
                        return output_path
                    else:
                        raise RuntimeError(f"Stability AI polling failed: {resp.text}")
            except Exception as e:
                logger.error(f"Stability AI video generation failed: {e}. Falling back to ffmpeg.")

        if self.use_openrouter:
            print("Generating video with OpenRouter...")
            if not self.openrouter_api_key:
                raise RuntimeError("OPENROUTER_API_KEY is required for video generation via OpenRouter.")
            
            # Resize image to 576x1024 to match SVD requirements
            processed_image_path = self._resize_image_for_video(image_path)

            try:
                # NOTE: This uses the Stability AI API structure, proxied via OpenRouter.
                # The exact endpoint on OpenRouter for this might vary.
                with open(processed_image_path, "rb") as f:
                    files = {"image": f}
                    headers = {"Authorization": f"Bearer {self.openrouter_api_key}"}
                    # This endpoint is a structured guess. OpenRouter may require a different path.
                    response = requests.post(
                        "https://openrouter.ai/api/v1/stability-ai/image-to-video",
                        headers=headers,
                        files=files,
                        data={"seed": 0, "cfg_scale": 2.5, "motion_bucket_id": 40},
                        timeout=300
                    )
                    response.raise_for_status()

                with open(output_path, "wb") as f:
                    f.write(response.content)
                print(f"Successfully generated video with OpenRouter: {output_path}")
                return output_path
            except Exception as e:
                logger.error(f"OpenRouter video generation failed: {e}. Falling back to ffmpeg.")
        
        # Fallback to ffmpeg
        print("Using ffmpeg for local video generation...")
        audio_path = self._ensure_background_music()

        try:
            # Simple Ken Burns effect: zoom in and pan slightly
            zoom_rate = 1.2
            vf_filter = (
                f"zoompan=z='min(zoom+{zoom_rate/duration/25},1.5)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',"
                f"scale=1080:1920,setsar=1"
            )
            command = [
                "ffmpeg",
                "-y",
                "-loop", "1", "-i", image_path,  # Input 0: Image
            ]

            if audio_path:
                command.extend(["-stream_loop", "-1", "-i", audio_path]) # Input 1: Audio (looped)
            
            command.extend([
                "-vf", vf_filter,
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryslow", "-crf", "28",
                "-t", str(duration)
            ])

            if audio_path:
                # Map video from stream 0, audio from stream 1, encode audio to aac
                command.extend(["-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "128k", "-shortest"])
            
            command.append(output_path)

            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"Successfully generated video with ffmpeg: {output_path}")
            return output_path
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"ffmpeg video generation failed: {e}")
            if isinstance(e, subprocess.CalledProcessError):
                logger.error(f"ffmpeg stderr: {e.stderr}")
            print("Warning: ffmpeg failed. Returning image path as fallback.")
            return image_path # Fallback to image if video fails