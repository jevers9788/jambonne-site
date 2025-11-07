# ---- Build Stage ----
FROM rust:latest AS builder

WORKDIR /app

# Copy the entire source and build
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

ENV PORT=8080

EXPOSE 8080

CMD ["/app/bin/jambonne-site"] 
