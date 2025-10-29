import os
from werkzeug.utils import secure_filename
from pathlib import Path

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload_file(file_storage):
    filename = secure_filename(file_storage.filename)
    # to avoid collisions, prefix timestamp
    from datetime import datetime
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    on_disk = f"{stamp}__{filename}"
    path = UPLOAD_DIR / on_disk
    file_storage.save(path)
    return str(path), filename
