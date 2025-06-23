use askama::Template;
use askama_axum::IntoResponse;
use axum::response::Response;
use axum::{extract::Path, routing::get, Router};
use include_dir::{include_dir, Dir};
use pulldown_cmark::{html, Options, Parser};
use serde::{Deserialize, Serialize};
use std::fs;
use std::net::SocketAddr;
use std::path::Path as FsPath;
use tokio::net::TcpListener;

pub mod filters {
    use askama::Result as AskamaResult;
    use serde::Serialize;
    pub fn join_keywords(keywords: &[String], sep: &str) -> AskamaResult<String> {
        Ok(keywords.join(sep))
    }
    pub fn tojson<T: Serialize>(value: &T) -> AskamaResult<String> {
        serde_json::to_string(value)
            .map_err(|_| askama::Error::Custom("JSON serialization failed".into()))
    }
}

pub use crate::filters::*;

// Embed static files directly into the binary
static STATIC_DIR: Dir<'_> = include_dir!("static");

#[derive(Template)]
#[template(path = "index.html")]
struct IndexTemplate;

#[derive(Template)]
#[template(path = "blog.html")]
struct BlogTemplate {
    posts: Vec<BlogPostMeta>,
}

#[derive(Template)]
#[template(path = "cv.html")]
struct CvTemplate;

#[derive(Template)]
#[template(path = "article.html")]
struct ArticleTemplate {
    title: String,
    content: String,
}

// Mind map data structures
#[derive(Deserialize, Serialize, Debug)]
struct MindMapNode {
    id: String,
    title: String,
    url: String,
    cluster: i32,
    position: Position,
    keywords: Vec<String>,
    content_preview: String,
}

#[derive(Deserialize, Serialize, Debug)]
struct Position {
    x: f64,
    y: f64,
}

#[derive(Deserialize, Serialize, Debug)]
struct MindMapEdge {
    source: String,
    target: String,
    weight: f64,
}

#[derive(Deserialize, Serialize, Debug)]
struct MindMapCluster {
    id: i32,
    name: String,
    keywords: Vec<String>,
    articles: Vec<i32>,
}

#[derive(Deserialize, Serialize, Debug)]
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
#[template(path = "mindmap.html", escape = "none")]
struct MindMapTemplate {
    mindmap: Option<MindMapData>,
    error: Option<String>,
}

struct BlogPostMeta {
    slug: String,
    title: String,
}

async fn landing() -> impl axum::response::IntoResponse {
    IndexTemplate
}

async fn blog() -> impl axum::response::IntoResponse {
    let mut posts = Vec::new();

    // Try different possible locations for the posts directory
    let posts_dirs = ["posts", "/app/posts"];

    for posts_dir in posts_dirs {
        if let Ok(entries) = fs::read_dir(posts_dir) {
            for entry in entries.flatten() {
                if let Some(ext) = entry.path().extension() {
                    if ext == "md" {
                        let filename = entry.file_name().to_string_lossy().to_string();
                        let slug = filename.trim_end_matches(".md").to_string();
                        let content = fs::read_to_string(entry.path()).unwrap_or_default();
                        let title = content
                            .lines()
                            .next()
                            .unwrap_or("Untitled")
                            .trim_start_matches('#')
                            .trim()
                            .to_string();
                        posts.push(BlogPostMeta { slug, title });
                    }
                }
            }
            break; // Found posts directory, stop looking
        }
    }

    posts.sort_by(|a, b| b.slug.cmp(&a.slug));
    BlogTemplate { posts }
}

async fn blog_post(Path(slug): Path<String>) -> Response {
    // Try different possible locations for the posts directory
    let posts_dirs = ["posts", "/app/posts"];
    let mut path = String::new();

    for posts_dir in posts_dirs {
        let test_path = format!("{}/{}.md", posts_dir, slug);
        if FsPath::new(&test_path).exists() {
            path = test_path;
            break;
        }
    }

    if path.is_empty() {
        return axum::http::StatusCode::NOT_FOUND.into_response();
    }

    let markdown = fs::read_to_string(&path).unwrap_or_default();
    let mut lines = markdown.lines();
    let title = lines
        .next()
        .unwrap_or("Untitled")
        .trim_start_matches('#')
        .trim();
    let content_md: String = lines.collect::<Vec<_>>().join("\n");

    let mut html_output = String::new();
    let parser = Parser::new_ext(&content_md, Options::all());
    html::push_html(&mut html_output, parser);

    ArticleTemplate {
        title: title.to_string(),
        content: html_output,
    }
    .into_response()
}

