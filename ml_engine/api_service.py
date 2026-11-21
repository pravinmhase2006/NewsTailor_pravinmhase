"""
NewsTailor ML Recommendation & Algorithmic Bias Mitigation Engine
Exposes high-performance REST APIs for hybrid recommendations, FAISS ANN retrieval,
LDA topic-based filter-bubble detection, and real-time feedback re-weighting.

Author: Pravin Mhase
Organization: Embed Square Solutions Pvt. Ltd.
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from lda_modeler import LDAModeler
from embeddings_indexer import EmbeddingsIndexer
from recsys_hybrid import HybridRecSys
from diversity_injector import DiversityInjector

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("NewsTailor-MLEngine")

# Global in-memory model instances
articles_data: List[Dict[str, Any]] = []
articles_map: Dict[str, Dict[str, Any]] = {}
users_data: List[Dict[str, Any]] = []
users_map: Dict[str, Dict[str, Any]] = {}
lda: Optional[LDAModeler] = None
indexer: Optional[EmbeddingsIndexer] = None
recsys: Optional[HybridRecSys] = None
injector: Optional[DiversityInjector] = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_ml_resources():
    """Initializes and caches all vector indices, models, and metadata into RAM."""
    global articles_data, articles_map, users_data, users_map, lda, indexer, recsys, injector

    logger.info("Loading NewsTailor ML models and indexes into memory...")

    # 1. Load 10k Articles
    articles_path = os.path.join(BASE_DIR, "articles_10k.json")
    if os.path.exists(articles_path):
        with open(articles_path, "r", encoding="utf-8") as f:
            articles_data = json.load(f)
            articles_map = {a["id"]: a for a in articles_data}
        logger.info("Loaded %d articles from %s", len(articles_data), articles_path)

    # 2. Load User Cohort
    users_path = os.path.join(BASE_DIR, "users.json")
    if os.path.exists(users_path):
        with open(users_path, "r", encoding="utf-8") as f:
            users_data = json.load(f)
            users_map = {u["user_id"]: u for u in users_data}
        logger.info("Loaded %d user profiles from %s", len(users_data), users_path)

    # 3. Load LDA Model
    lda_path = os.path.join(BASE_DIR, "lda_model.pkl")
    if os.path.exists(lda_path):
        lda = LDAModeler.load(lda_path)
        logger.info("Loaded LDA Topic Model with %d topics", lda.n_topics)

    # 4. Load 512-dim FAISS Vector Index
    index_dir = os.path.join(BASE_DIR, "index_data")
    if os.path.exists(os.path.join(index_dir, "faiss_news.index")):
        indexer = EmbeddingsIndexer.load(index_dir)
        logger.info("Loaded FAISS Vector Index with %d vectors (dim: %d)", indexer.index.ntotal, indexer.target_dim)

    # 5. Load SVD Collaborative Filter
    recsys_path = os.path.join(BASE_DIR, "hybrid_recsys.pkl")
    if os.path.exists(recsys_path):
        recsys = HybridRecSys.load(recsys_path)
        recsys.set_articles(articles_data)
        logger.info("Loaded SVD Collaborative Filtering model")
    elif articles_data:
        recsys = HybridRecSys(cf_weight=0.70, cb_weight=0.30)
        recsys.set_articles(articles_data)

    # 6. Initialize Diversity Injector
    injector = DiversityInjector(target_entropy=0.72)
    logger.info("Diversity Injector initialized with target entropy threshold: 0.72")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_ml_resources()
    yield
    logger.info("Shutting down NewsTailor ML Engine.")


app = FastAPI(
    title="NewsTailor Recommendation & Diversity Engine",
    description="Hybrid RecSys (70% CF SVD + 30% CB FAISS) with LDA Algorithmic Bias Mitigation",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# Pydantic Request / Response Schemas
# ==========================================

class FeedbackPayload(BaseModel):
    user_id: str = Field(..., description="Unique user identifier, e.g., 'usr_0001'")
    article_id: str = Field(..., description="Unique article ID, e.g., 'art_00042'")
    action: str = Field(..., description="User feedback action: 'like' or 'dislike'")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Explicit rating (1 to 5)")


class RecommendedArticle(BaseModel):
    rank: int
    article_id: str
    title: str
    snippet: str
    category: str
    political_alignment: str
    source: str
    published_at: str
    tags: List[str]
    score: float
    cf_score: float
    cb_score: float
    is_injected: bool
    injected_reason: Optional[str]
    dominant_topic: str


class RecommendationResponse(BaseModel):
    user_id: str
    is_cold_start: bool
    count: int
    diversity_score: float
    target_entropy_threshold: float
    mitigation_applied: bool
    status_message: str
    topic_distribution: List[float]
    recommendations: List[RecommendedArticle]


# ==========================================
# REST API Endpoints
# ==========================================

@app.get("/", summary="Root Health & Meta Information")
def root():
    return {
        "service": "NewsTailor ML Recommendation Engine",
        "status": "online",
        "version": "1.0.0",
        "vector_dimensions": indexer.target_dim if indexer else 512,
        "hybrid_weights": {"collaborative_filtering": 0.70, "content_based": 0.30},
        "bias_mitigation": "Active (LDA Topic Model + Diversity Injector)"
    }


@app.get("/health", summary="Service Healthcheck")
def healthcheck():
    return {
        "status": "healthy",
        "models_loaded": {
            "faiss_index": indexer is not None and indexer.index is not None,
            "lda_model": lda is not None,
            "svd_recsys": recsys is not None and recsys.svd_model is not None,
            "articles_count": len(articles_data)
        }
    }


@app.get("/recommend/{user_id}", response_model=RecommendationResponse, summary="Serve Top-10 Personalized Feed")
def get_recommendations(user_id: str, k: int = Query(default=10, ge=1, le=50)):
    """
    Computes hybrid scores (70% CF + 30% CB), monitors topic entropy,
    and injects underrepresented/opposing articles if a filter bubble is detected.
    """
    if recsys is None or indexer is None or lda is None or injector is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML models are initializing. Please retry in a few seconds."
        )

    is_cold_start = user_id not in recsys.user_history or len(recsys.user_history[user_id]) == 0

    # 1. Candidate Generation (70% SVD Collaborative + 30% FAISS Content-Based)
    candidates = recsys.get_hybrid_candidates(user_id, indexer, top_n=max(50, k * 3))

    # 2. Algorithmic Bias Mitigation (Filter-Bubble Buster)
    final_slate, div_score, mitigated, status_msg = injector.inject_diversity(
        candidates, lda, articles_map, slate_size=k
    )

    # 3. Compute Slate Metrics
    slate_ids = [c["article_id"] for c in final_slate]
    norm_entropy, topic_probs = lda.calculate_slate_entropy(slate_ids)

    recommended_articles = []
    for rank, item in enumerate(final_slate, 1):
        art_id = item["article_id"]
        art = articles_map.get(art_id, {})
        topic_idx = lda.article_dominant_topic.get(art_id, 0)
        topic_name = lda.topic_names[topic_idx] if topic_idx < len(lda.topic_names) else f"Topic {topic_idx}"

        recommended_articles.append(RecommendedArticle(
            rank=rank,
            article_id=art_id,
            title=art.get("title", ""),
            snippet=art.get("snippet", ""),
            category=art.get("category", ""),
            political_alignment=art.get("political_alignment", "Center"),
            source=art.get("source", ""),
            published_at=art.get("published_at", ""),
            tags=art.get("tags", []),
            score=round(item.get("score", 0.5), 4),
            cf_score=round(item.get("cf_score", 0.5), 4),
            cb_score=round(item.get("cb_score", 0.5), 4),
            is_injected=item.get("is_injected", False),
            injected_reason=item.get("injected_reason"),
            dominant_topic=topic_name
        ))

    return RecommendationResponse(
        user_id=user_id,
        is_cold_start=is_cold_start,
        count=len(recommended_articles),
        diversity_score=round(div_score, 4),
        target_entropy_threshold=0.70,
        mitigation_applied=mitigated,
        status_message=status_msg,
        topic_distribution=[round(p, 4) for p in topic_probs],
        recommendations=recommended_articles
    )


@app.post("/feedback", summary="Capture Real-Time Thumbs Up/Down and Re-weight")
def submit_feedback(payload: FeedbackPayload):
    """Dynamically updates user interaction history and recalculates user profile centroid."""
    if recsys is None:
        raise HTTPException(status_code=503, detail="RecSys model not ready.")

    rating = payload.rating
    if rating is None:
        rating = 5 if payload.action.lower() == "like" else 1

    recsys.add_interaction(payload.user_id, payload.article_id, rating)

    if payload.article_id in articles_map:
        if payload.action.lower() == "like":
            articles_map[payload.article_id]["upvotes"] = articles_map[payload.article_id].get("upvotes", 0) + 1
        else:
            articles_map[payload.article_id]["downvotes"] = articles_map[payload.article_id].get("downvotes", 0) + 1

    logger.info("Recorded feedback: User %s %sd article %s (Rating: %d)", payload.user_id, payload.action, payload.article_id, rating)

    return {
        "success": True,
        "user_id": payload.user_id,
        "article_id": payload.article_id,
        "action": payload.action,
        "rating": rating,
        "total_interactions_for_user": len(recsys.user_history.get(payload.user_id, []))
    }


@app.get("/stats", summary="Engine Statistics")
def get_stats():
    return {
        "articles_indexed": len(articles_data),
        "faiss_total_vectors": indexer.index.ntotal if indexer and indexer.index else 0,
        "vector_dim": indexer.target_dim if indexer else 512,
        "lda_topics_count": lda.n_topics if lda else 0,
        "lda_topic_names": lda.topic_names if lda else [],
        "total_registered_users": len(users_data)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_service:app", host="0.0.0.0", port=8000, reload=False)
