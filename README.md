# System Design Demo Projects

Small, focused demos for system design interview preparation. Each demo covers one classic topic with working code, real infrastructure, and explicit trade-off discussion — built for deep understanding, not production completeness.

## Demos

### [rate-limiter-demo](./rate-limiter-demo/)
**Topic:** Rate Limiting

Five algorithms implemented in a single FastAPI service backed by Redis, switchable via a config file:

| Algorithm | Burst | Memory | Accuracy |
|---|---|---|---|
| Token Bucket | Yes — up to capacity | O(1) | Exact |
| Leaking Bucket | Absorbed, smoothed output | O(1) | Exact |
| Fixed Window | Boundary burst risk | O(1) | Approximate |
| Sliding Window Log | No | O(requests in window) | Exact |
| Sliding Window Counter | No | O(1) | Approximate |

Key concepts: atomic read-modify-write in Redis, Lua scripting vs optimistic locking, per-algorithm Redis data structures.

---

### [google-drive-demo](./google-drive-demo/)
**Topic:** File Storage with Chunking

A Google Drive-like file storage service demonstrating large file upload via S3 chunking with SQL metadata tracking.

Key concepts: chunked multipart upload, metadata vs blob separation, presigned URLs.

---

## Patterns Across All Demos

- **FastAPI + uv** — consistent tooling
- **Real infrastructure** — Redis, S3, SQL (no mocks)
- **`/debug` endpoints** — inspect internal state to observe the concept in action
- **Config-driven** — swap algorithms or parameters without code changes
- **Trade-offs documented** — every design decision is explained with its strengths and weaknesses
