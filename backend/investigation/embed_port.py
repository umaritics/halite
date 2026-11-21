"""Optional retrieval-owned embedding adapter; absence is explicit lexical fallback."""
from importlib import import_module
import math


def embed_texts(texts):
    """V1 may expose retrieval.embeddings.embed_texts; no model/dependency is installed here."""
    try:
        module = import_module('retrieval.embeddings')
    except ModuleNotFoundError as exc:
        if exc.name not in ('retrieval', 'retrieval.embeddings'):
            raise
        return None
    embed = getattr(module, 'embed_texts', None)
    if embed is None:
        return None
    values = embed(list(texts))
    if values is None:
        return None
    values = [list(row) for row in values]
    if len(values) != len(texts) or not values or not values[0]:
        raise ValueError('Embedding adapter returned the wrong shape.')
    width = len(values[0])
    if any(len(row) != width or any(not math.isfinite(v) for v in row) for row in values):
        raise ValueError('Embedding vectors must be finite and have matching dimensions.')
    return values
