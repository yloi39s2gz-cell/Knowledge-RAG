from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status


ALLOWED_SUFFIXES = {".pdf", ".txt", ".md", ".docx"}


@dataclass(frozen=True)
class SavedUpload:
    document_id: str
    original_filename: str
    stored_filename: str
    content_type: str
    size_bytes: int
    storage_path: str


async def save_upload_file(
    upload_file: UploadFile,
    upload_dir: str,
    max_upload_mb: int,
) -> SavedUpload:
    original_filename = Path(upload_file.filename or "").name
    suffix = Path(original_filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {suffix or 'unknown'}",
        )

    document_id = str(uuid4())
    target_dir = Path(upload_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{document_id}{suffix}"
    target_path = target_dir / stored_filename
    max_bytes = max_upload_mb * 1024 * 1024

    size_bytes = 0
    try:
        with target_path.open("wb") as out_file:
            while chunk := await upload_file.read(1024 * 1024):
                size_bytes += len(chunk)
                if size_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds {max_upload_mb} MB limit",
                    )
                out_file.write(chunk)
    except HTTPException:
        target_path.unlink(missing_ok=True)
        raise
    finally:
        await upload_file.close()

    if size_bytes == 0:
        target_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    return SavedUpload(
        document_id=document_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=upload_file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        storage_path=str(target_path),
    )
