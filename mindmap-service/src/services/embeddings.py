import numpy as np
from typing import List, Optional
from sentence_transformers import SentenceTransformer
import openai
import os
from ..models import EmbeddingModel, EmbeddingOptions


class EmbeddingService:
    """Service for generating text embeddings"""
    
    def __init__(self):
        self.models = {}
        self._load_models()
    
    def _load_models(self):
        """Load embedding models"""
        try:
            # Load local models
            self.models[EmbeddingModel.MINILM] = SentenceTransformer('all-MiniLM-L6-v2')
            self.models[EmbeddingModel.MPNET] = SentenceTransformer('all-mpnet-base-v2')
        except Exception as e:
            print(f"Warning: Could not load local models: {e}")
        
        # Set up OpenAI if API key is available
        if os.getenv("OPENAI_API_KEY"):
            openai.api_key = os.getenv("OPENAI_API_KEY")
    
    def generate_embeddings(self, texts: List[str], options: EmbeddingOptions) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []
        
        if options.model == EmbeddingModel.OPENAI:
            return self._generate_openai_embeddings(texts)
        else:
            return self._generate_local_embeddings(texts, options)
    
    def _generate_local_embeddings(self, texts: List[str], options: EmbeddingOptions) -> List[List[float]]:
        """Generate embeddings using local sentence-transformers models."""
        if options.model not in self.models:
            raise ValueError(f"Model {options.model} not available")
        
        model = self.models[options.model]
        
        # Generate embeddings in batches
        embeddings = []
        for i in range(0, len(texts), options.batch_size):
            batch = texts[i:i + options.batch_size]
            batch_embeddings = model.encode(batch, convert_to_tensor=False)
            
            if options.normalize:
                # Normalize embeddings
                batch_embeddings = batch_embeddings / np.linalg.norm(batch_embeddings, axis=1, keepdims=True)
            
            embeddings.extend(batch_embeddings.tolist())
        
        return embeddings
    
    def _generate_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        if not openai.api_key:
            raise ValueError("OpenAI API key not configured")
        
        try:
            response = openai.Embedding.create(
                input=texts,
                model="text-embedding-ada-002"
            )
            
            embeddings = [data.embedding for data in response.data]
            return embeddings
            
        except Exception as e:
            raise Exception(f"OpenAI embedding generation failed: {e}")
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Compute cosine similarity between two embeddings."""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Normalize vectors
        vec1_norm = vec1 / np.linalg.norm(vec1)
        vec2_norm = vec2 / np.linalg.norm(vec2)
        
        # Compute cosine similarity
        similarity = np.dot(vec1_norm, vec2_norm)
        return float(similarity)
    
    def find_similar_articles(self, target_embedding: List[float], all_embeddings: List[List[float]], 
                            top_k: int = 5) -> List[tuple]:
        """Find the most similar articles to a target embedding."""
        similarities = []
        
        for i, embedding in enumerate(all_embeddings):
            similarity = self.compute_similarity(target_embedding, embedding)
            similarities.append((i, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def get_available_models(self) -> List[str]:
        """Get list of available embedding models."""
        available = []
        
        # Check local models
        for model_name in [EmbeddingModel.MINILM, EmbeddingModel.MPNET]:
            if model_name in self.models:
                available.append(model_name)
        
        # Check OpenAI
        if os.getenv("OPENAI_API_KEY"):
            available.append(EmbeddingModel.OPENAI)
        
        return available 