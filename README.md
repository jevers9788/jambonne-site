# Jambonne: Personal Website

This repository houses the Rust/Axum site that is currently deployed. A separate `mindmap-service/` FastAPI project still lives in the repo, but it is **decoupled for now** while it undergoes heavy changes and is not part of the running site.

- **Rust Website (Frontend):** Fast, type-safe web frontend that powers the live site (landing page, about, reading list).
- **Mind Map Service (On Hold):** Experimental FastAPI microservice kept in `mindmap-service/` for future work but intentionally not wired into the site or deployment pipeline.
- **Python Scripts:** Standalone utilities (e.g., exporting the Safari reading list) used by the Rust site.

---

## Project Structure

- `src/` — Rust web application (frontend)
- `mindmap-service/` — FastAPI microservice (experimental, currently decoupled)
- `scripts/` — Python utilities (e.g., Safari reading list export)
- `templates/` — Askama HTML templates
- `static/` — Static assets (CSS, fonts, images, data)

---

## Current Workflow

1. **Export your Safari Reading List (if you want `/reading` populated)** using the provided Python script.
2. **Run the Rust site** locally or via Docker.
3. **(Optional)** Work on the experimental mind map service separately; it no longer needs to be running for the site to build or serve pages.

## Quick Start

### 1. Export Your Safari Reading List
```bash
uv run python scripts/export_reading_list.py \
  --output static/data/reading_list.json
```
- Requires Full Disk Access for your terminal the first time you read `Bookmarks.plist`.
- Checks `~/Library/Safari/Bookmarks.plist`, extracts title/url/date, and writes JSON your site can embed or copy into a Docker image.
- Override the destination with `--output` or set the `READING_LIST_FILE` env var for the Rust server.
- When building Docker images, copy the exported JSON into the container so `/reading` works without macOS data access.

### 2. Rust Website
```bash
cargo run
# Visit http://localhost:3000/
```

---

## Mind Map Service (On Hold)

The FastAPI service still lives in `mindmap-service/`, but it is intentionally decoupled:

- Not referenced by the Rust router.
- Not linted or built by default (`just lint-all` skips it; use `just lint-mindmap` if you need to work on it).
- Deployment manifests do not start it.

You can still develop it independently by following [`mindmap-service/README.md`](mindmap-service/README.md) when you’re ready to re-integrate.

---

## Contributing & Development
- See each subproject's README for development, testing, and deployment instructions.
- All Python and Rust code is formatted and linted using standard tools (see Makefiles and pyproject.toml).

---

## License
MIT 
