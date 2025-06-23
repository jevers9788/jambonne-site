# Rust Website Mind Map Integration

> **Note:** For a project overview and structure, see the top-level `README.md`. This document provides detailed integration steps for connecting the Rust website to the Python mind map service.

This guide shows how to integrate the Python mind map service with your Rust website.

## 1. Add Mind Map Route to Rust Website

Add this to your `src/main.rs`:

```rust
use serde::{Deserialize, Serialize};
use reqwest;

// Mind map data structures
#[derive(Deserialize, Serialize)]
struct MindMapNode {
    id: String,
    title: String,
    url: String,
    cluster: i32,
    position: Position,
    keywords: Vec<String>,
    content_preview: String,
}

#[derive(Deserialize, Serialize)]
struct Position {
    x: f64,
    y: f64,
}

#[derive(Deserialize, Serialize)]
struct MindMapEdge {
    source: String,
    target: String,
    weight: f64,
}

#[derive(Deserialize, Serialize)]
struct MindMapCluster {
    id: i32,
    name: String,
    keywords: Vec<String>,
    articles: Vec<String>,
}

#[derive(Deserialize, Serialize)]
struct MindMapData {
    id: String,
    nodes: Vec<MindMapNode>,
    edges: Vec<MindMapEdge>,
    clusters: Vec<MindMapCluster>,
    metadata: serde_json::Value,
    created_at: String,
}

// Mind map template
#[derive(Template)]
#[template(path = "mindmap.html")]
struct MindMapTemplate {
    mindmap: Option<MindMapData>,
    error: Option<String>,
}

// Mind map handler
async fn mindmap() -> impl IntoResponse {
    let mindmap_service_url = std::env::var("MINDMAP_SERVICE_URL")
        .unwrap_or_else(|_| "http://localhost:8000".to_string());
    
    let client = reqwest::Client::new();
    let response = client
        .get(&format!("{}/api/mindmap/latest", mindmap_service_url))
        .send()
        .await;
    
    match response {
        Ok(resp) => {
            match resp.json::<MindMapData>().await {
                Ok(mindmap_data) => MindMapTemplate {
                    mindmap: Some(mindmap_data),
                    error: None,
                },
                Err(e) => MindMapTemplate {
                    mindmap: None,
                    error: Some(format!("Failed to parse mind map data: {}", e)),
                },
            }
        }
        Err(e) => MindMapTemplate {
            mindmap: None,
            error: Some(format!("Failed to fetch mind map: {}", e)),
        },
    }
}

// Add to your router
let app = Router::new()
    .route("/", get(landing))
    .route("/blog", get(blog))
    .route("/blog/:slug", get(blog_post))
    .route("/cv", get(cv))
    .route("/mindmap", get(mindmap))  // Add this line
    .route("/static/*path", get(static_handler));
```

## 2. Create Mind Map Template

Create `templates/mindmap.html`:

```html
{% extends "base.html" %}

{% block title %}Mind Map - My Reading List{% endblock %}

{% block content %}
<div class="mindmap-container">
    <h1>My Reading List Mind Map</h1>
    
    {% if error %}
    <div class="error-message">
        <p>Error: {{ error }}</p>
        <p>Make sure the mind map service is running and accessible.</p>
    </div>
    {% elif mindmap %}
    <div class="mindmap-info">
        <p>Generated on: {{ mindmap.created_at }}</p>
        <p>Total articles: {{ mindmap.nodes | length }}</p>
        <p>Clusters: {{ mindmap.clusters | length }}</p>
    </div>
    
    <div class="mindmap-visualization">
        <div id="mindmap-canvas"></div>
    </div>
    
    <div class="mindmap-clusters">
        <h3>Topic Clusters</h3>
        {% for cluster in mindmap.clusters %}
        <div class="cluster">
            <h4>{{ cluster.name }}</h4>
            <p>Articles: {{ cluster.articles | length }}</p>
            <p>Keywords: {{ cluster.keywords | join(", ") }}</p>
        </div>
        {% endfor %}
    </div>
    
    <div class="mindmap-articles">
        <h3>Articles</h3>
        {% for node in mindmap.nodes %}
        <div class="article">
            <h4><a href="{{ node.url }}" target="_blank">{{ node.title }}</a></h4>
            <p>Cluster: {{ node.cluster }}</p>
            <p>Keywords: {{ node.keywords | join(", ") }}</p>
            <p>{{ node.content_preview }}</p>
        </div>
        {% endfor %}
    </div>
    
    <script>
        // Mind map visualization using D3.js or similar
        const mindmapData = {{ mindmap | tojson }};
        
        // Initialize visualization
        function initMindMap() {
            const width = 800;
            const height = 600;
            
            const svg = d3.select("#mindmap-canvas")
                .append("svg")
                .attr("width", width)
                .attr("height", height);
            
            // Create force simulation
            const simulation = d3.forceSimulation(mindmapData.nodes)
                .force("link", d3.forceLink(mindmapData.edges).id(d => d.id))
                .force("charge", d3.forceManyBody().strength(-100))
                .force("center", d3.forceCenter(width / 2, height / 2));
            
            // Draw links
            const links = svg.append("g")
                .selectAll("line")
                .data(mindmapData.edges)
                .enter().append("line")
                .attr("stroke", "#999")
                .attr("stroke-opacity", 0.6)
                .attr("stroke-width", d => Math.sqrt(d.weight) * 2);
            
            // Draw nodes
            const nodes = svg.append("g")
                .selectAll("circle")
                .data(mindmapData.nodes)
                .enter().append("circle")
                .attr("r", 5)
                .attr("fill", d => d3.schemeCategory10[d.cluster % 10])
                .call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended));
            
            // Add tooltips
            nodes.append("title")
                .text(d => d.title);
            
            // Update positions on simulation tick
            simulation.on("tick", () => {
                links
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);
                
                nodes
                    .attr("cx", d => d.x)
                    .attr("cy", d => d.y);
            });
            
            function dragstarted(event, d) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            }
            
            function dragged(event, d) {
                d.fx = event.x;
                d.fy = event.y;
            }
            
            function dragended(event, d) {
                if (!event.active) simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            }
        }
        
        // Load D3.js and initialize
        if (typeof d3 !== 'undefined') {
            initMindMap();
        } else {
            // Load D3.js dynamically
            const script = document.createElement('script');
            script.src = 'https://d3js.org/d3.v7.min.js';
            script.onload = initMindMap;
            document.head.appendChild(script);
        }
    </script>
    {% else %}
    <div class="no-data">
        <p>No mind map data available.</p>
        <p>Try running the mind map service first.</p>
    </div>
    {% endif %}
</div>
{% endblock %}
```

