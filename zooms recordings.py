import requests
import base64
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/upload-video", methods=["POST"])
def upload_video():
    data = request.get_json()

    video_url = data.get("video_url")
    base_name = data.get("base_name")
    FOLDER_ID = data.get("folder_id")
    GOOGLE_TOKEN = data.get("google_token")
    ZOOM_TOKEN = data.get("zoom_token")

    zoom_headers = {"Authorization": f"Bearer {ZOOM_TOKEN}"}
    google_headers = {"Authorization": f"Bearer {GOOGLE_TOKEN}"}

    # Descargar de Zoom en streaming
    zoom_resp = requests.get(video_url, headers=zoom_headers, stream=True)
    total_size = int(zoom_resp.headers.get("content-length", 0))

    # Iniciar sesion resumable en Drive
    init_resp = requests.post(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
        headers={**google_headers, "Content-Type": "application/json"},
        json={"name": f"{base_name}.mp4", "parents": [FOLDER_ID]}
    )
    upload_url = init_resp.headers.get("Location")

    # Subir en chunks
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