"""Corpus embeddings for B3 (CPU; FastEmbed ONNX when available)."""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from evaluation.bm25 import tokenize

logger = logging.getLogger(__name__)

EMBED_DIM = 384
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
BackendKind = Literal["fastembed", "hashing"]


def doc_text(row: pd.Series) -> str:
    return f"{row.get('PartName', '')} {row.get('Discrepancy', '')}".strip()


def _hash_embed(text: str, dim: int = EMBED_DIM) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    for token in tokenize(text):
        digest = hashlib.md5(token.encode()).hexdigest()
        h = int(digest[:8], 16)
        idx = h % dim
        sign = -1.0 if h & 1 else 1.0
        vec[idx] += sign
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec /= norm
    return vec


def _cosine_matrix(query: np.ndarray, docs: np.ndarray) -> np.ndarray:
    if docs.size == 0:
        return np.array([], dtype=np.float32)
    q = query.astype(np.float32)
    qn = np.linalg.norm(q)
    if qn == 0:
        return np.zeros(len(docs), dtype=np.float32)
    q = q / qn
    norms = np.linalg.norm(docs, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-9)
    return (docs / norms) @ q


class EmbeddingBackend:
    def __init__(self, kind: BackendKind = "fastembed", model_name: str = DEFAULT_MODEL) -> None:
        self.kind = kind
        self.model_name = model_name
        self._model = None

    def _lazy_fastembed(self):
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, EMBED_DIM), dtype=np.float32)
        if self.kind == "hashing":
            return np.stack([_hash_embed(t) for t in texts], axis=0)
        model = self._lazy_fastembed()
        out = list(model.embed(texts, batch_size=128))
        return np.asarray(out, dtype=np.float32)

    def encode_query(self, text: str) -> np.ndarray:
        return self.encode([text])[0]


def corpus_cache_meta(corpus: pd.DataFrame, backend: EmbeddingBackend) -> dict:
    return {
        "rows": int(len(corpus)),
        "backend": backend.kind,
        "model": backend.model_name,
        "first_id": str(corpus.iloc[0]["OperatorControlNumber"]) if len(corpus) else "",
        "last_id": str(corpus.iloc[-1]["OperatorControlNumber"]) if len(corpus) else "",
    }


def load_or_build_corpus_matrix(
    corpus: pd.DataFrame,
    cache_dir: Path,
    backend: EmbeddingBackend,
    *,
    force: bool = False,
) -> np.ndarray:
    """Row-aligned embedding matrix for ``corpus`` (same order as caller's frame)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_slug = backend.model_name.replace("/", "_")
    vec_path = cache_dir / f"embeddings_{backend.kind}_{model_slug}.npy"
    meta_path = cache_dir / f"embeddings_{backend.kind}_{model_slug}.meta.json"
    meta = corpus_cache_meta(corpus, backend)

    if not force and vec_path.is_file() and meta_path.is_file():
        try:
            saved = json.loads(meta_path.read_text(encoding="utf-8"))
            if saved == meta:
                matrix = np.load(vec_path)
                if matrix.shape[0] == len(corpus):
                    logger.info("Loaded embedding cache %s", vec_path)
                    return matrix
        except Exception as exc:
            logger.warning("Embedding cache invalid (%s), rebuilding", exc)

    texts = [doc_text(row) for _, row in corpus.iterrows()]
    logger.info("Encoding %d documents (%s)", len(texts), backend.kind)
    matrix = backend.encode(texts)
    np.save(vec_path, matrix)
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info("Wrote embedding cache %s", vec_path)
    return matrix


def cosine_scores_for_visible(
    corpus_vectors: np.ndarray,
    corpus: pd.DataFrame,
    visible: pd.DataFrame,
    query_text: str,
    backend: EmbeddingBackend,
) -> np.ndarray:
    """Cosine similarity between query and each row in ``visible`` (by corpus row index)."""
    if visible.empty:
        return np.array([], dtype=np.float32)
    positions = visible.index.to_numpy()
    query_vec = backend.encode_query(query_text)
    doc_vectors = corpus_vectors[positions]
    return _cosine_matrix(query_vec, doc_vectors)