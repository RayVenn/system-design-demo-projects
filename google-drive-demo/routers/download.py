from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import FileRecord, get_db
from storage import download_chunk

router = APIRouter(prefix="/files", tags=["files"])


class DownloadResponse(BaseModel):
    file_id: str
    original_name: str
    output_path: str
    file_size: int
    total_chunks: int


@router.get("/{file_id}/download", response_model=DownloadResponse)
def download_file(file_id: str, output_path: str, db: Session = Depends(get_db)):
    file_record: FileRecord | None = db.get(FileRecord, file_id)
    if file_record is None:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")

    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Reassemble chunks in order
    try:
        with open(dest, "wb") as out:
            for chunk in file_record.chunks:
                data = download_chunk(chunk.s3_key)
                out.write(data)
    except Exception as e:
        # Remove partial output file on failure
        if dest.exists():
            dest.unlink()
        raise HTTPException(status_code=500, detail=f"Download failed: {e}") from e

    return DownloadResponse(
        file_id=file_id,
        original_name=file_record.original_name,
        output_path=str(dest.resolve()),
        file_size=file_record.file_size,
        total_chunks=file_record.total_chunks,
    )
