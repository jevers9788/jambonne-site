# Project Structure

> **Note:** For the most up-to-date project structure and integration overview, see the top-level `README.md`.

# Project Restructure for Embeddings-Based Mind Maps

## Recommended Architecture: Microservices

```
jambonne-site/
├── rust-website/                 # Current Rust site (unchanged)
│   ├── src/
│   ├── templates/
│   ├── static/
│   ├── posts/
│   ├── Cargo.toml
│   └── Dockerfile
│
├── mindmap-service/              # New Python service
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI server
│   │   ├── models.py            # Pydantic models
│   │   ├── embeddings.py        # Embedding generation
│   │   ├── clustering.py        # Topic clustering
│   │   └── visualization.py     # Mind map generation
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py            # API endpoints
│   │   └── middleware.py        # CORS, auth, etc.
│   ├── services/
│   │   ├── __init__.py
│   │   ├── safari_reader.py     # Safari reading list extraction
│   │   ├── web_scraper.py       # Content scraping
│   │   └── mindmap_generator.py # Mind map creation
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── text_processing.py   # Text cleaning, keyword extraction
│   │   └── file_handlers.py     # JSON, file operations
│   ├── tests/
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── README.md
│
├── shared/                      # Shared data structures
│   ├── types/
│   │   ├── reading_list.rs      # Rust types
│   │   └── reading_list.py      # Python types
│   └── schemas/
│       └── mindmap.json         # JSON schemas
│
├── scripts/                     # Keep existing scripts (legacy)
│   ├── reading_list.py
│   ├── mind_map_visualizer.py
│   └── setup.sh
│
├── docker-compose.yml           # Service orchestration
├── .github/
│   └── workflows/
│       ├── rust-website.yml
│       └── mindmap-service.yml
└── README.md
```

## Service Responsibilities

### Rust Website (Frontend)
- **Purpose**: Static site hosting, blog, portfolio
- **Features**: 
  - Display mind maps (via iframe or API calls)
  - Blog posts about mind map insights
  - Portfolio showcase
- **Tech**: Axum, Askama templates
- **Deployment**: Static hosting (Vercel, Netlify, etc.)

### Mind Map Service (Backend)
- **Purpose**: AI-powered mind map generation
- **Features**:
  - Safari reading list extraction
  - Web content scraping
  - Embedding generation (OpenAI, local models)
  - Topic clustering and visualization
  - API endpoints for mind map data
- **Tech**: FastAPI, sentence-transformers, scikit-learn
- **Deployment**: Containerized (Docker, Kubernetes)

## API Design

### Mind Map Service Endpoints

```python
# GET /api/reading-list
# Extract Safari reading list
{
  "entries": [
    {
      "title": "Article Title",
      "url": "https://example.com",
      "date_added": "2024-01-01T00:00:00Z"
    }
  ]
}

# POST /api/scrape-content
# Scrape content from URLs
{
  "urls": ["https://example.com"],
  "options": {
    "max_content_length": 5000,
    "include_metadata": true
  }
}

# POST /api/generate-embeddings
# Generate embeddings for content
{
  "content": ["article content 1", "article content 2"],
  "model": "all-MiniLM-L6-v2"  # or "openai"
}

# POST /api/create-mindmap
# Generate mind map from embeddings
{
  "embeddings": [...],
  "metadata": [...],
  "options": {
    "clustering_method": "kmeans",
    "n_clusters": 5,
    "visualization_type": "interactive"
  }
}

# GET /api/mindmap/{id}
# Retrieve generated mind map
{
  "id": "mindmap_123",
  "nodes": [...],
  "edges": [...],
  "clusters": [...],
  "metadata": {...}
}
```

## Integration Points

### 1. Rust Website → Mind Map Service
```rust
// In your Rust site, add a mind map page
async fn mindmap() -> impl IntoResponse {
    // Fetch mind map data from Python service
    let client = reqwest::Client::new();
    let response = client
        .get("http://mindmap-service:8000/api/mindmap/latest")
        .send()
        .await?;
    
    let mindmap_data = response.json().await?;
    MindmapTemplate { data: mindmap_data }
}
```

### 2. Shared Data Types
```rust
// shared/types/reading_list.rs
#[derive(Serialize, Deserialize)]
pub struct ReadingListEntry {
    pub title: String,
    pub url: String,
    pub date_added: DateTime<Utc>,
    pub content: Option<String>,
}
```

```python
# shared/types/reading_list.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ReadingListEntry(BaseModel):
    title: str
    url: str
    date_added: datetime
    content: Optional[str] = None
```

## Development Workflow

### Local Development
```bash
# Start all services
docker-compose up

# Or develop individually
cd rust-website && cargo run
cd mindmap-service && uv run python -m uvicorn src.main:app --reload
```

### Deployment
```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml up -d

# Or deploy separately
# Rust site to Vercel/Netlify
# Python service to Railway/Render/DigitalOcean
```

## Benefits of This Approach

1. **Scalability**: Each service can scale independently
2. **Technology Fit**: Python for ML, Rust for performance
3. **Maintainability**: Clear separation of concerns
4. **Flexibility**: Easy to add new features to either service
5. **Deployment**: Can deploy to different platforms optimized for each tech stack

## Migration Strategy

1. **Phase 1**: Create mind map service alongside existing scripts
2. **Phase 2**: Add API endpoints to Rust site for mind map display
3. **Phase 3**: Migrate from scripts to service-based approach
4. **Phase 4**: Add advanced features (real-time updates, user accounts)

## Cost Considerations

- **Rust site**: Free/cheap static hosting
- **Python service**: 
  - Embedding API costs (OpenAI: ~$0.0001/1K tokens)
  - Compute costs for clustering/visualization
  - Storage for mind map data

This architecture gives you the best of both worlds: a fast, reliable Rust frontend and a powerful Python backend for AI/ML features. 