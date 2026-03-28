import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # SQLite only
)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    original_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)       # bytes
    s3_key = Column(String, nullable=False)           # S3 object key
    status = Column(String, nullable=False, default="pending")  # pending | ready
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
