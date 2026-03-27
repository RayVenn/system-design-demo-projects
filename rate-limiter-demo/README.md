# Rate Limiter Demo

## What This Is

A single FastAPI service that implements five classic rate-limiting algorithms, all backed by Redis and switchable via a YAML config file. The goal is to understand what each algorithm actually stores, why, and what trade-offs it makes — not to build a production rate limiter.

## Architecture

```
Client
  │
  ▼
FastAPI Middleware (RateLimitMiddleware)
  │  reads app.state.limiter (set at startup from config)
  ▼
RateLimiter.is_allowed("global")
  │  atomic read-modify-write
  ▼
Redis
  │
  └── X-RateLimit-* headers added to response
      429 returned if over limit
```

All five algorithms share the same interface (`is_allowed(identifier) → LimitResult`) and the same Redis connection. Swapping algorithms is a one-line config change.

## Algorithms and Trade-offs

| Algorithm | Burst allowed? | Memory per key | Accuracy | Best for |
|---|---|---|---|---|
| Token Bucket | Yes — up to capacity | O(1) — 1 hash (2 fields) | Exact | APIs that want to allow short bursts |
| Leaking Bucket | Absorbed, but output is smooth | O(1) — 1 hash (2 fields) | Exact | Smoothing traffic to a slow downstream |
| Fixed Window | Boundary burst (2× rate) | O(1) — 1 int | Approximate | Simplest implementation, coarse limits |
| Sliding Window Log | No | O(N) — 1 sorted set, N = requests in window | Exact | Strict limits where accuracy matters |
| Sliding Window Counter | No | O(1) — 2 ints | Approximate (assumes uniform prev window) | Accuracy close to log at a fraction of memory |

## What Each Algorithm Stores in Redis

### Token Bucket — `rl:global:tb` (Hash)
```
tokens       9.4          float — current token count
last_refill  1743050412   float — unix timestamp of last refill calculation
```
Refill is computed lazily: `new_tokens = min(capacity, tokens + elapsed * refill_rate)`.

### Leaking Bucket — `rl:global:lb` (Hash)
```
queue_size   3.2          float — virtual queue occupancy
last_leak    1743050412   float — unix timestamp of last drain calculation
```
Drain is computed lazily: `queue = max(0, queue - elapsed * leak_rate)`.

### Fixed Window — `rl:global:fw:<window_id>` (String)
```
rl:global:fw:29050840  →  "7"    TTL: 2 × window_size
```
`window_id = floor(now / window_size)`. Old windows expire via Redis TTL — nothing to clean up.

### Sliding Window Log — `rl:global:swl` (Sorted Set)
```
member                          score (timestamp)
"1743050412.3-a3f9..."          1743050412.3
"1743050398.1-b7c2..."          1743050398.1
```
On each request: remove scores older than `now - window_size`, count remaining, add new entry if allowed. Member includes a UUID so simultaneous requests don't collide.

### Sliding Window Counter — `rl:global:swc:<window_id>` (String × 2)
```
rl:global:swc:29050840  →  "5"    current window   TTL: 2 × window_size
rl:global:swc:29050839  →  "8"    previous window  TTL: 2 × window_size
```
Estimate: `prev_count × (1 - elapsed_in_window / window_size) + current_count`.

## Why Lua Scripts?

Token Bucket, Leaking Bucket, and Sliding Window Log all require **read → compute → write** as one atomic operation. Without atomicity, two concurrent requests can both read the same state and both be allowed when only one should be.

Redis is single-threaded and runs Lua scripts without interruption, so the entire sequence is atomic in one round-trip — no locks, no retries. Fixed Window and Sliding Window Counter don't need Lua because `INCR` is already atomic and the counter reads are advisory.

## How to Run

Requires Redis on `localhost:6379`.

```bash
# start Redis (Docker)
docker run -d -p 6379:6379 redis

# install and run
cd rate-limiter-demo
uv sync
uv run python main.py
```

## How to Observe

```bash
# hit the protected endpoint — watch X-RateLimit-* headers
curl -i http://localhost:8000/api/resource

# inspect raw Redis state for the active algorithm
curl http://localhost:8000/debug/state

# reset all rate-limit keys (useful between experiments)
curl -X POST http://localhost:8000/debug/reset
```

Change the `algorithm:` field in `rate_limit_config.yaml` and restart to switch algorithms. The `/debug/state` output will show exactly what each algorithm stores in Redis.