## 3. Add CSS Styles

Add to your `static/style.css`:

```css
/* Mind Map Styles */
.mindmap-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.mindmap-info {
    background: #f5f5f5;
    padding: 15px;
    border-radius: 5px;
    margin-bottom: 20px;
}

.mindmap-visualization {
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 20px;
    margin-bottom: 30px;
    background: white;
}

#mindmap-canvas {
    width: 100%;
    height: 600px;
    border: 1px solid #eee;
}

.mindmap-clusters {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.cluster {
    background: #f9f9f9;
    padding: 15px;
    border-radius: 5px;
    border-left: 4px solid #007acc;
}

.cluster h4 {
    margin: 0 0 10px 0;
    color: #333;
}

.mindmap-articles {
    display: grid;
    gap: 15px;
}

.article {
    background: white;
    padding: 15px;
    border-radius: 5px;
    border: 1px solid #eee;
}

.article h4 {
    margin: 0 0 10px 0;
}

.article h4 a {
    color: #007acc;
    text-decoration: none;
}

.article h4 a:hover {
    text-decoration: underline;
}

.error-message {
    background: #ffebee;
    color: #c62828;
    padding: 15px;
    border-radius: 5px;
    border: 1px solid #ffcdd2;
}

.no-data {
    text-align: center;
    padding: 40px;
    color: #666;
}
```

## 4. Update Cargo.toml

Add these dependencies to your `Cargo.toml`:

```toml
[dependencies]
# ... existing dependencies ...
reqwest = { version = "0.11", features = ["json"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tokio = { version = "1.0", features = ["full"] }
```

## 5. Environment Configuration

Set the mind map service URL in your environment:

```bash
# For local development
export MINDMAP_SERVICE_URL=http://localhost:8000

# For production (after deploying to Railway)
export MINDMAP_SERVICE_URL=https://your-mindmap-service.railway.app
```

## 6. Add Navigation Link

Update your `templates/base.html` to include a link to the mind map:

```html
<nav>
    <a href="/">Home</a>
    <a href="/blog">Blog</a>
    <a href="/cv">CV</a>
    <a href="/mindmap">Mind Map</a>  <!-- Add this line -->
</nav>
```

## 7. Deployment

1. **Deploy the Python service to Railway**:
```bash
cd mindmap-service
railway up
```

2. **Deploy your Rust website** (as usual):
```bash
cargo build --release
# Deploy to your hosting platform
```

3. **Set environment variables** in your Rust website deployment:
   - `MINDMAP_SERVICE_URL`: Your Railway app URL

## Benefits of This Integration

- **Clean separation**: Rust site stays fast and simple
- **AI capabilities**: Python service handles all ML workloads
- **Scalable**: Each service can scale independently
- **Cost-effective**: Only pay for Python service when generating mind maps
- **Maintainable**: Clear boundaries between frontend and backend

The mind map will be accessible at `/mindmap` on your Rust website and will automatically fetch the latest mind map data from your Railway-deployed Python service! 