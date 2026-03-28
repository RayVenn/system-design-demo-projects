import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import FileRecord, get_db
from storage import generate_presigned_upload_url

router = APIRouter(prefix="/files", tags=["files"])


class UploadInitRequest(BaseModel):
    filename: str
    file_size: int  # bytes


class UploadInitResponse(BaseModel):
    file_id: str
    upload_url: str  # presigned S3 PUT URL — client uploads directly here


class UploadCompleteResponse(BaseModel):
    file_id: str
    status: str


@router.post("/upload/init", response_model=UploadInitResponse)
def upload_init(req: UploadInitRequest, db: Session = Depends(get_db)):
    file_id = str(uuid.uuid4())
    s3_key = f"files/{file_id}"

    upload_url = generate_presigned_upload_url(s3_key)

    file_record = FileRecord(
        id=file_id,
        original_name=req.filename,
        file_size=req.file_size,
        s3_key=s3_key,
        status="pending",
    )
    db.add(file_record)
    db.commit()

    return UploadInitResponse(file_id=file_id, upload_url=upload_url)


@router.post("/{file_id}/complete", response_model=UploadCompleteResponse)
def upload_complete(file_id: str, db: Session = Depends(get_db)):
    file_record: FileRecord | None = db.get(FileRecord, file_id)
    if file_record is None:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
    if file_record.status != "pending":
        raise HTTPException(status_code=400, detail=f"File is already {file_record.status}")

    file_record.status = "ready"
    db.commit()

    return UploadCompleteResponse(file_id=file_id, status="ready")