async fn cv() -> impl axum::response::IntoResponse {
    CvTemplate
}

// Mind map handler
async fn mindmap() -> impl IntoResponse {
    let mindmap_service_url = std::env::var("MINDMAP_SERVICE_URL")
        .unwrap_or_else(|_| "http://localhost:8000".to_string());

    let client = reqwest::Client::new();
    let response = client
        .get(format!("{}/api/mindmap/latest", mindmap_service_url))
        .send()
        .await;

    match response {
        Ok(resp) => match resp.json::<MindMapData>().await {
            Ok(mindmap_data) => MindMapTemplate {
                mindmap: Some(mindmap_data),
                error: None,
            }
            .into_response(),
            Err(e) => MindMapTemplate {
                mindmap: None,
                error: Some(format!("Failed to parse mind map data: {}", e)),
            }
            .into_response(),
        },
        Err(e) => MindMapTemplate {
            mindmap: None,
            error: Some(format!("Failed to fetch mind map: {}", e)),
        }
        .into_response(),
    }
}

// Custom static file handler that serves from embedded files
async fn static_handler(Path(path): Path<String>) -> Response {
    if let Some(file) = STATIC_DIR.get_file(&path) {
        let content_type = match path.split('.').next_back() {
            Some("css") => "text/css",
            Some("js") => "application/javascript",
            Some("png") => "image/png",
            Some("jpg") | Some("jpeg") => "image/jpeg",
            Some("svg") => "image/svg+xml",
            Some("woff") => "font/woff",
            Some("woff2") => "font/woff2",
            Some("ttf") => "font/ttf",
            _ => "text/plain",
        };
        let headers = [("content-type", content_type)];
        return (headers, file.contents()).into_response();
    }
    axum::http::StatusCode::NOT_FOUND.into_response()
}

#[tokio::main]
async fn main() {
    println!("Starting jambonne-site...");
    println!("Static files embedded in binary");

    // Log environment variables
    for (key, value) in std::env::vars() {
        println!("env: {}={}", key, value);
    }

    let app = Router::new()
        .route(
            "/",
            get(|| async {
                println!("Handling landing page request");
                landing().await
            }),
        )
        .route(
            "/blog",
            get(|| async {
                println!("Handling blog page request");
                blog().await
            }),
        )
        .route(
            "/blog/:slug",
            get(|path| async move {
                println!("Handling blog post request: {:?}", path);
                blog_post(path).await
            }),
        )
        .route(
            "/cv",
            get(|| async {
                println!("Handling CV page request");
                cv().await
            }),
        )
        .route(
            "/mindmap",
            get(|| async {
                println!("Handling mindmap page request");
                mindmap().await
            }),
        )
        .route(
            "/static/*path",
            get(|path| async move {
                println!("Handling static file request: {:?}", path);
                static_handler(path).await
            }),
        );

    // Use environment variables for deployment flexibility
    let port = std::env::var("PORT").unwrap_or_else(|_| "3000".to_string());
    let port: u16 = port.parse().unwrap_or(3000);
    println!("Using port: {}", port);

    // For deployment, bind to all interfaces
    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    println!("Attempting to bind to: {}", addr);

    let listener = match TcpListener::bind(addr).await {
        Ok(listener) => {
            println!("Successfully bound to {}", addr);
            listener
        }
        Err(e) => {
            eprintln!("Failed to bind to {}: {}", addr, e);
            std::process::exit(1);
        }
    };

    println!("Starting server...");
    if let Err(e) = axum::serve(listener, app).await {
        eprintln!("Server error: {}", e);
        std::process::exit(1);
    }
}
