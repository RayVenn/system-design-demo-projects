from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from database import init_db
from routers import download, upload
from storage import ensure_bucket_exists


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    ensure_bucket_exists()
    yield


app = FastAPI(title="Google Drive Demo", version="0.1.0", lifespan=lifespan)

app.include_router(upload.router)
app.include_router(download.router)


@app.get("/health")
def health():
    return {"status": "ok"}


def start():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
