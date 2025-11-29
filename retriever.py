# retriever.py
import json
import os
import re
from collections import defaultdict
from typing import List, Dict, Any, Tuple

BASE_DIR = os.path.dirname(__file__)
RETRIEVER_PATH = os.path.join(BASE_DIR, "data", "retriever_index.json")

# ----------------- LOAD INDEX -----------------

with open(RETRIEVER_PATH, "r", encoding="utf-8") as f:
    _raw = json.load(f)

DOCUMENTS = _raw["documents"]          # list[{id, source, title, chunk_text, tokens}]
TERM_INDEX = _raw["term_index"]        # {token: [doc_id, ...]}

# Tạo map id -> doc để tra nhanh
DOC_BY_ID = {d["id"]: d for d in DOCUMENTS}
N_DOCS = len(DOCUMENTS)


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    return re.findall(r"\w+", text)


def search_docs(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Retriever rất đơn giản:
    - tokenize query
    - lấy các doc_id chứa những từ đó từ TERM_INDEX
    - score = tổng (idf(term)) với idf = log(N / (1 + df))
    - trả về top_k doc có score cao nhất
    """
    import math

    tokens = _tokenize(query)
    if not tokens:
        return []

    scores = defaultdict(float)

    for t in set(tokens):
        doc_ids = TERM_INDEX.get(t)
        if not doc_ids:
            continue
        df = len(doc_ids)
        idf = math.log((N_DOCS + 1) / (df + 1)) + 1.0  # idf đơn giản

        for doc_id in doc_ids:
            scores[doc_id] += idf

    if not scores:
        return []

    # sort theo score giảm dần
    ranked: List[Tuple[str, float]] = sorted(
        scores.items(), key=lambda x: x[1], reverse=True
    )

    top_docs = []
    for doc_id, sc in ranked[:top_k]:
        d = DOC_BY_ID[doc_id]
        top_docs.append(
            {
                "id": d["id"],
                "source": d["source"],
                "title": d["title"],
                "chunk_text": d["chunk_text"],
                "score": sc,
            }
        )
    return top_docs
