import json
import os
import pickle
import numpy as np
import pandas as pd
from surprise import Dataset, Reader, SVD
from surprise.model_selection import train_test_split

class HybridRecSys:
    def __init__(self, cf_weight=0.70, cb_weight=0.30, random_state=42):
        self.cf_weight = cf_weight
        self.cb_weight = cb_weight
        self.random_state = random_state
        self.svd_model = None
        self.user_history = {} # user_id -> list of (article_id, rating)
        self.all_article_ids = []
        self.articles_map = {}
        
    def fit_cf(self, interactions):
        """
        Fits SVD collaborative filtering on user-article ratings
        """
        print(f"Training SVD Collaborative Filter on {len(interactions)} interactions...")
        df = pd.DataFrame(interactions)
        reader = Reader(rating_scale=(1, 5))
        data = Dataset.load_from_df(df[['user_id', 'article_id', 'rating']], reader)
        
        trainset = data.build_full_trainset()
        self.svd_model = SVD(n_factors=30, n_epochs=20, lr_all=0.005, reg_all=0.02, random_state=self.random_state)
        self.svd_model.fit(trainset)
        
        # Build user interaction cache
        self.user_history = {}
        for row in interactions:
            uid = row['user_id']
            aid = row['article_id']
            r = row['rating']
            if uid not in self.user_history:
                self.user_history[uid] = []
            self.user_history[uid].append((aid, r))
            
        print("SVD Collaborative Filtering model trained successfully.")

    def set_articles(self, articles):
        self.all_article_ids = [a['id'] for a in articles]
        self.articles_map = {a['id']: a for a in articles}

    def predict_cf_scores(self, user_id, candidate_ids):
        """
        Predicts CF rating for each candidate article and normalizes to [0, 1]
        """
        scores = {}
        for aid in candidate_ids:
            if self.svd_model is not None:
                pred = self.svd_model.predict(user_id, aid).est
            else:
                pred = 3.0
            scores[aid] = pred
            
        # Min-max normalization
        vals = list(scores.values())
        min_v, max_v = min(vals), max(vals)
        if max_v - min_v > 1e-6:
            for aid in scores:
                scores[aid] = (scores[aid] - min_v) / (max_v - min_v)
        else:
            for aid in scores:
                scores[aid] = 0.5
        return scores

    def compute_cb_scores(self, user_id, candidate_ids, embeddings_indexer):
        """
        Computes Content-Based similarity using FAISS embeddings of liked articles
        """
        scores = {aid: 0.5 for aid in candidate_ids}
        history = self.user_history.get(user_id, [])
        liked = [aid for aid, r in history if r >= 4]
        
        if not liked or embeddings_indexer.index is None:
            # Cold-start or no likes yet
            return scores
            
        # Build user profile vector by averaging embeddings of liked articles
        liked_vectors = []
        for aid in liked:
            vec = embeddings_indexer.get_article_vector(aid)
            if vec is not None:
                liked_vectors.append(vec)
                
        if not liked_vectors:
            return scores
            
        user_vector = np.mean(liked_vectors, axis=0)
        
        # Query FAISS for nearest neighbors
        # We search a large pool to cover candidates
        search_k = min(len(self.all_article_ids), 300)
        ann_results = embeddings_indexer.query_similar(user_vector, top_k=search_k)
        
        ann_map = {r['article_id']: r['similarity'] for r in ann_results}
        
        for aid in candidate_ids:
            if aid in ann_map:
                scores[aid] = ann_map[aid]
            else:
                scores[aid] = 0.0
                
        # Min-max normalization
        vals = list(scores.values())
        min_v, max_v = min(vals), max(vals)
        if max_v - min_v > 1e-6:
            for aid in scores:
                scores[aid] = (scores[aid] - min_v) / (max_v - min_v)
        else:
            for aid in scores:
                scores[aid] = 0.5
        return scores

    def get_hybrid_candidates(self, user_id, embeddings_indexer, top_n=50):
        """
        Computes 70% CF + 30% CB hybrid scores across a pool of candidates
        """
        read_articles = set(aid for aid, _ in self.user_history.get(user_id, []))
        # Exclude already read/voted articles
        unseen_ids = [aid for aid in self.all_article_ids if aid not in read_articles]
        
        if not unseen_ids:
            unseen_ids = self.all_article_ids
            
        # Cold start check
        is_cold_start = len(read_articles) == 0
        if is_cold_start:
            # Use popularity / editorial baseline
            sample_candidates = sorted(
                unseen_ids, 
                key=lambda aid: self.articles_map.get(aid, {}).get('upvotes', 0), 
                reverse=True
            )[:top_n * 2]
        else:
            # Sample candidate pool (mix of CF top candidates and trending)
            sample_candidates = unseen_ids[:min(len(unseen_ids), 500)]
            
        cf_scores = self.predict_cf_scores(user_id, sample_candidates)
        cb_scores = self.compute_cb_scores(user_id, sample_candidates, embeddings_indexer)
        
        hybrid_scores = []
        for aid in sample_candidates:
            s_cf = cf_scores.get(aid, 0.5)
            s_cb = cb_scores.get(aid, 0.5)
            s_hybrid = (self.cf_weight * s_cf) + (self.cb_weight * s_cb)
            hybrid_scores.append({
                "article_id": aid,
                "score": float(s_hybrid),
                "cf_score": float(s_cf),
                "cb_score": float(s_cb)
            })
            
        hybrid_scores.sort(key=lambda x: x["score"], reverse=True)
        return hybrid_scores[:top_n]

    def add_interaction(self, user_id, article_id, rating):
        """
        Dynamically captures real-time user feedback (like/dislike)
        """
        if user_id not in self.user_history:
            self.user_history[user_id] = []
        self.user_history[user_id].append((article_id, rating))

    def save(self, filepath="hybrid_recsys.pkl"):
        data = {
            "cf_weight": self.cf_weight,
            "cb_weight": self.cb_weight,
            "svd_model": self.svd_model,
            "user_history": self.user_history,
            "all_article_ids": self.all_article_ids
        }
        with open(filepath, "wb") as f:
            pickle.dump(data, f)
        print(f"Saved Hybrid RecSys model to {filepath}")

    @classmethod
    def load(cls, filepath="hybrid_recsys.pkl"):
        with open(filepath, "rb") as f:
            data = pickle.load(f)
        obj = cls(cf_weight=data["cf_weight"], cb_weight=data["cb_weight"])
        obj.svd_model = data["svd_model"]
        obj.user_history = data["user_history"]
        obj.all_article_ids = data["all_article_ids"]
        return obj
