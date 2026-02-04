import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class YouTubePoster:
    def __init__(self, client_secrets_file, credentials_file, dry_run=True):
        self.client_secrets_file = client_secrets_file
        self.credentials_file = credentials_file
        self.dry_run = dry_run
        self.scopes = ['https://www.googleapis.com/auth/youtube.upload']
        self.youtube = self.get_authenticated_service()

    def get_authenticated_service(self):
        if self.dry_run:
            print("[DRY RUN] Would authenticate with YouTube")
            return None

        credentials = None
        if os.path.exists(self.credentials_file):
            try:
                credentials = Credentials.from_authorized_user_file(self.credentials_file, self.scopes)
            except Exception as e:
                print(f"Warning: Failed to load existing credentials: {e}")

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_file,
                    scopes=self.scopes
                )
                credentials = flow.run_local_server(port=0)

            with open(self.credentials_file, 'w') as token:
                token.write(credentials.to_json())

        return build('youtube', 'v3', credentials=credentials)

    def upload_video(self, file_path, title, description, privacy_status='private'):
        if self.dry_run:
            print(f"[DRY RUN] Would upload video: {file_path}")
            print(f"  Title: {title}")
            print(f"  Description: {description}")
            return {"id": "dryrun_youtube_123", "status": "dry_run"}

        # Ensure #Shorts is in the title for better visibility
        if "#Shorts" not in title and "#Shorts" not in description:
            title = f"{title} #Shorts"

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': ['Shorts', 'AI', 'Generated'],
                'categoryId': '22'
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False,
            },
        }

        media = MediaFileUpload(file_path, chunksize=-1, resumable=True)

        request = self.youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%")

        print(f"Upload successful! Video ID: {response.get('id')}")
        return response
