from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ClusteringMethod(str, Enum):
    KMEANS = "kmeans"
    DBSCAN = "dbscan"
    HIERARCHICAL = "hierarchical"


class EmbeddingModel(str, Enum):
    MINILM = "all-MiniLM-L6-v2"
    OPENAI = "openai"
    MPNET = "all-mpnet-base-v2"


class ReadingListEntry(BaseModel):
    title: str
    url: HttpUrl
    date_added: datetime
    content: Optional[str] = None
    content_length: Optional[int] = None


class ScrapingOptions(BaseModel):
    max_content_length: int = 5000
    include_metadata: bool = True
    timeout: int = 10
    delay: float = 1.0


class EmbeddingOptions(BaseModel):
    model: EmbeddingModel = EmbeddingModel.MINILM
    batch_size: int = 32
    normalize: bool = True


class MindMapOptions(BaseModel):
    clustering_method: ClusteringMethod = ClusteringMethod.KMEANS
    n_clusters: int = 5
    visualization_type: str = "interactive"
    include_keywords: bool = True


class ScrapingRequest(BaseModel):
    urls: List[HttpUrl]
    options: Optional[ScrapingOptions] = None


class EmbeddingRequest(BaseModel):
    content: List[str]
    options: Optional[EmbeddingOptions] = None


class MindMapRequest(BaseModel):
    embeddings: List[List[float]]
    metadata: List[Dict[str, Any]]
    options: Optional[MindMapOptions] = None


class MindMapNode(BaseModel):
    id: str
    title: str
    url: str
    cluster: int
    position: Dict[str, float]
    keywords: List[str]
    content_preview: str


class MindMapEdge(BaseModel):
    source: str
    target: str
    weight: float


class MindMapCluster(BaseModel):
    id: int
    name: str
    keywords: List[str]
    articles: List[int]


class MindMapResponse(BaseModel):
    id: str
    nodes: List[MindMapNode]
    edges: List[MindMapEdge]
    clusters: List[MindMapCluster]
    metadata: Dict[str, Any]
    created_at: datetime


class ReadingListResponse(BaseModel):
    entries: List[ReadingListEntry]
    total_count: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None 