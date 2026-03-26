import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

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
    total_chunks = Column(Integer, nullable=False)
    chunk_size = Column(Integer, nullable=False)      # bytes per chunk (except last)
    created_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("ChunkRecord", back_populates="file", order_by="ChunkRecord.chunk_index")


class ChunkRecord(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String, ForeignKey("files.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)     # 0-based order
    s3_key = Column(String, nullable=False)           # S3 object key
    chunk_size = Column(Integer, nullable=False)      # actual size of this chunk

    file = relationship("FileRecord", back_populates="chunks")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
