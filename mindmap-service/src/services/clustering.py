import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any 
import re
from collections import Counter
from ..models import ClusteringMethod, MindMapOptions


class ClusteringService:
    """Service for clustering articles based on embeddings"""
    
    def __init__(self):
        self.stop_words = {
            'this', 'that', 'with', 'have', 'will', 'from', 'they', 'been', 
            'were', 'said', 'each', 'which', 'their', 'time', 'would', 
            'there', 'could', 'other', 'than', 'first', 'very', 'after',
            'some', 'what', 'when', 'where', 'more', 'most', 'over',
            'into', 'through', 'during', 'before', 'after', 'above',
            'below', 'between', 'among', 'within', 'without', 'against',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'must'
        }
    
    def cluster_articles(self, embeddings: List[List[float]], metadata: List[Dict[str, Any]], 
                        options: MindMapOptions) -> Dict[str, Any]:
        """Cluster articles based on embeddings and return cluster information."""
        if not embeddings or len(embeddings) < 2:
            return self._create_single_cluster_result(embeddings, metadata)
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings)
        
        # Determine optimal number of clusters if using KMeans
        if options.clustering_method == ClusteringMethod.KMEANS:
            n_clusters = min(options.n_clusters, len(embeddings) - 1, 10)
            if n_clusters < 2:
                return self._create_single_cluster_result(embeddings, metadata)
        else:
            n_clusters = options.n_clusters
        
        # Perform clustering
        if options.clustering_method == ClusteringMethod.KMEANS:
            cluster_labels = self._kmeans_clustering(embeddings_array, n_clusters)
        elif options.clustering_method == ClusteringMethod.DBSCAN:
            cluster_labels = self._dbscan_clustering(embeddings_array)
        else:
            cluster_labels = self._kmeans_clustering(embeddings_array, n_clusters)
        
        # Generate 2D positions for visualization
        positions = self._generate_2d_positions(embeddings_array)
        
        # Extract keywords for each cluster
        cluster_keywords = self._extract_cluster_keywords(cluster_labels, metadata)
        
        # Create cluster information
        clusters = []
        for cluster_id in set(cluster_labels):
            if cluster_id == -1:  # Noise points from DBSCAN
                continue
                
            cluster_articles = [i for i, label in enumerate(cluster_labels) if label == cluster_id]
            cluster_name = self._generate_cluster_name(cluster_keywords.get(cluster_id, []))
            
            clusters.append({
                "id": int(cluster_id),
                "name": cluster_name,
                "keywords": cluster_keywords.get(cluster_id, []),
                "articles": cluster_articles,
                "size": len(cluster_articles)
            })
        
        # Create nodes for mind map
        nodes = []
        for i, (embedding, meta, label, pos) in enumerate(zip(embeddings, metadata, cluster_labels, positions)):
            if label == -1:  # Handle noise points
                label = len(clusters)  # Assign to a new cluster
            
            keywords = self._extract_article_keywords(meta.get('content', ''))
            
            nodes.append({
                "id": f"node_{i}",
                "title": meta.get('title', f'Article {i}'),
                "url": meta.get('url', ''),
                "cluster": int(label),
                "position": {"x": float(pos[0]), "y": float(pos[1])},
                "keywords": keywords[:5],  # Top 5 keywords
                "content_preview": meta.get('content', '')[:200] + "..." if meta.get('content') else ""
            })
        
        # Create edges based on similarity
        edges = self._create_similarity_edges(embeddings_array, threshold=0.7)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "clusters": clusters,
            "metadata": {
                "clustering_method": options.clustering_method,
                "n_clusters": len(clusters),
                "total_articles": len(embeddings)
            }
        }
    
    def _kmeans_clustering(self, embeddings: np.ndarray, n_clusters: int) -> np.ndarray:
        """Perform K-means clustering."""
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        return kmeans.fit_predict(embeddings)
    
    def _dbscan_clustering(self, embeddings: np.ndarray) -> np.ndarray:
        """Perform DBSCAN clustering."""
        # Compute pairwise distances for DBSCAN
        similarities = cosine_similarity(embeddings)
        distances = 1 - similarities
        
        # Use median distance as eps parameter
        eps = np.median(distances[distances > 0])
        dbscan = DBSCAN(eps=eps, min_samples=2, metric='precomputed')
        return dbscan.fit_predict(distances)
    
    def _generate_2d_positions(self, embeddings: np.ndarray) -> np.ndarray:
        """Generate 2D positions for visualization using t-SNE."""
        if len(embeddings) < 2:
            return np.array([[0, 0]])
        
        # Use PCA first for dimensionality reduction if needed
        # Adjust n_components based on dataset size
        max_components = min(50, embeddings.shape[1], len(embeddings) - 1)
        if max_components < 2:
            # If we can't do PCA, use the original embeddings
            embeddings_reduced = embeddings
        else:
            pca = PCA(n_components=max_components)
            embeddings_reduced = pca.fit_transform(embeddings)
        
        # Use t-SNE for 2D visualization
        # Adjust perplexity based on dataset size
        perplexity = min(30, len(embeddings) - 1)
        if perplexity < 1:
            perplexity = 1
        
        tsne = TSNE(n_components=2, random_state=42, perplexity=perplexity)
        positions = tsne.fit_transform(embeddings_reduced)
        
        return positions
    
    def _extract_cluster_keywords(self, cluster_labels: np.ndarray, metadata: List[Dict[str, Any]]) -> Dict[int, List[str]]:
        """Extract common keywords for each cluster."""
        cluster_keywords = {}
        
        for cluster_id in set(cluster_labels):
            if cluster_id == -1:  # Skip noise points
                continue
                
            # Get all content for this cluster
            cluster_content = []
            for i, label in enumerate(cluster_labels):
                if label == cluster_id:
                    content = metadata[i].get('content', '')
                    if content:
                        cluster_content.append(content)
            
            if cluster_content:
                # Extract keywords from all content in cluster
                all_text = ' '.join(cluster_content)
                keywords = self._extract_keywords(all_text, max_keywords=10)
                cluster_keywords[cluster_id] = keywords
        
        return cluster_keywords
    
    def _extract_article_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """Extract keywords from a single article."""
        return self._extract_keywords(text, max_keywords)
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract common keywords from text."""
        if not text:
            return []
        
        # Simple keyword extraction
        words = re.findall(r'\b\w{4,}\b', text.lower())
        
        # Remove stop words
        words = [word for word in words if word not in self.stop_words]
        
        # Count frequency
        word_count = Counter(words)
        
        # Return most common words
        return [word for word, count in word_count.most_common(max_keywords)]
    
    def _generate_cluster_name(self, keywords: List[str]) -> str:
        """Generate a name for a cluster based on its keywords."""
        if not keywords:
            return "General"
        
        # Use the most common keyword as cluster name
        return keywords[0].title() if keywords else "General"
    
    def _create_similarity_edges(self, embeddings: np.ndarray, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Create edges between similar articles."""
        edges = []
        n_articles = len(embeddings)
        
        for i in range(n_articles):
            for j in range(i + 1, n_articles):
                similarity = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
                
                if similarity > threshold:
                    edges.append({
                        "source": f"node_{i}",
                        "target": f"node_{j}",
                        "weight": float(similarity)
                    })
        
        return edges
    
    def _create_single_cluster_result(self, embeddings: List[List[float]], metadata: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create result for single cluster (when not enough data for clustering)."""
        nodes = []
        for i, (embedding, meta) in enumerate(zip(embeddings, metadata)):
            keywords = self._extract_article_keywords(meta.get('content', ''))
            nodes.append({
                "id": f"node_{i}",
                "title": meta.get('title', f'Article {i}'),
                "url": meta.get('url', ''),
                "cluster": 0,
                "position": {"x": 0.0, "y": 0.0},
                "keywords": keywords[:5],
                "content_preview": meta.get('content', '')[:200] + "..." if meta.get('content') else ""
            })
        
        return {
            "nodes": nodes,
            "edges": [],
            "clusters": [{
                "id": 0,
                "name": "All Articles",
                "keywords": [],
                "articles": list(range(len(embeddings))),
                "size": len(embeddings)
            }],
            "metadata": {
                "clustering_method": "single_cluster",
                "n_clusters": 1,
                "total_articles": len(embeddings)
            }
        } 