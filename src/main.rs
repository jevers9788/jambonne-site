use askama::Template;
use axum::{routing::get, Router};
use std::net::SocketAddr;
use tokio::net::TcpListener;
use tower_http::services::ServeDir;

#[derive(Template)]
#[template(path = "index.html")]
struct IndexTemplate;

#[derive(Template)]
#[template(path = "blog.html")]
struct BlogTemplate;

#[derive(Template)]
#[template(path = "cv.html")]
struct CvTemplate;

async fn landing() -> impl axum::response::IntoResponse {
    IndexTemplate
}

async fn blog() -> impl axum::response::IntoResponse {
    BlogTemplate
}

async fn cv() -> impl axum::response::IntoResponse {
    CvTemplate
}

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/", get(landing))
        .route("/blog", get(blog))
        .route("/cv", get(cv))
        .nest_service("/static", ServeDir::new("static"));

    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    println!("Listening on http://{}", addr);

    let listener = TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
