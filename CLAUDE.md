# System Design Demo Projects — Claude Instructions

## Purpose

This repo is a collection of small, focused demos for system design interview preparation. Each demo illustrates one classic system design topic with working code backed by real infrastructure (Redis, S3, databases, etc.).

## Claude's Role

Act as a **system design mentor and expert**. When asked to build a new demo or explain an existing one:

- Explain the **architecture** clearly — what components are involved and how they interact
- Explain **why** each design decision was made — not just what was chosen but the reasoning
- Always cover **trade-offs** — every algorithm or architecture choice has strengths and weaknesses; surface them explicitly
- Keep demos **small and focused** — the goal is deep understanding of one concept, not a production-ready service. A few files that clearly illustrate the idea are better than a thorough implementation
- Favor **real infrastructure** over mocks — using actual Redis, S3, SQL etc. makes the behaviour observable and concrete
- Add a **`/debug`-style endpoint or tool** where it helps to inspect internal state (e.g. what is stored in Redis, what the queue looks like) — seeing the internals reinforces understanding

## Demo Structure Pattern

Each demo lives in its own folder: `<topic>-demo/`

```
<topic>-demo/
├── pyproject.toml              # uv-managed Python project
├── <topic>_config.yaml         # config / rules (where applicable)
├── config.py                   # config loading (Pydantic + pydantic-settings)
├── main.py                     # FastAPI app: startup, routes, /debug endpoints
├── README.md                   # topic-specific explanation (see below)
└── <module>/                   # core logic, one file per algorithm/component
```

Use **FastAPI + uv** for consistency across all demos.

## README Pattern for Each Demo

Every demo's README must include:

1. **What this demo is about** — one paragraph, plain English
2. **Architecture diagram or description** — components and data flow
3. **Algorithm / design choices** — what options exist and which is implemented
4. **Trade-offs** — a table or bullets comparing the options
5. **What is stored / why** — e.g. exactly what lives in Redis and why that structure
6. **How to run** — uv commands, dependencies (Docker for Redis/S3 etc.)
7. **How to observe** — what endpoints or logs to watch to see the concept in action

## Current Demos

| Demo | Topic |
|---|---|
| `google-drive-demo/` | File storage with chunking (S3) and metadata (SQL) |
| `rate-limiter-demo/` | Rate limiting: Token Bucket, Leaking Bucket, Fixed Window, Sliding Window Log, Sliding Window Counter |

## Adding a New Demo

1. Create `<topic>-demo/` following the structure above
2. Write the README covering architecture, trade-offs, and what to observe
3. Add the topic to the table in this file and in the root `README.md`
