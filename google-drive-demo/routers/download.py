from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import FileRecord, get_db
from storage import generate_presigned_download_url

router = APIRouter(prefix="/files", tags=["files"])


class DownloadResponse(BaseModel):
    file_id: str
    original_name: str
    file_size: int
    download_url: str  # presigned S3 GET URL — client fetches directly from S3


@router.get("/{file_id}/download", response_model=DownloadResponse)
def download_file(file_id: str, db: Session = Depends(get_db)):
    file_record: FileRecord | None = db.get(FileRecord, file_id)
    if file_record is None:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
    if file_record.status != "ready":
        raise HTTPException(status_code=409, detail=f"File is not ready yet (status: {file_record.status})")

    download_url = generate_presigned_download_url(file_record.s3_key)

    return DownloadResponse(
        file_id=file_id,
        original_name=file_record.original_name,
        file_size=file_record.file_size,
        download_url=download_url,
    )
