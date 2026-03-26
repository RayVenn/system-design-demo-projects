import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import ChunkRecord, FileRecord, get_db
from storage import upload_chunk

router = APIRouter(prefix="/files", tags=["files"])


class UploadRequest(BaseModel):
    local_path: str


class UploadResponse(BaseModel):
    file_id: str
    original_name: str
    file_size: int
    total_chunks: int
    chunk_size: int


@router.post("/upload", response_model=UploadResponse)
def upload_file(req: UploadRequest, db: Session = Depends(get_db)):
    path = Path(req.local_path)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"File not found: {req.local_path}")
    if not path.is_file():
        raise HTTPException(status_code=400, detail=f"Path is not a file: {req.local_path}")

    file_size = path.stat().st_size
    chunk_size = settings.chunk_size_bytes
    file_id = str(uuid.uuid4())
    original_name = path.name

    chunk_records: list[ChunkRecord] = []
    s3_keys_uploaded: list[str] = []

    try:
        with open(path, "rb") as f:
            chunk_index = 0
            while True:
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                s3_key = f"files/{file_id}/chunk_{chunk_index:06d}"
                upload_chunk(s3_key, chunk_data)
                s3_keys_uploaded.append(s3_key)
                chunk_records.append(
                    ChunkRecord(
                        file_id=file_id,
                        chunk_index=chunk_index,
                        s3_key=s3_key,
                        chunk_size=len(chunk_data),
                    )
                )
                chunk_index += 1
    except Exception as e:
        # Clean up any uploaded chunks on failure
        from storage import delete_chunks
        delete_chunks(s3_keys_uploaded)
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}") from e

    total_chunks = len(chunk_records)
    file_record = FileRecord(
        id=file_id,
        original_name=original_name,
        file_size=file_size,
        total_chunks=total_chunks,
        chunk_size=chunk_size,
    )
    db.add(file_record)
    db.add_all(chunk_records)
    db.commit()

    return UploadResponse(
        file_id=file_id,
        original_name=original_name,
        file_size=file_size,
        total_chunks=total_chunks,
        chunk_size=chunk_size,
    )
