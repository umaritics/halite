"""Okapi BM25 over maintenance report text (evaluation only, no extra deps)."""
from __future__ import annotations

import math
import re
from collections import Counter


_TOKEN = re.compile(r"[A-Z0-9]+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return [t.upper() for t in _TOKEN.findall((text or "").upper())]


class BM25Index:
    def __init__(self, documents: list[str], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.docs = [tokenize(d) for d in documents]
        self.n_docs = len(self.docs)
        if self.n_docs == 0:
            self.avg_dl = 0.0
            self.df: Counter[str] = Counter()
            self.doc_lens: list[int] = []
            return
        self.doc_lens = [len(d) for d in self.docs]
        self.avg_dl = sum(self.doc_lens) / self.n_docs
        self.df = Counter()
        for doc in self.docs:
            for term in set(doc):
                self.df[term] += 1

    def _idf(self, term: str) -> float:
        n = self.df.get(term, 0)
        return math.log(1 + (self.n_docs - n + 0.5) / (n + 0.5))

    def score(self, query: str) -> list[float]:
        if not self.docs:
            return []
        q_terms = tokenize(query)
        scores = [0.0] * self.n_docs
        for term in q_terms:
            idf = self._idf(term)
            if idf <= 0:
                continue
            for i, doc in enumerate(self.docs):
                tf = doc.count(term)
                if tf == 0:
                    continue
                dl = self.doc_lens[i]
                denom = tf + self.k1 * (1 - self.b + self.b * dl / (self.avg_dl or 1))
                scores[i] += idf * (tf * (self.k1 + 1)) / denom
        return scores