from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

from .api.routes import router

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Mind Map Service",
    description="AI-powered mind map generation service for Safari reading lists",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Mind Map Service API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health"
    }

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or default to 8000
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    ) 