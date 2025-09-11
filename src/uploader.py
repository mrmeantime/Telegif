import requests
import os

def upload_to_catbox(filepath):
    """
    Upload file to catbox.moe and return the direct link
    """
    try:
        with open(filepath, "rb") as f:
            response = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f}
            )

        if response.status_code == 200:
            # Catbox returns just the URL as plain text
            catbox_url = response.text.strip()
            return catbox_url
        else:
            print(f"Catbox upload failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Catbox uploader error: {e}")
        return None
