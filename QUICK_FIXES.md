# Quick Fixes - Critical Issues

## 1. Remove Environment Variable Logging (15 minutes)

**File:** `src/main.rs` (lines 333-335)  
**Current Code:**
```rust
for (key, value) in std::env::vars() {
    println!("env: {}={}", key, value);
}
```

**Fixed Code:**
```rust
// Remove entirely or replace with:
#[cfg(debug_assertions)]
{
    eprintln!("Debug mode enabled");
}
```

**Why:** Prevents API keys and secrets from being logged.

---

## 2. Fix Path Traversal Vulnerability (30-60 minutes)

**File:** `src/main.rs` (lines 222-237)  
**Current Code:**
```rust
async fn blog_post(Path(slug): Path<String>) -> Response {
    let posts_dirs = ["posts", "/app/posts"];
    let mut path = String::new();
    
    for posts_dir in posts_dirs {
        let test_path = format!("{}/{}.md", posts_dir, slug);
        if FsPath::new(&test_path).exists() {
            path = test_path;
            break;
        }
    }
```

**Fixed Code:**
```rust
fn is_valid_slug(slug: &str) -> bool {
    !slug.is_empty()
        && slug.len() < 256
        && slug.chars().all(|c| c.is_alphanumeric() || c == '-' || c == '_')
}

async fn blog_post(Path(slug): Path<String>) -> Response {
    // Validate slug first
    if !is_valid_slug(&slug) {
        return axum::http::StatusCode::BAD_REQUEST.into_response();
    }
    
    let posts_dirs = ["posts", "/app/posts"];
    let mut path = String::new();
    
    for posts_dir in posts_dirs {
        let test_path = format!("{}/{}.md", posts_dir, slug);
        if FsPath::new(&test_path).exists() {
            path = test_path;
            break;
        }
    }
    // ... rest of function
}
```

**Why:** Prevents reading arbitrary files via path traversal (e.g., `../../../etc/passwd`).

---

## 3. Fix CORS Configuration (30 minutes)

**File:** `mindmap-service/src/main.py` (lines 21-28)  
**Current Code:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Fixed Code:**
```python
import os

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,  # Set to True only if using sessions
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

**Add to `.env` or environment:**
```bash
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

**Why:** Prevents CSRF attacks and limits API access to your own domain.

---

## 4. Enable HTML Escaping in Templates (15 minutes)

**File:** `src/main.rs` (line 174)  
**Current Code:**
```rust
#[template(path = "reading.html", escape = "none")]
struct ReadingTemplate {
```

**Fixed Code:**
```rust
#[template(path = "reading.html")]  // Remove escape = "none"
struct ReadingTemplate {
```

**In template `templates/reading.html`:**
```html
<!-- Current (vulnerable): -->
<a href="{{ node.url }}" target="_blank">

<!-- Fixed: -->
<a href="{{ node.url }}" target="_blank">
```

**Why:** Prevents XSS attacks if mind map data contains malicious content.

---

## 5. Fix Deprecated datetime.utcnow() (15 minutes)

**File:** `mindmap-service/src/api/routes.py` (lines 97, 197, 237)  
**Current Code:**
```python
from datetime import datetime

created_at=datetime.utcnow()
timestamp: datetime.utcnow().isoformat()
```

**Fixed Code:**
```python
from datetime import datetime, timezone

created_at=datetime.now(timezone.utc)
timestamp: datetime.now(timezone.utc).isoformat()
```

**Why:** Current code is deprecated and will break in Python 3.14.

---

## 6. Remove Debug Print Statements (30 minutes)

**File:** `mindmap-service/src/api/routes.py` (lines 112-113, 120-121, 202-204)  
**Current Code:**
```python
print(f"DEBUG: mind_maps keys: {list(mind_maps.keys())}")
print(f"DEBUG: mind_maps length: {len(mind_maps)}")
print(f"DEBUG: latest_id: {latest_id}")
print(f"DEBUG: latest mind map type: {type(mind_maps[latest_id])}")
print(f"DEBUG: Stored mind map with ID: {mindmap_id}")
```

**Fixed Code:**
```python
import logging

logger = logging.getLogger(__name__)

# Replace all print() calls with:
logger.debug(f"Mind maps stored: {len(mind_maps)}")
logger.info(f"Stored mind map with ID: {mindmap_id}")
```

**Why:** Proper logging is cleaner, can be configured by log level, and is production-safe.

---

## Testing the Fixes

After applying these fixes:

```bash
# Rust
cargo fmt
cargo clippy
cargo test

# Python
cd mindmap-service
uv run black .
uv run ruff check .
uv run mypy src/
```

---

## Verification

- [ ] Path validation prevents `../../../etc/passwd` access
- [ ] CORS only allows specified origins
- [ ] No environment variables logged
- [ ] No debug print statements in code
- [ ] Code passes linters (clippy, ruff, mypy)
- [ ] HTML escaping is enabled in templates
- [ ] datetime uses timezone.utc instead of utcnow()

---

## Total Time: ~2 hours for all 6 critical fixes

These fixes should be applied before any production deployment.
