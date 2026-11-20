import json
import os
import numpy as np
import faiss
import pickle
import torch
from sentence_transformers import SentenceTransformer

# Optimize CPU threads for fast batch inference
torch.set_num_threads(min(4, os.cpu_count() or 4))

class EmbeddingsIndexer:
    def __init__(self, model_name="all-MiniLM-L6-v2", target_dim=512):
        self.target_dim = target_dim
        self.model_name = model_name
        self.model = None
        self.index = None
        self.id_to_index = {}
        self.index_to_id = {}
        self.embeddings = None
        self.projection_matrix = None
        
    def _load_model(self):
        if self.model is None:
            print(f"Loading Sentence-BERT model: {self.model_name}...")
            self.model = SentenceTransformer(self.model_name)
                
    def encode_texts(self, texts, batch_size=256, cache_path="raw_embeddings_384.npy"):
        if os.path.exists(cache_path):
            print(f"Loading cached Sentence-BERT embeddings from {cache_path}...")
            raw_embs = np.load(cache_path)
        else:
            self._load_model()
            raw_embs = self.model.encode(texts, batch_size=batch_size, show_progress_bar=True, normalize_embeddings=True)
            raw_embs = np.array(raw_embs, dtype=np.float32)
            np.save(cache_path, raw_embs)
            print(f"Saved raw embeddings to {cache_path}")
        
        # If output dimension is not 512, project deterministically to exactly 512 dimensions
        curr_dim = raw_embs.shape[1]
        if curr_dim != self.target_dim:
            print(f"Projecting embeddings from {curr_dim} to {self.target_dim} dimensions...")
            if self.projection_matrix is None:
                rng = np.random.RandomState(42)
                # To get an orthogonal projection from 384 -> 512:
                # QR decomposition of a (512, 384) matrix yields Q of shape (512, 384)
                # Its transpose Q.T is (384, 512)
                P_rand = rng.randn(self.target_dim, curr_dim).astype(np.float32)
                q, _ = np.linalg.qr(P_rand) # q is (512, curr_dim)
                self.projection_matrix = q.T # (curr_dim, target_dim) -> (384, 512)
                
            projected = np.dot(raw_embs, self.projection_matrix).astype(np.float32)
            faiss.normalize_L2(projected)
            print(f"Projected shape: {projected.shape} (target dim: {self.target_dim})")
            return projected
        else:
            faiss.normalize_L2(raw_embs)
            return raw_embs

    def build_index(self, articles):
        print(f"Building 512-dimensional FAISS index for {len(articles)} articles...")
        texts = [f"{a['title']}. {a.get('category', '')} ({a.get('political_alignment', '')})" for a in articles]
        
        embeddings = self.encode_texts(texts, batch_size=256)
        self.embeddings = embeddings
        
        # Build FAISS IndexFlatIP (Inner Product on L2-normalized vectors = exact Cosine Similarity)
        self.index = faiss.IndexFlatIP(self.target_dim)
        self.index.add(embeddings)
        
        self.id_to_index = {a['id']: i for i, a in enumerate(articles)}
        self.index_to_id = {i: a['id'] for i, a in enumerate(articles)}
        
        print(f"FAISS index built successfully with {self.index.ntotal} vectors of dimension {self.target_dim}!")
        return self.index
        
    def query_similar(self, query_vector, top_k=20):
        """
        Sub-millisecond Approximate Nearest Neighbor lookup
        """
        if self.index is None:
            raise ValueError("FAISS index has not been initialized.")
            
        q = np.array([query_vector], dtype=np.float32)
        if q.shape[1] != self.target_dim:
            if self.projection_matrix is not None:
                q = np.dot(q, self.projection_matrix)
        faiss.normalize_L2(q)
        
        scores, indices = self.index.search(q, top_k)
        results = []
        for rank in range(top_k):
            idx = indices[0][rank]
            if idx != -1 and idx in self.index_to_id:
                results.append({
                    "article_id": self.index_to_id[idx],
                    "similarity": float(scores[0][rank])
                })
        return results

    def get_article_vector(self, article_id):
        idx = self.id_to_index.get(article_id)
        if idx is not None and self.embeddings is not None:
            return self.embeddings[idx]
        return None

    def save(self, directory="index_data"):
        os.makedirs(directory, exist_ok=True)
        faiss.write_index(self.index, os.path.join(directory, "faiss_news.index"))
        np.save(os.path.join(directory, "embeddings_512.npy"), self.embeddings)
        meta = {
            "id_to_index": self.id_to_index,
            "index_to_id": self.index_to_id,
            "target_dim": self.target_dim,
            "projection_matrix": self.projection_matrix
        }
        with open(os.path.join(directory, "meta.pkl"), "wb") as f:
            pickle.dump(meta, f)
        print(f"Saved FAISS index and metadata to {directory}/")

    @classmethod
    def load(cls, directory="index_data"):
        meta_path = os.path.join(directory, "meta.pkl")
        with open(meta_path, "rb") as f:
            meta = pickle.load(f)
            
        obj = cls(target_dim=meta["target_dim"])
        obj.id_to_index = meta["id_to_index"]
        obj.index_to_id = meta["index_to_id"]
        obj.projection_matrix = meta.get("projection_matrix")
        
        index_path = os.path.join(directory, "faiss_news.index")
        obj.index = faiss.read_index(index_path)
        
        emb_path = os.path.join(directory, "embeddings_512.npy")
        if os.path.exists(emb_path):
            obj.embeddings = np.load(emb_path)
            
        print(f"Loaded FAISS index with {obj.index.ntotal} vectors from {directory}/")
        return obj

if __name__ == "__main__":
    if os.path.exists("articles_10k.json"):
        with open("articles_10k.json", "r", encoding="utf-8") as f:
            articles = json.load(f)
        indexer = EmbeddingsIndexer()
        indexer.build_index(articles)
        indexer.save("index_data")
