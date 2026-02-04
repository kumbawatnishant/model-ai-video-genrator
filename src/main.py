"""Orchestrator example: generate concept, image, video, caption, then post to Instagram.

Run as a module: `python -m src.main`
"""
import os
import time
from dotenv import load_dotenv

from .gemini_client import GeminiClient
from .video_gen import VideoGenerator
from .instagram_poster import InstagramPoster
from .youtube_poster import YouTubePoster
from .database import init_db, save_generated_content

try:
    from scripts.migrate_cref_json_to_sqlite import migrate
except Exception:
    migrate = None


def orchestrate(dry_run: bool = True) -> dict:
    print(f"orchestrate called with dry_run={dry_run}")

    # Init clients
    gemini = GeminiClient(dry_run=dry_run)
    video_gen = VideoGenerator(dry_run=dry_run)
    ig = InstagramPoster(dry_run=dry_run)
    # Add the YouTube Poster client
    yt = YouTubePoster(
        client_secrets_file=os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json"),
        credentials_file=os.getenv("YOUTUBE_TOKEN_FILE", "youtube_token.json"),
        dry_run=dry_run,
    )


    # 1. Generate concept and image prompt
    theme, prompt = gemini.generate_concept()
    print(f"Concept: {theme}\nPrompt: {prompt}\n")

    # 2. Generate image
    # If you have a character ref id for consistency, pass it via `cref`.
    image_url = gemini.generate_image(prompt, output_file="generated_image.png")
    print(f"Image URL:", image_url)

    # 3. Animate -> produce a short video. In dry-run request a local file so
    # we can exercise the resumable upload path end-to-end.
    # We force output_local=True because YouTube API requires a file upload.
    duration = int(os.getenv("VIDEO_DURATION", "5"))
    video_url = video_gen.animate_image_to_video(image_url, duration=duration, output_local=True)
    print("Video URL:", video_url)

    # 4. Draft caption and hashtags
    caption_text, hashtags = gemini.draft_caption_and_hashtags(theme, prompt)
    caption = caption_text + "\n\n" + " ".join(hashtags)

    # 5. Post to Instagram and YouTube
    ig_result = None
    yt_result = None
    try:
        if isinstance(video_url, str) and (video_url.startswith("file:") or __import__("os").path.exists(video_url)):
            # normalize file:// prefix
            if video_url.startswith("file://"):
                local_path = video_url[len("file://") :]
            else:
                local_path = video_url
            print(f"Detected local video file, uploading from: {local_path}")
            
            # Upload to YouTube first
            privacy = os.getenv("YOUTUBE_PRIVACY_STATUS", "private")
            yt_result = yt.upload_video(local_path, title=theme, description=caption, privacy_status=privacy)
            
            # Attempt Instagram upload (wrapped in try/except since API might be unavailable)
            try:
                ig_result = ig.upload_video_file(local_path, caption=caption)
                print("Instagram Post result:", ig_result)
            except Exception as ig_error:
                print(f"Instagram upload failed (skipping): {ig_error}")
        else:
            print("Error: Video generation did not return a local file path. Skipping uploads.")

        
        print("YouTube Post result:", yt_result)
    except Exception as e:
        print(f"Failed to post to social media: {e}")
    finally:
        if not dry_run:
            save_generated_content(theme, prompt, image_url, video_url, caption)
            print("Saved generated content to database.")

    return {"theme": theme, "image_url": image_url, "video_url": video_url, "caption": caption, "instagram_post_result": ig_result, "youtube_post_result": yt_result}


def run(dry_run: bool = True, auto_migrate: bool = False, fail_on_migrate_error: bool = False) -> dict:
    """Run optional one-time migration then orchestrator.

    If `auto_migrate` is True (or env var `AUTO_MIGRATE_ON_START` is set), the
    function will attempt to run the migration once. A marker file at
    `AUTO_MIGRATE_MARKER_PATH` (default `.cref_auto_migrated`) prevents repeated
    runs.
    """
    if not dry_run:
        init_db()
        print("Database initialized.")

    env_auto = os.getenv("AUTO_MIGRATE_ON_START", "false").lower() in ("1", "true", "yes")
    do_migrate = auto_migrate or env_auto

    marker = os.getenv("AUTO_MIGRATE_MARKER_PATH") or os.path.join(os.getcwd(), ".cref_auto_migrated")

    if do_migrate and migrate is not None:
        if os.path.exists(marker):
            print(f"Auto-migrate marker present ({marker}), skipping migration.")
        else:
            print("Auto-migrate: running one-time migration of cref store...")
            # Run migration with safe defaults: create JSON backup, verify, and rollback on fail
            try:
                rc = migrate(None, None, backup=True, dry_run=False, verify=True, rollback_on_fail=True)
                # migrate handles default src/dst via env vars
                if rc == -1:
                    print("Auto-migrate: migration failed or verification failed; see logs.")
                    if fail_on_migrate_error or os.getenv("AUTO_MIGRATE_FAIL_ON_ERROR", "false").lower() in ("1", "true", "yes"):
                        raise SystemExit("Auto-migrate failed and fail-on-error is enabled; aborting startup.")
                else:
                    # mark success
                    try:
                        with open(marker, "w") as f:
                            f.write(str(int(time.time())))
                        print(f"Auto-migrate: completed and marker written to {marker}")
                    except Exception as e:
                        print(f"Auto-migrate: completed but failed to write marker: {e}")
            except Exception as e:
                print(f"Auto-migrate: unexpected error during migration: {e}")
                if fail_on_migrate_error or os.getenv("AUTO_MIGRATE_FAIL_ON_ERROR", "false").lower() in ("1", "true", "yes"):
                    raise

    return orchestrate(dry_run=dry_run)


if __name__ == "__main__":
    import argparse

    # Get the absolute path to the .env file by going up one level from src
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    load_dotenv(dotenv_path=dotenv_path, override=True)
    print(f'DRY_RUN env var is: {os.getenv("DRY_RUN")}')
    is_dry_run = os.getenv("DRY_RUN", "true").lower() in ("1", "true", "yes")
    print(f"is_dry_run from env: {is_dry_run}")

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Run without making external API calls")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="Run with real API calls")
    parser.add_argument("--auto-migrate", dest="auto_migrate", action="store_true", help="Run one-time migration on start if not already run")
    parser.add_argument(
        "--fail-on-migrate-error", dest="fail_on_migrate_error", action="store_true", help="If auto-migrate fails, abort startup"
    )
    parser.set_defaults(dry_run=is_dry_run, auto_migrate=False, fail_on_migrate_error=False)
    args = parser.parse_args()
    print(f"args.dry_run: {args.dry_run}")

    run(dry_run=args.dry_run, auto_migrate=args.auto_migrate, fail_on_migrate_error=args.fail_on_migrate_error)
