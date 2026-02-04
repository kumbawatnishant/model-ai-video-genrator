import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# If modifying these scopes, delete the file youtube_token.json.
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_authenticated_service():
    creds = None
    # The file youtube_token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    token_file = os.getenv("YOUTUBE_TOKEN_FILE", "youtube_token.json")
    client_secrets_file = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secrets_file):
                raise FileNotFoundError(f"Client secrets file '{client_secrets_file}' not found. Please download it from Google Cloud Console.")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)

def upload_short(file_path, title, description=""):
    """
    Uploads a video to YouTube as a Short.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return None

    youtube = get_authenticated_service()

    # Add #Shorts to title if not present to help YouTube identify it
    if "#Shorts" not in title and "#Shorts" not in description:
        title = f"{title} #Shorts"

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["Shorts", "AI"],
            "categoryId": "22",  # Category 22 is 'People & Blogs'
        },
        "status": {
            "privacyStatus": os.getenv("YOUTUBE_PRIVACY_STATUS", "private"),
            "selfDeclaredMadeForKids": False,
        },
    }

    print(f"Uploading {file_path}...")
    
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")

    print(f"Upload Complete! Video ID: {response.get('id')}")
    return response

if __name__ == "__main__":
    # Run this script directly to perform the initial authentication
    print("Checking authentication...")
    try:
        get_authenticated_service()
        print("Authentication successful. 'youtube_token.json' has been saved.")

        # Allow testing upload from command line
        if len(sys.argv) > 1:
            video_path = sys.argv[1]
            print(f"\nTest mode: Uploading '{video_path}'...")
            upload_short(video_path, "Test AI Short", "Uploaded via Python script")
        else:
            print("\nTo test an upload immediately, run this script with a file path:")
            print("python youtube_uploader.py path/to/your/test_video.mp4")

    except Exception as e:
        print(f"Authentication failed: {e}")