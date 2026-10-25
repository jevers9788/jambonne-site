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

struct Post {
    slug: &'static str,
    title: &'static str,
    markdown: &'static str,
}

static POSTS: &[Post] = &[
    Post {
        slug: "ai-compiler",
        title: "How Low Can You Go: LLMs as Kernel Compilers",
        markdown: include_str!("../blog/ai-compiler.md"),
    },
    Post {
        slug: "dumpster-cluster",
        title: "Out But Not Down: the V100 Lives Again",
        markdown: include_str!("../blog/dumpster-cluster.md"),
    },
    Post {
        slug: "deep-infer",
        title: "Notes on DeepInfer",
        markdown: include_str!("../blog/deep-infer.md")
    },
];

#[derive(Template)]
#[template(path = "blog.html")]
struct BlogTemplate {
    posts: &'static [Post],
}

#[derive(Template)]
#[template(path = "post.html")]
struct PostTemplate {
    title: &'static str,
    slug: &'static str,
    posts: &'static [Post],
    html: String,
}

async fn blog() -> impl axum::response::IntoResponse {
    BlogTemplate { posts: POSTS }
}

#[derive(serde::Deserialize)]
struct ReadingItem {
    title: String,
    url: String,
}

#[derive(Template)]
#[template(path = "reading.html")]
struct ReadingTemplate {
    items: Vec<ReadingItem>,
}

fn parse_reading_list(data: &str) -> Result<Vec<ReadingItem>, serde_json::Error> {
    let mut items: Vec<ReadingItem> = serde_json::from_str(data)?;
    items.retain(|item| {
        item.url.parse::<axum::http::Uri>().is_ok_and(|uri| {
            matches!(uri.scheme_str(), Some("http" | "https")) && uri.host().is_some()
        })
    });
    Ok(items)
}

async fn reading() -> Response {
    match parse_reading_list(include_str!("../static/data/reading_list.json")) {
        Ok(items) => ReadingTemplate { items }.into_response(),
        Err(error) => {
            eprintln!("Failed to load reading list: {error}");
            axum::http::StatusCode::INTERNAL_SERVER_ERROR.into_response()
        }
    }
}

async fn post(Path(slug): Path<String>) -> Response {
    let Some(post) = POSTS.iter().find(|post| post.slug == slug) else {
        return axum::http::StatusCode::NOT_FOUND.into_response();
    };
    let mut html = String::new();
    // The template owns the title and byline; omit the Markdown title.
    let markdown = post
        .markdown
        .strip_prefix("# ")
        .and_then(|text| text.split_once('\n'))
        .map_or(post.markdown, |(_, body)| body);
    // Only repository-authored Markdown is rendered as trusted HTML.
    pulldown_cmark::html::push_html(
        &mut html,
        pulldown_cmark::Parser::new_ext(markdown, pulldown_cmark::Options::ENABLE_TABLES),
    );
    PostTemplate {
        title: post.title,
        slug: post.slug,
        posts: POSTS,
        html,
    }
    .into_response()
}

// 301 www.<host> -> <host> so Google sees a single canonical hostname
async fn redirect_www(req: axum::extract::Request, next: axum::middleware::Next) -> Response {
    let host = req
        .headers()
        .get(axum::http::header::HOST)
        .and_then(|h| h.to_str().ok());
    if let Some(bare) = host.and_then(|h| h.strip_prefix("www.")) {
        let path = req
            .uri()
            .path_and_query()
            .map(|p| p.as_str())
            .unwrap_or("/");
        let location = format!("https://{}{}", bare, path);
        return axum::response::Redirect::permanent(&location).into_response();
    }
    next.run(req).await
}

fn build_router() -> Router {
    Router::new()
        .route("/", get(landing))
        .route("/blog", get(blog))
        .route("/reading", get(reading))
        .route("/blog/:slug", get(post))
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
        .layer(axum::middleware::from_fn(redirect_www))
}

