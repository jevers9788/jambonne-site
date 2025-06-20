use askama::Template;
use askama_axum::IntoResponse;
use axum::response::Response;
use axum::{extract::Path, routing::get, Router};
use pulldown_cmark::{html, Options, Parser};
use std::fs;
use std::net::SocketAddr;
use std::path::Path as FsPath;
use tokio::net::TcpListener;
use tower_http::services::ServeDir;
use include_dir::{include_dir, Dir};
use std::env;

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

// Custom static file handler that serves from embedded files
async fn static_handler(Path(path): Path<String>) -> Response {
    let file_path = format!("static/{}", path);
    
    if let Some(file) = STATIC_DIR.get_file(&file_path) {
        let content_type = match path.split('.').last() {
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
    println!("Static files embedded in binary");

    let app = Router::new()
        .route("/", get(landing))
        .route("/blog", get(blog))
        .route("/blog/:slug", get(blog_post))
        .route("/cv", get(cv))
        .route("/static/*path", get(static_handler));

    // Use environment variables for deployment flexibility
    let port = std::env::var("PORT").unwrap_or_else(|_| "3000".to_string());
    let port: u16 = port.parse().unwrap_or(3000);

    // For deployment, bind to all interfaces
    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    println!("Listening on http://{}", addr);

    let listener = TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
