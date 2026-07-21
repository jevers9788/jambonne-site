use askama::Template;
use askama_axum::IntoResponse;
use axum::extract::Path;
use axum::response::Response;
use axum::{routing::get, Router};
use include_dir::{include_dir, Dir};
use std::net::SocketAddr;
use tokio::net::TcpListener;

// Embed static files directly into the binary
static STATIC_DIR: Dir<'_> = include_dir!("static");

#[derive(Template)]
#[template(path = "index.html")]
struct IndexTemplate;

async fn landing() -> impl axum::response::IntoResponse {
    IndexTemplate
}

fn build_router() -> Router {
    Router::new()
        .route("/", get(landing))
        .route(
            "/about",
            get(|| async { axum::response::Redirect::permanent("/") }),
        )
        .route(
            "/robots.txt",
            get(|| async {
                (
                    [("content-type", "text/plain")],
                    include_str!("../static/robots.txt"),
                )
            }),
        )
        .route(
            "/sitemap.xml",
            get(|| async {
                (
                    [("content-type", "application/xml")],
                    include_str!("../static/sitemap.xml"),
                )
            }),
        )
        .route("/static/*path", get(static_handler))
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
    println!("Starting jambonne-site...");

    let app = build_router();

    let port = std::env::var("PORT").unwrap_or_else(|_| "3000".to_string());
    let port: u16 = port.parse().unwrap_or(3000);

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    let listener = match TcpListener::bind(addr).await {
        Ok(listener) => {
            println!("Listening on {}", addr);
            listener
        }
        Err(e) => {
            eprintln!("Failed to bind to {}: {}", addr, e);
            std::process::exit(1);
        }
    };

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
}
