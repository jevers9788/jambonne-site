# Mind Map Service

> **Note:** This is the recommended backend for mind map generation and integration with the Rust website. See the top-level `README.md` for project structure and integration details.

AI-powered mind map generation service for Safari reading lists. This service extracts your Safari reading list, scrapes content from URLs, generates embeddings, and creates interactive mind maps using clustering algorithms.

## Features

- **Safari Reading List Extraction**: Reads Safari bookmarks.plist
- **Web Content Scraping**: Intelligently extracts main content from web pages
- **Embedding Generation**: Uses sentence-transformers or OpenAI for text embeddings
- **Topic Clustering**: K-means, DBSCAN, and hierarchical clustering
- **Interactive Mind Maps**: Generate visual representations of your reading patterns
- **RESTful API**: Complete API for integration with frontend applications

## Quick Start

### Local Development

1. **Install dependencies**:
```bash
cd mindmap-service
uv sync
```

2. **Set up environment variables**:
```bash
cp env.example .env
# Edit .env with your configuration
```

3. **Run the service**:
```bash
uv run uvicorn src.main:app --reload
```

4. **Access the API**:
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/health

### Railway Deployment

1. **Install Railway CLI**:
```bash
npm install -g @railway/cli
```

2. **Login to Railway**:
```bash
railway login
```

3. **Initialize project**:
```bash
railway init
```

4. **Set environment variables**:
```bash
railway variables set OPENAI_API_KEY=your_openai_api_key_here
```

5. **Deploy**:
```bash
railway up
```

## API Endpoints

### Core Endpoints

- `GET /api/reading-list` - Get Safari reading list
- `POST /api/scrape-content` - Scrape content from URLs
- `POST /api/generate-embeddings` - Generate text embeddings
- `POST /api/create-mindmap` - Create mind map from embeddings
- `POST /api/process-reading-list` - Complete pipeline (recommended)

### Mind Map Management

- `GET /api/mindmap/{id}` - Get specific mind map
- `GET /api/mindmap/latest` - Get most recent mind map
- `DELETE /api/mindmap/{id}` - Delete mind map

### Utility Endpoints

- `GET /api/models/available` - List available embedding models
- `GET /api/health` - Health check

## Usage Examples

### Complete Pipeline (Recommended)

```bash
curl -X POST http://localhost:8000/api/process-reading-list
```

This single endpoint:
1. Reads your Safari reading list
2. Scrapes content from all URLs
3. Generates embeddings
4. Creates a mind map with clustering
5. Returns the complete mind map data

### Step-by-Step Process

1. **Get reading list**:
```bash
curl http://localhost:8000/api/reading-list
```

2. **Scrape content**:
```bash
curl -X POST http://localhost:8000/api/scrape-content \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com"],
    "options": {
      "max_content_length": 5000,
      "timeout": 10
    }
  }'
```

3. **Generate embeddings**:
```bash
curl -X POST http://localhost:8000/api/generate-embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "content": ["article content here"],
    "options": {
      "model": "all-MiniLM-L6-v2"
    }
  }'
```

4. **Create mind map**:
```bash
curl -X POST http://localhost:8000/api/create-mindmap \
  -H "Content-Type: application/json" \
  -d '{
    "embeddings": [[0.1, 0.2, ...]],
    "metadata": [{"title": "Article", "url": "https://example.com"}],
    "options": {
      "clustering_method": "kmeans",
      "n_clusters": 5
    }
  }'
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings | None |
| `PORT` | Server port | 8000 |
| `HOST` | Server host | 0.0.0.0 |
| `LOG_LEVEL` | Logging level | INFO |

### Embedding Models

- **all-MiniLM-L6-v2**: Fast, good quality (default)
- **all-mpnet-base-v2**: Higher quality, slower
- **openai**: OpenAI API (requires API key)

### Clustering Methods

- **kmeans**: K-means clustering (default)
- **dbscan**: Density-based clustering
- **hierarchical**: Hierarchical clustering

## Architecture

```
src/
├── main.py              # FastAPI application
├── models.py            # Pydantic data models
├── api/
│   └── routes.py        # API endpoints
└── services/
    ├── safari_reader.py # Safari reading list extraction
    ├── web_scraper.py   # Web content scraping
    ├── embeddings.py    # Embedding generation
    └── clustering.py    # Topic clustering
```

## Integration with Rust Website

To integrate with your Rust website, add a mind map page that fetches data from this service:

```rust
// In your Rust site
async fn mindmap() -> impl IntoResponse {
    let client = reqwest::Client::new();
    let response = client
        .get("https://your-railway-app.railway.app/api/mindmap/latest")
        .send()
        .await?;
    
    let mindmap_data = response.json().await?;
    MindmapTemplate { data: mindmap_data }
}
```

## Development

### Adding New Features

1. **Add new models** in `src/models.py`
2. **Create services** in `src/services/`
3. **Add API endpoints** in `src/api/routes.py`
4. **Update tests** in `tests/`

### Code Quality

```bash
# Format code
uv run black .

# Lint code
uv run flake8 .

# Type checking
uv run mypy src/
```

### Testing

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src
```

## Deployment Considerations

### Railway

- **Automatic scaling**: Railway handles scaling based on traffic
- **Environment variables**: Set via Railway dashboard or CLI
- **Custom domains**: Configure in Railway dashboard
- **Monitoring**: Built-in logs and metrics

### Production Checklist

- [ ] Set `CORS_ORIGINS` to your frontend domain
- [ ] Configure `OPENAI_API_KEY` if using OpenAI embeddings
- [ ] Set up monitoring and logging
- [ ] Configure rate limiting
- [ ] Set up database for persistent storage

### Cost Optimization

- **Local models**: Use sentence-transformers (free)
- **OpenAI**: ~$0.0001/1K tokens (very cheap)
- **Railway**: Pay per usage, scales to zero

## Troubleshooting

### Common Issues

1. **Safari bookmarks not found**: Ensure Safari is installed and has reading list items
2. **Scraping failures**: Some sites block automated requests
3. **Model loading errors**: Check internet connection for model downloads
4. **Memory issues**: Reduce batch sizes or use smaller models

### Logs

```bash
# View Railway logs
railway logs

# Local development logs
uv run uvicorn src.main:app --log-level debug
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details. 