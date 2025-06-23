from fastapi import APIRouter, HTTPException, BackgroundTasks
import uuid
from datetime import datetime

from ..models import (
    ReadingListResponse, ScrapingRequest, EmbeddingRequest, MindMapRequest,
    MindMapResponse, ScrapingOptions, EmbeddingOptions, MindMapOptions
)
from ..services.safari_reader import SafariReader
from ..services.web_scraper import WebScraper
from ..services.embeddings import EmbeddingService
from ..services.clustering import ClusteringService

router = APIRouter(prefix="/api", tags=["mindmap"])

# Initialize services
safari_reader = SafariReader()
web_scraper = WebScraper()
embedding_service = EmbeddingService()
clustering_service = ClusteringService()

# In-memory storage for mind maps (in production, use a database)
mind_maps = {}


@router.get("/reading-list", response_model=ReadingListResponse)
async def get_reading_list():
    """Get Safari reading list entries."""
    try:
        entries = safari_reader.read_reading_list()
        return ReadingListResponse(
            entries=entries,
            total_count=len(entries)
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading Safari bookmarks: {str(e)}")


@router.post("/scrape-content")
async def scrape_content(request: ScrapingRequest):
    """Scrape content from a list of URLs."""
    try:
        options = request.options or ScrapingOptions()
        results = web_scraper.scrape_urls([str(url) for url in request.urls], options)
        
        return {
            "results": results,
            "total_scraped": len([r for r in results if r["success"]]),
            "total_failed": len([r for r in results if not r["success"]])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scraping content: {str(e)}")


@router.post("/generate-embeddings")
async def generate_embeddings(request: EmbeddingRequest):
    """Generate embeddings for a list of text content."""
    try:
        options = request.options or EmbeddingOptions()
        embeddings = embedding_service.generate_embeddings(request.content, options)
        
        return {
            "embeddings": embeddings,
            "model": options.model,
            "total_embeddings": len(embeddings),
            "embedding_dimension": len(embeddings[0]) if embeddings else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating embeddings: {str(e)}")


@router.post("/create-mindmap", response_model=MindMapResponse)
async def create_mindmap(request: MindMapRequest, background_tasks: BackgroundTasks):
    """Create a mind map from embeddings and metadata."""
    try:
        options = request.options or MindMapOptions()
        
        # Perform clustering
        clustering_result = clustering_service.cluster_articles(
            request.embeddings, 
            request.metadata, 
            options
        )
        
        # Generate unique ID for mind map
        mindmap_id = str(uuid.uuid4())
        
        # Create mind map response
        mindmap_response = MindMapResponse(
            id=mindmap_id,
            nodes=clustering_result["nodes"],
            edges=clustering_result["edges"],
            clusters=clustering_result["clusters"],
            metadata=clustering_result["metadata"],
            created_at=datetime.utcnow()
        )
        
        # Store mind map (in production, save to database)
        mind_maps[mindmap_id] = mindmap_response
        
        return mindmap_response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating mind map: {str(e)}")


@router.get("/mindmap/latest", response_model=MindMapResponse)
async def get_latest_mindmap():
    """Get the most recently created mind map."""
    print(f"DEBUG: mind_maps keys: {list(mind_maps.keys())}")
    print(f"DEBUG: mind_maps length: {len(mind_maps)}")
    
    if not mind_maps:
        raise HTTPException(status_code=404, detail="No mind maps found")
    
    # Get the most recent mind map (simple implementation)
    latest_id = list(mind_maps.keys())[-1]
    print(f"DEBUG: latest_id: {latest_id}")
    print(f"DEBUG: latest mind map type: {type(mind_maps[latest_id])}")
    
    return mind_maps[latest_id]


@router.get("/mindmap/{mindmap_id}", response_model=MindMapResponse)
async def get_mindmap(mindmap_id: str):
    """Get a specific mind map by ID."""
    if mindmap_id not in mind_maps:
        raise HTTPException(status_code=404, detail="Mind map not found")
    
    return mind_maps[mindmap_id]


@router.get("/models/available")
async def get_available_models():
    """Get list of available embedding models."""
    try:
        models = embedding_service.get_available_models()
        return {
            "available_models": models,
            "recommended": "all-MiniLM-L6-v2" if "all-MiniLM-L6-v2" in models else models[0] if models else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting available models: {str(e)}")


@router.post("/process-reading-list")
async def process_reading_list(background_tasks: BackgroundTasks):
    """Complete pipeline: read Safari list, scrape content, generate embeddings, create mind map."""
    try:
        # Step 1: Read Safari reading list
        entries = safari_reader.read_reading_list()
        if not entries:
            raise HTTPException(status_code=404, detail="No entries found in Safari reading list")
        
        # Step 2: Scrape content
        scraping_options = ScrapingOptions()
        scraped_entries = await web_scraper.scrape_entries(entries, scraping_options)
        
        # Filter out entries without content
        valid_entries = [entry for entry in scraped_entries if entry.content]
        if not valid_entries:
            raise HTTPException(status_code=400, detail="No content could be scraped from any URLs")
        
        # Step 3: Generate embeddings
        embedding_options = EmbeddingOptions()
        content_texts = [entry.content for entry in valid_entries]
        embeddings = embedding_service.generate_embeddings(content_texts, embedding_options)
        
        # Step 4: Create mind map
        mindmap_options = MindMapOptions()
        metadata = [
            {
                "title": entry.title,
                "url": str(entry.url),
                "content": entry.content,
                "date_added": entry.date_added.isoformat()
            }
            for entry in valid_entries
        ]
        
        clustering_result = clustering_service.cluster_articles(
            embeddings, metadata, mindmap_options
        )
        
        # Generate unique ID for mind map
        mindmap_id = str(uuid.uuid4())
        
        # Create mind map response
        mindmap_response = MindMapResponse(
            id=mindmap_id,
            nodes=clustering_result["nodes"],
            edges=clustering_result["edges"],
            clusters=clustering_result["clusters"],
            metadata=clustering_result["metadata"],
            created_at=datetime.utcnow()
        )
        
        # Store mind map
        mind_maps[mindmap_id] = mindmap_response
        print(f"DEBUG: Stored mind map with ID: {mindmap_id}")
        print(f"DEBUG: Total mind maps stored: {len(mind_maps)}")
        print(f"DEBUG: Mind map keys: {list(mind_maps.keys())}")
        
        return {
            "mindmap": mindmap_response,
            "processing_summary": {
                "total_entries": len(entries),
                "successfully_scraped": len(valid_entries),
                "failed_scrapes": len(entries) - len(valid_entries),
                "clusters_created": len(clustering_result["clusters"])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing reading list: {str(e)}")


@router.delete("/mindmap/{mindmap_id}")
async def delete_mindmap(mindmap_id: str):
    """Delete a specific mind map."""
    if mindmap_id not in mind_maps:
        raise HTTPException(status_code=404, detail="Mind map not found")
    
    del mind_maps[mindmap_id]
    return {"message": "Mind map deleted successfully"}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "safari_reader": "available",
            "web_scraper": "available",
            "embedding_service": "available",
            "clustering_service": "available"
        }
    } 