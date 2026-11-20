import json
import os
import pickle
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation

class LDAModeler:
    def __init__(self, n_topics=8, random_state=42):
        self.n_topics = n_topics
        self.random_state = random_state
        self.vectorizer = CountVectorizer(
            max_df=0.85, 
            min_df=3, 
            stop_words='english',
            max_features=2500
        )
        self.lda_model = LatentDirichletAllocation(
            n_components=n_topics,
            random_state=random_state,
            learning_method='online',
            batch_size=256,
            max_iter=15,
            n_jobs=-1
        )
        self.topic_names = []
        self.article_topic_dist = {}
        self.article_dominant_topic = {}
        
    def fit_transform(self, articles):
        print(f"Training LDA topic model with {self.n_topics} topics on {len(articles)} articles...")
        texts = [f"{a['title']} {a['snippet']} {a.get('category', '')} {' '.join(a.get('tags', []))}" for a in articles]
        dtm = self.vectorizer.fit_transform(texts)
        topic_distributions = self.lda_model.fit_transform(dtm)
        
        # Determine dominant terms for each topic
        feature_names = self.vectorizer.get_feature_names_out()
        self.topic_names = []
        for topic_idx, topic in enumerate(self.lda_model.components_):
            top_words_idx = topic.argsort()[:-6:-1]
            top_words = [feature_names[i] for i in top_words_idx]
            self.topic_names.append(f"Topic {topic_idx}: " + ", ".join(top_words))
            print(f"  [LDA] {self.topic_names[-1]}")
            
        for idx, a in enumerate(articles):
            dist = topic_distributions[idx].tolist()
            dom = int(np.argmax(dist))
            self.article_topic_dist[a['id']] = dist
            self.article_dominant_topic[a['id']] = dom
            
        print("LDA training completed successfully.")
        return self.article_topic_dist
        
    def get_topic_distribution(self, article_id):
        return self.article_topic_dist.get(article_id, [1.0 / self.n_topics] * self.n_topics)
        
    def calculate_slate_entropy(self, article_ids):
        """
        Calculates normalized Shannon Entropy of the topic distribution across a slate of articles.
        H_norm in [0.0, 1.0].
        A higher score means diverse representation; lower means a filter bubble.
        """
        if not article_ids:
            return 0.0
            
        aggregated_probs = np.zeros(self.n_topics)
        for aid in article_ids:
            dist = np.array(self.get_topic_distribution(aid))
            aggregated_probs += dist
            
        aggregated_probs /= len(article_ids)
        # Avoid log(0)
        eps = 1e-12
        probs = np.clip(aggregated_probs, eps, 1.0)
        probs = probs / np.sum(probs)
        
        raw_entropy = -np.sum(probs * np.log2(probs))
        max_entropy = np.log2(self.n_topics)
        normalized_entropy = float(raw_entropy / max_entropy)
        return normalized_entropy, probs.tolist()

    def save(self, filepath="lda_model.pkl"):
        data = {
            "n_topics": self.n_topics,
            "vectorizer": self.vectorizer,
            "lda_model": self.lda_model,
            "topic_names": self.topic_names,
            "article_topic_dist": self.article_topic_dist,
            "article_dominant_topic": self.article_dominant_topic
        }
        with open(filepath, "wb") as f:
            pickle.dump(data, f)
        print(f"Saved LDA model to {filepath}")

    @classmethod
    def load(cls, filepath="lda_model.pkl"):
        with open(filepath, "rb") as f:
            data = pickle.load(f)
        obj = cls(n_topics=data["n_topics"])
        obj.vectorizer = data["vectorizer"]
        obj.lda_model = data["lda_model"]
        obj.topic_names = data["topic_names"]
        obj.article_topic_dist = data["article_topic_dist"]
        obj.article_dominant_topic = data["article_dominant_topic"]
        return obj

if __name__ == "__main__":
    if os.path.exists("articles_10k.json"):
        with open("articles_10k.json", "r", encoding="utf-8") as f:
            articles = json.load(f)
        modeler = LDAModeler(n_topics=8)
        modeler.fit_transform(articles)
        modeler.save("lda_model.pkl")