// Custom static file handler that serves from embedded files
async fn static_handler(Path(path): Path<String>) -> Response {
    if let Some(file) = STATIC_DIR.get_file(&path) {
        let content_type = match path.split('.').next_back() {
            Some("css") => "text/css",
            Some("js") => "application/javascript",
            Some("png") => "image/png",
            Some("webp") => "image/webp",
            Some("jpg") | Some("jpeg") => "image/jpeg",
            Some("svg") => "image/svg+xml",
            Some("woff") => "font/woff",
            Some("woff2") => "font/woff2",
            Some("ttf") => "font/ttf",
            Some("pdf") => "application/pdf",
            _ => "text/plain",
        };
        let cache_control = if path.starts_with("v1/") {
            "public, max-age=31536000, immutable"
        } else {
            "public, max-age=3600"
        };
        let headers = [
            ("content-type", content_type),
            ("cache-control", cache_control),
        ];
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

    #[test]
    fn reading_list_validates_links_and_escapes_titles() {
        let items = parse_reading_list(
            r#"[
            {"title":"<script>alert(1)</script>","url":"https://example.com/"},
            {"title":"unsafe","url":"javascript:alert(1)"},
            {"title":"relative","url":"/private"}
        ]"#,
        )
        .unwrap();
        assert_eq!(items.len(), 1);
        let html = ReadingTemplate { items }.render().unwrap();
        assert!(html.contains("&lt;script&gt;"));
        assert!(!html.contains("javascript:"));
        assert!(parse_reading_list("invalid json").is_err());
        let saved = parse_reading_list(include_str!("../static/data/reading_list.json")).unwrap();
        assert!(!saved.is_empty());
        assert!(ReadingTemplate { items: vec![] }
            .render()
            .unwrap()
            .contains("No reading links yet."));
    }

    #[tokio::test]
    async fn blog_pages_render_and_unknown_posts_return_404() {
        for (path, expected) in [
            ("/", "href=\"/blog\""),
            ("/blog", "href=\"/blog/ai-compiler\""),
            ("/reading", "Weatherizing Salem"),
            (
                "/blog/ai-compiler",
                "<h1>How Low Can You Go: LLMs as Kernel Compilers</h1>",
            ),
            (
                "/blog/dumpster-cluster",
                "<h1>Out But Not Down: the V100 Lives Again</h1>",
            ),
        ] {
            let response = build_router()
                .oneshot(Request::builder().uri(path).body(Body::empty()).unwrap())
                .await
                .unwrap();
            assert_eq!(response.status(), axum::http::StatusCode::OK);
            let body = axum::body::to_bytes(response.into_body(), usize::MAX)
                .await
                .unwrap();
            let body = std::str::from_utf8(&body).unwrap();
            assert!(body.contains(expected), "{path}");
            if path == "/" {
                assert!(body.contains("href=\"/reading\""));
            }
            assert_eq!(body.contains("as=\"image\""), path == "/");
            if path.starts_with("/blog/") {
                assert_eq!(body.matches("class=\"post-header\"").count(), 1);
                assert!(!body.contains("<h1>Dumpster Cluster</h1>"));
                assert!(body.contains("<p class=\"byline\">James Walsh Evers</p>"));
            }
            if path == "/blog/ai-compiler" {
                assert!(body.contains("href=\"/blog/dumpster-cluster\""));
                assert!(!body.contains("href=\"/blog/ai-compiler\""));
                assert!(body.contains("class=\"banana-home\" href=\"/\""));
                assert!(body.contains("<table>"));
                assert!(body.contains(">0.271 ms</td>"));
                assert!(body.contains("href=\"https://arxiv.org/pdf/2609.36800\""));
                assert_eq!(body.matches("<h1>").count(), 1);
            }
        }
        let response = build_router()
            .oneshot(
                Request::builder()
                    .uri("/blog/missing")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(response.status(), axum::http::StatusCode::NOT_FOUND);
    }

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

    #[tokio::test]
    async fn static_assets_have_correct_types_and_cache_policies() {
        for (path, content_type, cache_control) in [
            (
                "v1/style.css",
                "text/css",
                "public, max-age=31536000, immutable",
            ),
            (
                "v1/v2_blueprint.webp",
                "image/webp",
                "public, max-age=31536000, immutable",
            ),
            (
                "v1/eb-garamond-latin-400.woff2",
                "font/woff2",
                "public, max-age=31536000, immutable",
            ),
            ("robots.txt", "text/plain", "public, max-age=3600"),
        ] {
            let response = build_router()
                .oneshot(
                    Request::builder()
                        .uri(format!("/static/{path}"))
                        .body(Body::empty())
                        .unwrap(),
                )
                .await
                .unwrap();
            assert_eq!(response.status(), axum::http::StatusCode::OK, "{path}");
            assert_eq!(response.headers()["content-type"], content_type, "{path}");
            assert_eq!(response.headers()["cache-control"], cache_control, "{path}");
            let body = axum::body::to_bytes(response.into_body(), usize::MAX)
                .await
                .unwrap();
            assert!(!body.is_empty(), "{path}");
        }
        let response = build_router()
            .oneshot(
                Request::builder()
                    .uri("/static/v1/missing.webp")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(response.status(), axum::http::StatusCode::NOT_FOUND);
        assert!(!response.headers().contains_key("cache-control"));
    }

    #[tokio::test]
    async fn www_host_redirects_to_bare_domain() {
        let app = build_router();
        let response = app
            .oneshot(
                Request::builder()
                    .uri("/about")
                    .header("host", "www.jambon.net")
                    .body(Body::empty())
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(
            response.status(),
            axum::http::StatusCode::PERMANENT_REDIRECT
        );
        assert_eq!(response.headers()["location"], "https://jambon.net/about");
    }
}
