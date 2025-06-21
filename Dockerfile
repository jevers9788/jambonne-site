# Use the official Rust image as a builder
FROM rust:1.75 as builder

# Set the working directory
WORKDIR /usr/src/app

# Copy the manifests
COPY Cargo.lock Cargo.toml ./

# Create a dummy main.rs to build dependencies
RUN mkdir src && echo "fn main() {}" > src/main.rs

# Build dependencies
RUN cargo build --release

# Remove the dummy main.rs and copy the real source code
RUN rm src/main.rs
COPY . .

# Build the application
RUN cargo build --release

# Create a new stage with a minimal image
FROM debian:bookworm-slim

# Install ca-certificates for HTTPS requests
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy the binary from builder stage
COPY --from=builder /usr/src/app/target/release/jambonne-site /usr/local/bin/jambonne-site

# Copy static files and templates
COPY --from=builder /usr/src/app/static /usr/local/bin/static
COPY --from=builder /usr/src/app/templates /usr/local/bin/templates
COPY --from=builder /usr/src/app/posts /usr/local/bin/posts

# Set the working directory
WORKDIR /usr/local/bin

# Expose port 3000
EXPOSE 3000

# Run the binary
CMD ["jambonne-site"] 