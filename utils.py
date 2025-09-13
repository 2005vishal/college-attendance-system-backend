import os
import uuid
from typing import Optional
from fastapi import UploadFile


UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg"}


def save_upload(file: Optional[UploadFile]) -> Optional[str]:
    if file is None:
        return None
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError("Unsupported image type")
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    fname = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, fname)
    with open(path, "wb") as f:
        f.write(file.file.read())
    # return relative path so frontend can store it
    return f"uploads/{fname}"