import re
from collections import Counter
from typing import List, Optional, Sequence, Set

import numpy as np
from sentence_transformers import SentenceTransformer


DEFAULT_STOP_WORDS: Set[str] = {
    "this",
    "that",
    "with",
    "have",
    "will",
    "from",
    "they",
    "been",
    "were",
    "said",
    "each",
    "which",
    "their",
    "time",
    "would",
    "there",
    "could",
    "other",
    "than",
    "first",
    "very",
    "after",
    "some",
    "what",
    "when",
    "where",
    "more",
    "most",
    "over",
    "into",
    "through",
    "during",
    "before",
    "above",
    "below",
    "between",
    "among",
    "within",
    "without",
    "against",
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "by",
    "is",
    "are",
    "was",
    "be",
    "being",
    "has",
    "had",
    "do",
    "does",
    "did",
    "should",
    "may",
    "might",
    "must",
}


class EmbeddingKeywordExtractor:
    """Generate keywords using semantic similarity between phrases and embeddings."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        stop_words: Optional[Set[str]] = None,
        max_ngram: int = 3,
        max_candidates: int = 60,
    ):
        self.model_name = model_name
        self.stop_words = stop_words or DEFAULT_STOP_WORDS
        self.max_ngram = max_ngram
        self.max_candidates = max_candidates
        self._token_pattern = re.compile(r"\b[a-zA-Z][\w-]+\b")
        self._model: Optional[SentenceTransformer] = None

    def extract_keywords(
        self,
        text: str,
        base_embedding: Optional[Sequence[float]],
        max_keywords: int = 10,
    ) -> List[str]:
        """Return keywords ranked by semantic similarity to the base embedding."""
        if not text:
            return []

        candidates = self._generate_candidates(text)
        if not candidates:
            return self._frequency_keywords(text, max_keywords)

        base_vector = self._prepare_base_embedding(base_embedding, text)
        if base_vector is None:
            return self._frequency_keywords(text, max_keywords)

        try:
            candidate_embeddings = self._encode_candidates(candidates)
        except Exception:
            return self._frequency_keywords(text, max_keywords)

        scores = candidate_embeddings @ base_vector
        ranked = [
            phrase
            for _, phrase in sorted(
                zip(scores, candidates), key=lambda pair: pair[0], reverse=True
            )
        ]

        deduped: List[str] = []
        seen: Set[str] = set()
        for phrase in ranked:
            normalized = phrase.strip()
            if not normalized or normalized in seen:
                continue
            deduped.append(normalized)
            seen.add(normalized)
            if len(deduped) >= max_keywords:
                break

        if not deduped:
            return self._frequency_keywords(text, max_keywords)

        return deduped

    def _prepare_base_embedding(
        self, base_embedding: Optional[Sequence[float]], text: str
    ) -> Optional[np.ndarray]:
        """Normalize provided embedding or derive one from the text."""
        vector: Optional[np.ndarray] = None

        if base_embedding is not None:
            vector = np.array(base_embedding, dtype=np.float32)
            norm = np.linalg.norm(vector)
            if norm == 0:
                vector = None
            else:
                vector = vector / norm

        if vector is not None:
            return vector

        try:
            self._ensure_model()
            encoded = self._model.encode(text, normalize_embeddings=True)
            return np.array(encoded, dtype=np.float32)
        except Exception:
            return None

    def _encode_candidates(self, candidates: List[str]) -> np.ndarray:
        """Embed candidates with the shared transformer model."""
        self._ensure_model()
        embeddings = self._model.encode(
            candidates, normalize_embeddings=True, convert_to_numpy=True
        )
        return np.array(embeddings, dtype=np.float32)

    def _generate_candidates(self, text: str) -> List[str]:
        """Produce candidate phrases up to the configured n-gram length."""
        tokens = self._tokenize(text)
        if not tokens:
            return []

        candidates: List[str] = []
        chunk: List[str] = []
        for token in tokens:
            if token in self.stop_words:
                if chunk:
                    candidates.extend(self._candidates_from_chunk(chunk))
                    chunk = []
                continue
            chunk.append(token)

        if chunk:
            candidates.extend(self._candidates_from_chunk(chunk))

        deduped: List[str] = []
        seen: Set[str] = set()
        for phrase in candidates:
            if phrase not in seen:
                deduped.append(phrase)
                seen.add(phrase)
            if len(deduped) >= self.max_candidates:
                break

        if not deduped:
            return []

        return deduped

    def _candidates_from_chunk(self, chunk: List[str]) -> List[str]:
        """Create n-gram candidates from a contiguous chunk of tokens."""
        results: List[str] = []
        max_size = min(len(chunk), self.max_ngram)
        for size in range(max_size, 0, -1):
            for start in range(0, len(chunk) - size + 1):
                phrase = " ".join(chunk[start : start + size])
                if len(phrase) >= 4:
                    results.append(phrase)
        return results

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text to lowercase alphanumeric words."""
        return [token.lower() for token in self._token_pattern.findall(text)]

    def _frequency_keywords(self, text: str, max_keywords: int) -> List[str]:
        """Fallback keyword extraction based on frequency."""
        tokens = [t for t in self._tokenize(text) if t not in self.stop_words]
        if not tokens:
            return []

        counts = Counter(tokens)
        return [word for word, _ in counts.most_common(max_keywords)]

    def _ensure_model(self) -> None:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
