import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.bm25 import BM25Index, tokenize


def test_tokenize_upper():
    assert tokenize("Hydraulic pump L/H INOP") == ["HYDRAULIC", "PUMP", "L", "H", "INOP"]


def test_bm25_ranks_matching_doc_higher():
    docs = [
        "fuel indicator failed after refuel",
        "hydraulic pump cracked on ground check",
        "unrelated weather radar test",
    ]
    index = BM25Index(docs)
    scores = index.score("hydraulic pump noise")
    assert scores[1] > scores[0]
    assert scores[1] > scores[2]