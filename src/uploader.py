import requests
import os
import logging

logger = logging.getLogger(__name__)

def upload_to_catbox(filepath):
    """
    Upload file to catbox.moe and return the direct link
    """
    try:
        logger.info(f"Uploading file to catbox: {filepath}")
        with open(filepath, "rb") as f:
            response = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f},
                timeout=30
            )

        if response.status_code == 200:
            # Catbox returns just the URL as plain text
            catbox_url = response.text.strip()
            logger.info(f"Successfully uploaded to catbox: {catbox_url}")
            return catbox_url
        else:
            logger.error(f"Catbox upload failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Catbox uploader error: {e}")
        return None
