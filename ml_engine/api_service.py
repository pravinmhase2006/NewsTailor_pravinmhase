import os
import json
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from lda_modeler import LDAModeler
from embeddings_indexer import EmbeddingsIndexer
from recsys_hybrid import HybridRecSys
from diversity_injector import DiversityInjector

app = FastAPI(
    title="NewsTailor Recommendation & Diversity Engine",
    description="Hybrid RecSys (70% CF SVD + 30% CB FAISS) with LDA Algorithmic Bias Mitigation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory models
articles_data = []
articles_map = {}
users_data = []
users_map = {}
lda = None
indexer = None
recsys = None
injector = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def init_models():
    global articles_data, articles_map, users_data, users_map, lda, indexer, recsys, injector
    
    print("[API] Initializing NewsTailor ML Engine components...")
    articles_path = os.path.join(BASE_DIR, "articles_10k.json")
    if os.path.exists(articles_path):
        with open(articles_path, "r", encoding="utf-8") as f:
            articles_data = json.load(f)
            articles_map = {a["id"]: a for a in articles_data}
            
    users_path = os.path.join(BASE_DIR, "users.json")
    if os.path.exists(users_path):
        with open(users_path, "r", encoding="utf-8") as f:
            users_data = json.load(f)
            users_map = {u["user_id"]: u for u in users_data}
            
    lda_path = os.path.join(BASE_DIR, "lda_model.pkl")
    if os.path.exists(lda_path):
        lda = LDAModeler.load(lda_path)
        
    index_dir = os.path.join(BASE_DIR, "index_data")
    if os.path.exists(os.path.join(index_dir, "faiss_news.index")):
        indexer = EmbeddingsIndexer.load(index_dir)
        
    recsys_path = os.path.join(BASE_DIR, "hybrid_recsys.pkl")
    if os.path.exists(recsys_path):
        recsys = HybridRecSys.load(recsys_path)
        recsys.set_articles(articles_data)
    elif articles_data:
        recsys = HybridRecSys(cf_weight=0.70, cb_weight=0.30)
        recsys.set_articles(articles_data)
        
    injector = DiversityInjector(target_entropy=0.72)
    print(f"[API] Initialization complete: {len(articles_data)} articles, {len(users_data)} users loaded.")

@app.on_event("startup")
def startup_event():
    init_models()

class FeedbackPayload(BaseModel):
    user_id: str
    article_id: str
    action: str # "like" or "dislike"
    rating: Optional[int] = None

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "NewsTailor ML Recommendation Engine",
        "vector_dimensions": 512,
        "hybrid_weights": {"collaborative_filtering": 0.70, "content_based": 0.30},
        "bias_mitigation": "Active (LDA Topic Model + Diversity Injector)"
    }

@app.get("/recommend/{user_id}")
def get_recommendations(user_id: str, k: int = Query(default=10, ge=1, le=50)):
    if recsys is None or indexer is None or lda is None:
        init_models()
        if recsys is None:
            raise HTTPException(status_code=503, detail="Models are still initializing. Try again in a few moments.")
            
    is_cold_start = user_id not in recsys.user_history or len(recsys.user_history[user_id]) == 0
    
    # 1. Fetch Top Hybrid Candidates (70% CF + 30% CB)
    candidates = recsys.get_hybrid_candidates(user_id, indexer, top_n=max(50, k * 3))
    
    # 2. Algorithmic Bias Mitigation & Diversity Injection
    final_slate, div_score, mitigated, status_msg = injector.inject_diversity(
        candidates, lda, articles_map, slate_size=k
    )
    
    # 3. Enrich with article metadata & topic metrics
    slate_ids = [c["article_id"] for c in final_slate]
    norm_entropy, topic_probs = lda.calculate_slate_entropy(slate_ids)
    
    recommended_articles = []
    for rank, item in enumerate(final_slate, 1):
        art_id = item["article_id"]
        art = articles_map.get(art_id, {})
        topic_idx = lda.article_dominant_topic.get(art_id, 0)
        topic_name = lda.topic_names[topic_idx] if topic_idx < len(lda.topic_names) else f"Topic {topic_idx}"
        
        recommended_articles.append({
            "rank": rank,
            "article_id": art_id,
            "title": art.get("title", ""),
            "snippet": art.get("snippet", ""),
            "category": art.get("category", ""),
            "political_alignment": art.get("political_alignment", "Center"),
            "source": art.get("source", ""),
            "published_at": art.get("published_at", ""),
            "tags": art.get("tags", []),
            "score": round(item.get("score", 0.5), 4),
            "cf_score": round(item.get("cf_score", 0.5), 4),
            "cb_score": round(item.get("cb_score", 0.5), 4),
            "is_injected": item.get("is_injected", False),
            "injected_reason": item.get("injected_reason"),
            "dominant_topic": topic_name
        })
        
    return {
        "user_id": user_id,
        "is_cold_start": is_cold_start,
        "count": len(recommended_articles),
        "diversity_score": round(div_score, 4),
        "target_entropy_threshold": 0.70,
        "mitigation_applied": mitigated,
        "status_message": status_msg,
        "topic_distribution": [round(p, 4) for p in topic_probs],
        "recommendations": recommended_articles
    }

@app.post("/feedback")
def submit_feedback(payload: FeedbackPayload):
    if recsys is None:
        init_models()
        
    rating = payload.rating
    if rating is None:
        rating = 5 if payload.action.lower() == "like" else 1
        
    recsys.add_interaction(payload.user_id, payload.article_id, rating)
    
    # Update article counters
    if payload.article_id in articles_map:
        if payload.action.lower() == "like":
            articles_map[payload.article_id]["upvotes"] = articles_map[payload.article_id].get("upvotes", 0) + 1
        else:
            articles_map[payload.article_id]["downvotes"] = articles_map[payload.article_id].get("downvotes", 0) + 1
            
    return {
        "success": True,
        "user_id": payload.user_id,
        "article_id": payload.article_id,
        "action": payload.action,
        "updated_rating": rating,
        "total_user_interactions": len(recsys.user_history.get(payload.user_id, []))
    }

@app.get("/articles")
def get_articles(page: int = 1, limit: int = 15, category: Optional[str] = None):
    start = (page - 1) * limit
    end = start + limit
    filtered = articles_data
    if category:
        filtered = [a for a in filtered if a.get("category", "").lower() == category.lower()]
    
    total = len(filtered)
    items = filtered[start:end]
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "has_more": end < total,
        "articles": items
    }

@app.get("/users")
def get_users():
    return {
        "count": len(users_data),
        "users": users_data[:20] # Return first 20 user personas for quick UI selection
    }

@app.get("/stats")
def get_stats():
    return {
        "articles_indexed": len(articles_data),
        "faiss_total_vectors": indexer.index.ntotal if indexer and indexer.index else 0,
        "vector_dim": 512,
        "lda_topics_count": lda.n_topics if lda else 0,
        "lda_topic_names": lda.topic_names if lda else [],
        "total_registered_users": len(users_data)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_service:app", host="127.0.0.1", port=8000, reload=False)
