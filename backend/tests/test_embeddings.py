import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.embeddings import EmbeddingBackend, cosine_scores_for_visible
import pandas as pd


def test_hashing_backend_similar_text_scores_higher():
    backend = EmbeddingBackend(kind="hashing")
    corpus = pd.DataFrame(
        [
            {"OperatorControlNumber": "A", "PartName": "PUMP", "Discrepancy": "hydraulic pump noise"},
            {"OperatorControlNumber": "B", "PartName": "VALVE", "Discrepancy": "unrelated weather radar"},
        ]
    )
    corpus = corpus.reset_index(drop=True)
    vecs = backend.encode([f"{r['PartName']} {r['Discrepancy']}" for _, r in corpus.iterrows()])
    visible = corpus.copy()
    scores = cosine_scores_for_visible(vecs, corpus, visible, "hydraulic pump noise", backend)
    assert float(scores[0]) >= float(scores[1])