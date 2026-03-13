import requests
import json
import os
import base64
from flask import Flask, request, jsonify

app = Flask(__name__)

# Credenciales desde variables de entorno de Render
ZOOM_CLIENT_ID = os.environ.get("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.environ.get("ZOOM_CLIENT_SECRET")
ZOOM_ACCOUNT_ID = os.environ.get("ZOOM_ACCOUNT_ID")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN")
FOLDER_ID = os.environ.get("FOLDER_ID")

@app.route("/upload-video", methods=["POST"])
def upload_video():
    data = request.get_json()
    video_url = data.get("video_url")
    base_name = data.get("base_name")

    # 1. Zoom token
    creds = base64.b64encode(f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}".encode()).decode()
    zoom_token = requests.post(
        f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={ZOOM_ACCOUNT_ID}",
        headers={"Authorization": f"Basic {creds}"}
    ).json().get("access_token", "")
    zoom_headers = {"Authorization": f"Bearer {zoom_token}"}

    # 2. Google token
    google_token = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": GOOGLE_REFRESH_TOKEN,
            "grant_type": "refresh_token"
        }
    ).json().get("access_token", "")
    google_headers = {"Authorization": f"Bearer {google_token}"}

    # 3. Descargar de Zoom en streaming
    zoom_resp = requests.get(video_url, headers=zoom_headers, stream=True)
    total_size = int(zoom_resp.headers.get("content-length", 0))

    # 4. Iniciar sesion resumable en Drive
    init_resp = requests.post(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
        headers={**google_headers, "Content-Type": "application/json"},
        json={"name": f"{base_name}.mp4", "parents": [FOLDER_ID]}
    )
    upload_url = init_resp.headers.get("Location")

    # 5. Subir en chunks
    chunk_size = 10 * 1024 * 1024  # 10MB
    uploaded = 0
    for chunk in zoom_resp.iter_content(chunk_size=chunk_size):
        end = uploaded + len(chunk) - 1
        requests.put(
            upload_url,
            headers={
                "Content-Range": f"bytes {uploaded}-{end}/{total_size}",
                "Content-Length": str(len(chunk))
            },
            data=chunk
        )
        uploaded += len(chunk)

    return jsonify({"status": "ok", "uploaded": uploaded})

if __name__ == "__main__":
    app.run()