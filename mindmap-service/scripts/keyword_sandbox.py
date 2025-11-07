import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from services.keyword_extraction import EmbeddingKeywordExtractor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Quickly rerank keywords using embedding-based extractor."
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("static/data/mindmap.json"),
        help="Path to mind map JSON fixture.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="all-MiniLM-L6-v2",
        help="SentenceTransformer model name.",
    )
    parser.add_argument(
        "--max-ngram", type=int, default=3, help="Maximum n-gram length."
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=60,
        help="Maximum candidate phrases per document.",
    )
    parser.add_argument(
        "--top-k", type=int, default=5, help="Number of keywords to display."
    )
    parser.add_argument(
        "--ner-model",
        type=str,
        default="en_core_web_sm",
        help="spaCy model to use for NER candidates.",
    )
    parser.add_argument(
        "--disable-ner",
        action="store_true",
        help="Disable NER-based candidate generation.",
    )
    parser.add_argument(
        "--clusters",
        action="store_true",
        help="Also recompute cluster keywords if present.",
    )
    return parser.parse_args()


def load_fixture(path: Path) -> Dict[str, Any]:
    with path.open() as f:
        return json.load(f)


def display_keywords(
    title: str,
    old: Sequence[str],
    semantic: Sequence[str],
    fallback: Sequence[str],
) -> None:
    print(f"\n{title}")
    print(f"  Old: {', '.join(old) if old else '-'}")
    if semantic:
        print(f"  Semantic: {', '.join(semantic)}")
    if fallback:
        print(f"  Fallback: {', '.join(fallback)}")
    if not semantic and not fallback:
        print("  Semantic/Fallback: -")


def recompute_article_keywords(
    data: Dict[str, Any], extractor: EmbeddingKeywordExtractor, top_k: int
) -> None:
    nodes: List[Dict[str, Any]] = data.get("nodes", [])
    embeddings = data.get("embeddings") or []

    for idx, node in enumerate(nodes):
        content = node.get("content_preview") or node.get("content", "")
        embedding = None
        if embeddings and idx < len(embeddings):
            embedding = np.array(embeddings[idx], dtype=np.float32)
        result = extractor.extract_keywords(content, embedding, max_keywords=top_k)
        display_keywords(
            f"Article {idx}: {node.get('title', 'Untitled')}",
            node.get("keywords", []),
            result["semantic"],
            result["fallback"],
        )


def recompute_cluster_keywords(
    data: Dict[str, Any], extractor: EmbeddingKeywordExtractor, top_k: int
) -> None:
    clusters: List[Dict[str, Any]] = data.get("clusters", [])
    nodes: List[Dict[str, Any]] = data.get("nodes", [])
    embeddings = data.get("embeddings") or []

    for cluster in clusters:
        article_indices = cluster.get("articles", [])
        texts = []
        vectors = []
        for idx in article_indices:
            if idx < len(nodes):
                texts.append(nodes[idx].get("content_preview") or "")
            if embeddings and idx < len(embeddings):
                vectors.append(embeddings[idx])
        centroid = None
        if vectors:
            centroid = np.mean(np.array(vectors, dtype=np.float32), axis=0)
        concatenated = " ".join(texts)
        result = extractor.extract_keywords(concatenated, centroid, max_keywords=top_k)
        display_keywords(
            f"Cluster {cluster.get('id')}",
            cluster.get("keywords", []),
            result["semantic"],
            result["fallback"],
        )


def main() -> None:
    args = parse_args()
    data = load_fixture(args.fixture)
    extractor = EmbeddingKeywordExtractor(
        model_name=args.model,
        max_ngram=args.max_ngram,
        max_candidates=args.max_candidates,
        enable_ner=not args.disable_ner,
        ner_model=args.ner_model,
    )

    print("=== Article Keywords ===")
    recompute_article_keywords(data, extractor, args.top_k)

    if args.clusters:
        print("\n=== Cluster Keywords ===")
        recompute_cluster_keywords(data, extractor, args.top_k)


if __name__ == "__main__":
    main()
