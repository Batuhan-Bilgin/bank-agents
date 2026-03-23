import math
import re
from collections import Counter
from pathlib import Path

DB_PATH = Path(__file__).parent / "db"

_collection = None


def _get_collection():
    global _collection
    if _collection is not None:
        return _collection
    if not (DB_PATH / "chroma.sqlite3").exists():
        return None
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        client = chromadb.PersistentClient(path=str(DB_PATH))
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        _collection = client.get_or_create_collection(
            name="bank_workflows", embedding_function=ef
        )
        return _collection
    except Exception:
        return None


class BM25:
    def __init__(self, corpus: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.tokenized = [self._tokenize(d) for d in corpus]
        self.doc_freqs: list[Counter] = [Counter(t) for t in self.tokenized]
        self.doc_lengths = [len(t) for t in self.tokenized]
        self.avgdl = sum(self.doc_lengths) / max(len(self.doc_lengths), 1)
        self.N = len(corpus)
        self.idf: dict[str, float] = {}
        all_words = set(w for t in self.tokenized for w in t)
        for word in all_words:
            df = sum(1 for t in self.tokenized if word in t)
            self.idf[word] = math.log((self.N - df + 0.5) / (df + 0.5) + 1)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    def score(self, query: str, top_k: int = 10) -> list[tuple[int, float]]:
        tokens = self._tokenize(query)
        scores = []
        for i, tf in enumerate(self.doc_freqs):
            dl = self.doc_lengths[i]
            s = 0.0
            for token in tokens:
                if token not in tf:
                    continue
                idf = self.idf.get(token, 0)
                tf_val = tf[token]
                denom = tf_val + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                s += idf * (tf_val * (self.k1 + 1)) / denom
            scores.append((i, s))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


def _reciprocal_rank_fusion(rankings: list[list[int]], k: int = 60) -> list[int]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, doc_idx in enumerate(ranking):
            scores[doc_idx] = scores.get(doc_idx, 0) + 1.0 / (k + rank + 1)
    return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)


def retrieve(query: str, domains: list[str] | None = None,
             top_k: int = 5, min_relevance: float = 0.3,
             use_hybrid: bool = True) -> str:
    collection = _get_collection()
    if collection is None or collection.count() == 0:
        return ""

    where = {"domain": {"$in": domains}} if domains else None
    fetch_k = min(top_k * 4, collection.count())

    try:
        results = collection.query(
            query_texts=[query],
            n_results=fetch_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return ""

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    if not docs:
        return ""

    if use_hybrid and len(docs) > 1:
        semantic_ranking = list(range(len(docs)))

        bm25 = BM25(docs)
        bm25_scores = bm25.score(query, top_k=len(docs))
        bm25_ranking = [idx for idx, _ in bm25_scores]

        fused = _reciprocal_rank_fusion([semantic_ranking, bm25_ranking])
        final_indices = fused[:top_k]
    else:
        final_indices = list(range(min(top_k, len(docs))))

    chunks = []
    for i in final_indices:
        relevance = 1 - distances[i]
        if relevance < min_relevance:
            continue
        source = metas[i].get("source", "")
        domain = metas[i].get("domain", "")
        chunks.append(f"[{domain} / {source}]\n{docs[i]}")

    if not chunks:
        return ""

    return "\n\n---\n\n".join(chunks)


def retrieve_with_scores(query: str, domains: list[str] | None = None,
                         top_k: int = 5) -> list[dict]:
    collection = _get_collection()
    if collection is None or collection.count() == 0:
        return []

    where = {"domain": {"$in": domains}} if domains else None
    fetch_k = min(top_k * 3, collection.count())

    try:
        results = collection.query(
            query_texts=[query],
            n_results=fetch_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return []

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    output = []
    for doc, meta, dist in zip(docs, metas, distances):
        output.append({
            "text": doc,
            "source": meta.get("source", ""),
            "domain": meta.get("domain", ""),
            "relevance": round(1 - dist, 4),
        })

    return sorted(output, key=lambda x: x["relevance"], reverse=True)[:top_k]


def is_ready() -> bool:
    collection = _get_collection()
    return collection is not None and collection.count() > 0
