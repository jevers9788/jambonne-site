# ---- Build Stage ----
FROM rust:latest AS builder

WORKDIR /app

# Copy the entire source and build
COPY . .
RUN cargo build --release

# ---- Runtime Stage ----
FROM debian:bookworm-slim

WORKDIR /app

# Copy the binary (static assets and templates are compiled into it)
COPY --from=builder /app/target/release/jambonne-site /app/bin/jambonne-site

ENV PORT=8080

EXPOSE 8080

CMD ["/app/bin/jambonne-site"] 
