# Google Drive Demo

## What This Is

A minimal Google Drive-like file storage service that demonstrates the core architecture behind large file storage: separating **blob data** (stored in S3) from **metadata** (stored in SQL), with chunking to handle files larger than memory. The goal is to understand why this split exists and what trade-offs it involves — not to replicate Google Drive feature-for-feature.

## Architecture

```
Client
  │
  ├── POST /upload  (multipart form)
  │     │
  │     ├── Split file into chunks (default 5 MB each)
  │     ├── Upload each chunk → S3  (key: files/<file_id>/chunk_<index>)
  │     └── Write metadata → SQLite
  │           ├── files table  (id, name, size, total_chunks, chunk_size)
  │           └── chunks table (file_id, chunk_index, s3_key, chunk_size)
  │
  └── GET /download/{file_id}
        │
        ├── Read chunk records from SQLite (ordered by chunk_index)
        ├── Fetch each chunk from S3 in order
        └── Stream reassembled bytes to client
```

## Why Separate Blob and Metadata?

This is the central design decision. The two storage systems have different strengths:

| | SQL (SQLite / Postgres) | Object Store (S3) |
|---|---|---|
| Good at | Querying, filtering, relationships | Storing large binary blobs cheaply |
| Bad at | Storing multi-GB binary files | Ad-hoc queries or joins |
| Scalability | Vertical (bigger DB) | Horizontal (infinite objects) |
| Cost | Expensive per GB | Cheap per GB |

Mixing them (e.g. storing blobs as SQL `BLOB` columns) breaks at scale: the database becomes enormous, backups slow down, and queries compete with large sequential reads. The split keeps the database lean and the blob store doing what it's good at.

## Why Chunking?

| Concern | Without chunking | With chunking |
|---|---|---|
| Memory | Entire file buffered in server RAM | One chunk at a time (5 MB default) |
| Resumability | Failed upload = restart from zero | Can resume from last successful chunk |
| Parallel upload | Not possible | Upload chunks concurrently |
| Partial reads | Must download whole file | Can fetch only needed chunks |

Even for small files the pattern is the same — chunking just becomes more impactful as file size grows.

## Data Model

### `files` table
```
id             UUID    primary key
original_name  TEXT    original filename
file_size      INT     total bytes
total_chunks   INT     number of chunks
chunk_size     INT     bytes per chunk (last chunk may be smaller)
created_at     DATETIME
```

### `chunks` table
```
id             UUID    primary key
file_id        UUID    foreign key → files.id
chunk_index    INT     0-based position (used to reassemble in order)
s3_key         TEXT    S3 object key: files/<file_id>/chunk_<index>
chunk_size     INT     actual byte size of this chunk
```

The `chunk_index` column is what guarantees correct reassembly — S3 has no ordering concept, so order must be stored explicitly in the metadata layer.

## Trade-offs in This Implementation

- **SQLite** is used for simplicity. In production, use Postgres — it handles concurrent writes and scales independently of the app server.
- **Synchronous S3 uploads** — chunks are uploaded sequentially. For large files, parallel uploads (using `asyncio.gather` or S3 multipart upload API) would be faster.
- **No deduplication** — the same file uploaded twice stores two full copies. Content-addressed storage (hashing chunks) would deduplicate automatically.
- **No presigned URLs** — download goes through the app server. In production, the server would return a presigned S3 URL and the client would download directly from S3, removing the server from the data path entirely.

## How to Run

Requires LocalStack (local S3 emulator) or real AWS credentials.

```bash
# start LocalStack (local S3)
docker run -d -p 4566:4566 localstack/localstack

# configure
cp .env.example .env
# set S3_ENDPOINT_URL=http://localhost:4566 in .env

# install and run
cd google-drive-demo
uv sync
uv run python main.py
```

## How to Observe

```bash
# upload a file
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/large_file.bin"

# response includes file_id, total_chunks, chunk_size

# download the file
curl http://localhost:8000/download/<file_id> -o output.bin

# inspect the SQLite metadata directly
sqlite3 gdrive_demo.db "SELECT * FROM files;"
sqlite3 gdrive_demo.db "SELECT * FROM chunks WHERE file_id='<file_id>';"
```

The SQLite queries show exactly what metadata is stored per chunk, and you can verify chunk objects exist in S3 via the LocalStack console or AWS CLI.
