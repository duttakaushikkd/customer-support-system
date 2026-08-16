from pathlib import Path

from app.config import settings
from app.services import mongo
from app.services.llm import embed

KB_DIR = Path(__file__).resolve().parent.parent.parent / "kb" / "articles"


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _load_articles(kb_dir: Path) -> list[dict]:
    articles = []
    if not kb_dir.exists():
        return articles
    for path in sorted(kb_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, _, body = text.partition("\n---\n")
        fields: dict[str, str] = {}
        for line in meta.strip().splitlines():
            if line.startswith("---"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                fields[k.strip()] = v.strip()
        articles.append(
            {
                "article_id": fields.get("id", path.stem),
                "title": fields.get("title", path.stem),
                "category": fields.get("category", "general"),
                "confidence_tag": fields.get("confidence_tag", "human_review"),
                "proposed_action": fields.get("proposed_action", "reply_kb"),
                "body": body.strip(),
            }
        )
    return articles


def seed_kb_if_needed(kb_dir: Path | None = None) -> None:
    kb_dir = kb_dir or KB_DIR
    articles = _load_articles(kb_dir)
    if not articles:
        return
    if mongo.kb_articles().count_documents({}) >= len(articles):
        return
    upsert_articles(articles)


def upsert_articles(articles: list[dict]) -> None:
    vectors = embed([f"{a['title']}\n{a['body']}" for a in articles])
    for article, vector in zip(articles, vectors):
        mongo.kb_articles().replace_one(
            {"article_id": article["article_id"]},
            {**article, "embedding": vector},
            upsert=True,
        )


def search_kb(query: str, limit: int = 3) -> list[dict]:
    seed_kb_if_needed()
    query_vec = embed([query])[0]
    docs = list(mongo.kb_articles().find({}, {"_id": 0}))
    ranked: list[dict] = []
    for doc in docs:
        vector = doc.get("embedding") or []
        score = _cosine(query_vec, vector)
        ranked.append(
            {
                **{k: v for k, v in doc.items() if k != "embedding"},
                "score": score,
                "snippet": (doc.get("body") or "")[:280],
            }
        )
    ranked.sort(key=lambda d: d["score"], reverse=True)
    results = ranked[:limit]
    if not results or results[0]["score"] < settings.rag_confidence_floor:
        lexical = _lexical_search(query, limit)
        if lexical and (not results or lexical[0]["score"] > results[0]["score"]):
            results = lexical
    return results


def _lexical_search(query: str, limit: int) -> list[dict]:
    articles = _load_articles(KB_DIR)
    if not articles:
        articles = [
            {k: v for k, v in d.items() if k != "embedding"}
            for d in mongo.kb_articles().find({}, {"_id": 0, "embedding": 0})
        ]
    q_tokens = set(query.lower().split())
    scored = []
    for article in articles:
        blob = f"{article.get('title', '')} {article.get('body', '')}".lower()
        overlap = sum(1 for tok in q_tokens if tok in blob)
        score = overlap / max(len(q_tokens), 1)
        scored.append({**article, "score": score, "snippet": (article.get("body") or "")[:280]})
    scored.sort(key=lambda a: a["score"], reverse=True)
    return scored[:limit]
