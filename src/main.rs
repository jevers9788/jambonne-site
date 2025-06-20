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

// mod filters {
// pub fn safe(s: &str) -> ::askama::Result<String> {
// Ok(s.to_owned())
// }
// }

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
    if let Ok(entries) = fs::read_dir("posts") {
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
    }
    posts.sort_by(|a, b| b.slug.cmp(&a.slug));
    BlogTemplate { posts }
}

async fn blog_post(Path(slug): Path<String>) -> Response {
    let path = format!("posts/{}.md", slug);
    if !FsPath::new(&path).exists() {
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

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/", get(landing))
        .route("/blog", get(blog))
        .route("/blog/:slug", get(blog_post))
        .route("/cv", get(cv))
        .nest_service("/static", ServeDir::new("static"));

    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    println!("Listening on http://{}", addr);

    let listener = TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
