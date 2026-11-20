import os
import json
import time
import numpy as np
from generate_dataset import generate_articles
from generate_interactions import generate_interactions
from lda_modeler import LDAModeler
from embeddings_indexer import EmbeddingsIndexer
from recsys_hybrid import HybridRecSys
from diversity_injector import DiversityInjector

def run_full_pipeline(num_articles=10000, num_users=500):
    print("=" * 70)
    print("NEWSTAILOR END-TO-END PIPELINE: GENERATION, INDEXING & TRAINING")
    print("=" * 70)
    
    # 1. Dataset Generation
    articles_file = "articles_10k.json"
    if not os.path.exists(articles_file):
        articles = generate_articles(total_count=num_articles, output_path=articles_file)
    else:
        print(f"Loading existing {articles_file}...")
        with open(articles_file, "r", encoding="utf-8") as f:
            articles = json.load(f)
            
    # 2. Interactions & Users Generation
    interactions_file = "interactions.json"
    if not os.path.exists(interactions_file) or not os.path.exists("users.json"):
        users, interactions = generate_interactions(articles_file, num_users=num_users, output_path=interactions_file)
    else:
        print(f"Loading existing {interactions_file} and users.json...")
        with open("users.json", "r", encoding="utf-8") as f:
            users = json.load(f)
        with open(interactions_file, "r", encoding="utf-8") as f:
            interactions = json.load(f)
            
    # 3. Train LDA Topic Model
    lda_file = "lda_model.pkl"
    if not os.path.exists(lda_file):
        t0 = time.time()
        lda = LDAModeler(n_topics=8)
        lda.fit_transform(articles)
        lda.save(lda_file)
        print(f"LDA model training finished in {time.time() - t0:.2f}s")
    else:
        print(f"Loading existing {lda_file}...")
        lda = LDAModeler.load(lda_file)
        
    # 4. Sentence-BERT 512-dim Embeddings & FAISS Index
    index_dir = "index_data"
    if not os.path.exists(os.path.join(index_dir, "faiss_news.index")):
        t0 = time.time()
        indexer = EmbeddingsIndexer(model_name="all-MiniLM-L6-v2", target_dim=512)
        indexer.build_index(articles)
        indexer.save(index_dir)
        print(f"FAISS indexing finished in {time.time() - t0:.2f}s")
    else:
        print(f"Loading existing FAISS index from {index_dir}/...")
        indexer = EmbeddingsIndexer.load(index_dir)
        
    # 5. Hybrid Recommender (70% CF SVD + 30% CB FAISS)
    recsys_file = "hybrid_recsys.pkl"
    if not os.path.exists(recsys_file):
        t0 = time.time()
        recsys = HybridRecSys(cf_weight=0.70, cb_weight=0.30)
        recsys.set_articles(articles)
        recsys.fit_cf(interactions)
        recsys.save(recsys_file)
        print(f"Hybrid RecSys SVD training finished in {time.time() - t0:.2f}s")
    else:
        print(f"Loading existing {recsys_file}...")
        recsys = HybridRecSys.load(recsys_file)
        recsys.set_articles(articles)
        
    print("\n" + "=" * 70)
    print("TESTING HYBRID RECOMMENDATIONS + DIVERSITY INJECTOR")
    print("=" * 70)
    
    test_uid = users[0]["user_id"]
    print(f"Generating Top-10 recommendations for sample user {test_uid} ({users[0]['archetype']})...")
    candidates = recsys.get_hybrid_candidates(test_uid, indexer, top_n=50)
    
    injector = DiversityInjector(target_entropy=0.72)
    final_slate, div_score, mitigated, status_msg = injector.inject_diversity(
        candidates, lda, recsys.articles_map, slate_size=10
    )
    
    print(f"Final Diversity Score (Entropy): {div_score}")
    print(f"Status: {status_msg}")
    print("\nTop-10 Recommended Articles:")
    for rank, item in enumerate(final_slate, 1):
        art = recsys.articles_map[item["article_id"]]
        tag = "[DIVERSITY INJECTED]" if item.get("is_injected") else "[RECSYS HYBRID]"
        print(f"  {rank}. {tag} {art['title']}")
        print(f"     Category: {art['category']} | Alignment: {art['political_alignment']} | Score: {item['score']:.3f}")
        if item.get("injected_reason"):
            print(f"     Reason: {item['injected_reason']}")
            
    print("\nPipeline complete! All models, embeddings, and indices ready.")

if __name__ == "__main__":
    run_full_pipeline()
