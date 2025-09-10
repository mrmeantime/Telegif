import os
import requests
from src.config import UPLOAD_SERVER, CAT_HOST

def upload_file(filepath):
    try:
        with open(filepath, "rb") as f:
            response = requests.post(
                UPLOAD_SERVER,
                files={"file": f}
            )

        if response.status_code == 200:
            # Build hosted URL
            filename = os.path.basename(filepath)
            return f"{CAT_HOST}/{filename}"
        else:
            print("Upload failed:", response.text)
            return None
    except Exception as e:
        print("Uploader error:", e)
        return None
