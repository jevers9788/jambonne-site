# ---- Build Stage ----
FROM rust:1.76 as builder

WORKDIR /app

# Copy manifests first for caching
COPY Cargo.toml Cargo.lock ./
RUN mkdir src
RUN echo "fn main() {}" > src/main.rs
RUN cargo build --release || true

# Now copy the rest of the source
COPY . .
RUN cargo build --release

# ---- Runtime Stage ----
FROM debian:bookworm-slim

WORKDIR /app

# Install CA certificates for HTTPS
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy the binary
COPY --from=builder /app/target/release/jambonne-site /app/bin/jambonne-site

# Copy static assets, posts, and templates
COPY --from=builder /app/static /app/static
COPY --from=builder /app/posts /app/posts
COPY --from=builder /app/templates /app/templates

EXPOSE 8080

CMD ["/app/bin/jambonne-site"] 