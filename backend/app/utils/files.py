import shutil
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile


def sanitize_ext(filename: str) -> str:
    return Path(filename).suffix.lower().strip()


def save_upload_file(upload_file: UploadFile, target_dir: Path) -> Tuple[str, str]:
    target_dir.mkdir(parents=True, exist_ok=True)
    ext = sanitize_ext(upload_file.filename or "")
    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path = target_dir / stored_name
    with file_path.open("wb") as out_file:
        shutil.copyfileobj(upload_file.file, out_file)
    return str(file_path), ext

