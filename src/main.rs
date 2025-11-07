use askama::Template;
use askama_axum::IntoResponse;
use axum::response::Response;
use axum::{extract::Path, routing::get, Router};
use chrono::Utc;
use include_dir::{include_dir, Dir};
use once_cell::sync::Lazy;
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
#[template(path = "about.html")]
struct AboutTemplate;

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
struct ReadingData {
    id: String,
    nodes: Vec<MindMapNode>,
    edges: Vec<MindMapEdge>,
    clusters: Vec<MindMapCluster>,
    metadata: serde_json::Value,
    created_at: String,
}

#[derive(Deserialize, Serialize, Debug)]
struct ReadingListItem {
    title: String,
    url: String,
    date_added: String,
}

// Global reading list data - thread-safe lazy initialization
const DEFAULT_READING_LIST_FILE: &str = "static/data/reading_list.json";

static READING_LIST: Lazy<Vec<ReadingListItem>> = Lazy::new(|| {
    load_reading_list_from_file().unwrap_or_else(|e| {
        eprintln!("Failed to load reading list: {}", e);
        Vec::new()
    })
});

fn load_reading_list_from_file() -> Result<Vec<ReadingListItem>, Box<dyn std::error::Error>> {
    let path = std::env::var("READING_LIST_FILE")
        .unwrap_or_else(|_| DEFAULT_READING_LIST_FILE.to_string());
    let data = fs::read_to_string(&path)?;
    let items: Vec<ReadingListItem> = serde_json::from_str(&data)?;
    Ok(items)
}

// Mind map template
#[derive(Template)]
#[template(path = "reading.html")]
struct ReadingTemplate {
    reading: Option<ReadingData>,
    error: Option<String>,
}

struct BlogPostMeta {
    slug: String,
    title: String,
}

fn is_valid_slug(slug: &str) -> bool {
    let len = slug.len();
    len > 0
        && len <= 128
        && slug
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
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
    if !is_valid_slug(&slug) {
        return axum::http::StatusCode::BAD_REQUEST.into_response();
    }

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

async fn about() -> impl axum::response::IntoResponse {
    AboutTemplate
}

fn build_router() -> Router {
    Router::new()
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
            "/reading",
            get(|| async {
                println!("Handling reading list page request");
                reading().await
            }),
        )
        .route(
            "/about",
            get(|| async {
                println!("Handling about page request");
                about().await
            }),
        )
        .route(
            "/static/*path",
            get(|path| async move {
                println!("Handling static file request: {:?}", path);
                static_handler(path).await
            }),
        )
}

// Reading list handler
async fn reading() -> impl IntoResponse {
    let items = &*READING_LIST;

    if items.is_empty() {
        return ReadingTemplate {
            reading: None,
            error: Some("No reading list items found".to_string()),
        }
        .into_response();
    }

    // Convert ReadingListItem to MindMapNode for template compatibility
    let nodes: Vec<MindMapNode> = items
        .iter()
        .enumerate()
        .map(|(i, item)| MindMapNode {
            id: i.to_string(),
            title: item.title.clone(),
            url: item.url.clone(),
            cluster: 0,
            position: Position { x: 0.0, y: 0.0 },
            keywords: vec![],
            content_preview: "".to_string(),
        })
        .collect();

    let reading_data = ReadingData {
        id: "reading-list".to_string(),
        nodes,
        edges: vec![],
        clusters: vec![],
        metadata: serde_json::json!({}),
        created_at: Utc::now().to_rfc3339(),
    };

    ReadingTemplate {
        reading: Some(reading_data),
        error: None,
    }
    .into_response()
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
            Some("pdf") => "application/pdf",
            _ => "text/plain",
        };
        let headers = [("content-type", content_type)];
        return (headers, file.contents()).into_response();
    }
    axum::http::StatusCode::NOT_FOUND.into_response()
}

#[tokio::main]
async fn main() {
    println!("Reached main!");
    println!("Starting jambonne-site...");
    println!("Static files embedded in binary");

    let app = build_router();

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

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{body::Body, http::Request};
    use tower::util::ServiceExt;

    #[tokio::test]
    async fn landing_route_returns_ok() {
        let app = build_router();
        let response = app
            .clone()
            .oneshot(
                Request::builder()
                    .uri("/")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), axum::http::StatusCode::OK);
    }

    #[tokio::test]
    async fn blog_route_rejects_traversal_slug() {
        let app = build_router();
        let response = app
            .clone()
            .oneshot(
                Request::builder()
                    .uri("/blog/bad!slug")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), axum::http::StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn blog_route_valid_slug_missing_file() {
        let app = build_router();
        let response = app
            .oneshot(
                Request::builder()
                    .uri("/blog/nonexistent-slug")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), axum::http::StatusCode::NOT_FOUND);
    }
}
