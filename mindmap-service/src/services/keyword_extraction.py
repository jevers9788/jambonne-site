import re
from collections import Counter
from typing import Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer
try:
    import spacy
    from spacy.language import Language
    from spacy.tokens import Doc
except ImportError:  # pragma: no cover
    spacy = None
    Language = None
    Doc = None


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

DEFAULT_NER_LABELS: Set[str] = {
    "PERSON",
    "ORG",
    "GPE",
    "LOC",
    "NORP",
    "PRODUCT",
    "EVENT",
    "WORK_OF_ART",
    "LAW",
}


class EmbeddingKeywordExtractor:
    """Generate keywords using semantic similarity between phrases and embeddings."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        stop_words: Optional[Set[str]] = None,
        max_ngram: int = 3,
        max_candidates: int = 60,
        enable_ner: bool = True,
        ner_model: str = "en_core_web_sm",
        ner_labels: Optional[Set[str]] = None,
    ):
        self.model_name = model_name
        self.stop_words = stop_words or DEFAULT_STOP_WORDS
        self.max_ngram = max_ngram
        self.max_candidates = max_candidates
        self.enable_ner = enable_ner and spacy is not None
        self.ner_model = ner_model
        self.ner_labels = ner_labels or DEFAULT_NER_LABELS
        self._token_pattern = re.compile(r"\b[a-zA-Z][\w-]+\b")
        self._model: Optional[SentenceTransformer] = None
        self._nlp: Optional["Language"] = None

    def extract_keywords(
        self,
        text: str,
        base_embedding: Optional[Sequence[float]],
        max_keywords: int = 10,
    ) -> Dict[str, List[str]]:
        """Return keywords separated into embedding-ranked and fallback categories."""
        if not text:
            return {"semantic": [], "fallback": []}

        doc = self._get_doc(text)
        candidates = self._generate_candidates(text, doc)
        if not candidates:
            fallback = self._frequency_keywords(text, max_keywords)
            return {"semantic": [], "fallback": fallback}

        base_vector = self._prepare_base_embedding(base_embedding, text)
        if base_vector is None:
            fallback = self._frequency_keywords(text, max_keywords)
            return {"semantic": [], "fallback": fallback}

        try:
            candidate_embeddings = self._encode_candidates(candidates)
        except Exception:
            fallback = self._frequency_keywords(text, max_keywords)
            return {"semantic": [], "fallback": fallback}

        scores = candidate_embeddings @ base_vector
        ranked = [
            (phrase, score)
            for phrase, score in sorted(
                zip(candidates, scores), key=lambda pair: pair[1], reverse=True
            )
        ]

        semantic: List[str] = []
        seen: Set[str] = set()
        seen_tokens: List[Tuple[str, ...]] = []
        for phrase, _ in ranked:
            normalized = phrase.strip()
            if not normalized or normalized in seen:
                continue
            token_key = self._phrase_token_signature(normalized)
            if self._is_redundant(token_key, seen_tokens):
                continue
            semantic.append(normalized)
            seen.add(normalized)
            seen_tokens.append(token_key)
            if len(semantic) >= max_keywords:
                break

        if semantic:
            return {"semantic": semantic, "fallback": []}

        fallback = self._frequency_keywords(text, max_keywords)
        return {"semantic": [], "fallback": fallback}

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

    def _generate_candidates(self, text: str, doc: Optional["Doc"]) -> List[str]:
        """Produce candidate phrases up to the configured n-gram length."""
        if doc is not None:
            token_stream = self._tokens_from_doc(doc)
        else:
            token_stream = self._tokenize(text)

        if not token_stream:
            return []

        if doc is not None:
            candidates = self._candidates_from_doc(doc, token_stream)
        else:
            candidates = self._candidates_from_tokens(token_stream)

        deduped: List[str] = []
        seen: Set[str] = set()

        for phrase in candidates:
            normalized = self._clean_phrase(phrase)
            if not normalized or normalized in seen:
                continue
            deduped.append(normalized)
            seen.add(normalized)
            if len(deduped) >= self.max_candidates:
                break

        return deduped

    def _candidates_from_doc(self, doc: "Doc", token_stream: List[str]) -> List[str]:
        """Use spaCy noun chunks, entities, and fallback n-grams."""
        candidates: List[str] = []

        # Noun chunks capture many multiword subjects
        if getattr(doc, "is_parsed", False):
            for chunk in doc.noun_chunks:
                text = self._clean_phrase(chunk.text)
                if self._valid_candidate(text):
                    candidates.append(text)

        # Entities provide high-value proper nouns
        for ent in doc.ents:
            if ent.label_ in self.ner_labels:
                text = self._clean_phrase(ent.text)
                if self._valid_candidate(text):
                    candidates.append(text)

        # Fallback n-gram extraction that respects punctuation via doc tokens
        chunk: List[str] = []
        for token in doc:
            if token.is_punct or token.is_space or token.lower_ in self.stop_words:
                if chunk:
                    candidates.extend(self._candidates_from_chunk(chunk))
                    chunk = []
                continue
            chunk.append(token.text.lower())

        if chunk:
            candidates.extend(self._candidates_from_chunk(chunk))

        return candidates or self._candidates_from_tokens(token_stream)

    def _candidates_from_tokens(self, tokens: List[str]) -> List[str]:
        """Fallback candidate generation using pre-tokenized text."""
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

        return candidates

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

    def _ensure_nlp(self) -> Optional["Language"]:
        if not self.enable_ner or spacy is None:
            return None
        if self._nlp is not None:
            return self._nlp
        try:
            self._nlp = spacy.load(self.ner_model)
        except Exception:
            self._nlp = None
        return self._nlp

    def _get_doc(self, text: str) -> Optional["Doc"]:
        nlp = self._ensure_nlp()
        if not nlp:
            return None
        try:
            return nlp(text)
        except Exception:
            return None

    def _tokens_from_doc(self, doc: "Doc") -> List[str]:
        tokens = [
            token.text.lower()
            for token in doc
            if not token.is_space and not token.is_punct
        ]
        return tokens

    def _clean_phrase(self, phrase: str) -> str:
        normalized = " ".join(phrase.split())
        return normalized.strip(" -_,.;:!?\"'()[]{}")

    def _valid_candidate(self, phrase: str) -> bool:
        if not phrase or len(phrase) < 4:
            return False
        tokens = [tok for tok in phrase.lower().split() if tok]
        if not tokens:
            return False
        # Reject phrases that are entirely stop words
        if all(tok in self.stop_words for tok in tokens):
            return False
        return True

    def _phrase_token_signature(self, phrase: str) -> Tuple[str, ...]:
        return tuple(token for token in phrase.lower().split() if token)

    def _is_redundant(
        self, candidate_tokens: Tuple[str, ...], existing: List[Tuple[str, ...]]
    ) -> bool:
        if not candidate_tokens:
            return True
        candidate_set = set(candidate_tokens)
        for tokens in existing:
            other_set = set(tokens)
            overlap = len(candidate_set & other_set)
            base = min(len(candidate_set), len(other_set))
            if base > 0 and overlap / base >= 0.7:
                return True
        return False
