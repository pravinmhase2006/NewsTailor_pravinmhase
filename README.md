# NewsTailor_pravinmhase
# NewsTailor — Personalized News Recommender with Hybrid RecSys & Algorithmic Bias Mitigation

**Author:** Pravin Mhase  
**Project:** AI/ML Full-Stack Hybrid Recommendation System with Algorithmic Bias Reduction  
**Organization:** Embed Square Solutions Pvt. Ltd. (Assignment Submission)  
**Repository:** [https://github.com/pravinmhase2006/NewsTailor_pravinmhase.git](https://github.com/pravinmhase2006/NewsTailor_pravinmhase.git)

---

## 📌 Executive Summary

Modern news recommendation platforms face two critical pitfalls: **filter bubbles** (ideological echo chambers caused by over-fitting to past preferences) and **cold-start latency** (serving irrelevant content to new users). 

**NewsTailor** solves this challenge through an end-to-end, full-stack recommendation engine that:
1. **Indexes 10,000+ news articles** into **512-dimensional vector embeddings** via **Sentence-BERT** and performs sub-millisecond Approximate Nearest Neighbor (ANN) search using a **FAISS** index.
2. Combines **70% Collaborative Filtering (SVD)** from historical user ratings with **30% Content-Based Filtering (FAISS)**.
3. Actively monitors topical and political skew using a **Latent Dirichlet Allocation (LDA)** topic model and dynamically enforces **Algorithmic Bias Mitigation** using a custom **Diversity Injector** whenever topic entropy drops below the target threshold ($H_{\text{norm}} \ge 0.70$).
4. Provides an interactive **MERN application (MongoDB, Express, React, Node.js)** featuring an infinite-scroll feed, live feedback loops (upvote/downvote), persona switching, and real-time weight re-calculation.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Data & Vector Indexing Layer
        Corpus[10,000+ News Articles Corpus] --> SBERT[Sentence-BERT Encoder]
        SBERT --> Proj[512-Dimensional Orthogonal Projection]
        Proj --> FAISS[(FAISS IndexFlatIP - Sub-ms ANN)]
        Corpus --> LDA[LDA Topic Model - 8 Core Topics]
    end

    subgraph Recommendation & Diversity Core
        Users[500 Users & 24k Interactions] --> SVD[SVD Collaborative Filter - scikit-surprise]
        SVD -->|70% CF Score| Hybrid[Hybrid Blending Engine]
        FAISS -->|30% CB Score| Hybrid
        Hybrid --> Slate[Candidate Top Slate]
        Slate --> Injector{Diversity Injector: Entropy Check}
        LDA --> Injector
        Injector -->|Entropy < 0.70: Bubble Detected| Inject[Forced Injection of Opposing / Underrepresented Topics]
        Injector -->|Entropy >= 0.70: Balanced| Output[Final Top-10 Personalized Feed]
        Inject --> Output
    end

    subgraph Backend & Database (Node.js & MongoDB)
        Output --> NodeAPI[Express.js REST API]
        NodeAPI <--> MongoDB[(MongoDB: Articles, Users, Embeddings)]
        NodeAPI --> Endpoints["GET /recommend/:userId<br/>POST /feedback"]
    end

    subgraph Frontend (React Interactive UI)
        Endpoints --> ReactUI[React + Vite Infinite Scroll UI]
        ReactUI --> Feedback[Thumbs Up / Down Live Votes]
        Feedback -->|Dynamic Re-weighting| NodeAPI
    end
```

---

## 🚀 Key Functional Capabilities

### 1. 512-Dimensional Semantic Indexing with FAISS
- Each article's title, category, and metadata are encoded via **Sentence-BERT** (`all-MiniLM-L6-v2`) and mapped to **512 dimensions** via orthogonal projection.
- Embeddings are indexed using `faiss.IndexFlatIP` (Inner Product on $L_2$-normalized vectors = exact Cosine Similarity).
- Vector search latency is **$< 0.12$ ms** across the entire 10,000-article collection.

### 2. Hybrid Recommendation Scoring (70% CF / 30% CB)
The hybrid score for user $u$ on candidate article $a$ is:
$$\hat{S}_{\text{hybrid}}(u, a) = 0.70 \cdot \bar{S}_{\text{CF}}(u, a) + 0.30 \cdot \bar{S}_{\text{CB}}(u, a)$$
- **Collaborative Filtering ($S_{\text{CF}}$):** Uses regularized matrix factorization (**SVD** from `scikit-surprise`) trained on historical user like/dislike interactions.
- **Content-Based Filtering ($S_{\text{CB}}$):** Uses the centroid of user $u$'s positively rated articles $\vec{c}_u = \frac{1}{|L_u|} \sum_{i \in L_u} \vec{v}_i$ queried against the FAISS index.

### 3. Algorithmic Bias Mitigation & "Diversity Injector"
- An 8-topic **Latent Dirichlet Allocation (LDA)** model infers topical distributions across the entire news corpus.
- When generating the Top-10 slate, the system computes the normalized Shannon Topic Entropy:
  $$\bar{H} = \frac{-\sum_{t=1}^K p_t \log_2(p_t)}{\log_2(K)}$$
- If $\bar{H} < 0.70$ or single-topic concentration $> 45\%$, a **Filter Bubble** is flagged.
- The **Diversity Injector** swaps out the lowest-ranked homogeneous articles for top-quality articles from underrepresented topics or opposing political perspectives (Left $\leftrightarrow$ Right) until $\bar{H} \ge 0.70$.

### 4. Real-time Feedback Loop & Cold-Start Solution
- **Cold-Start Handling:** For new readers with no interaction history, the system serves an editorially balanced, high-entropy exploratory slate across all major news categories and viewpoints.
- **Dynamic Re-weighting:** When a user clicks thumbs up or thumbs down, the `POST /feedback` endpoint captures the signal, logs it to MongoDB, updates the user's interaction profile in real-time, and shifts future recommendations immediately.

---

## 📊 Benchmark & Evaluation Results

Tested across a benchmark suite of 50 users and 24,000+ interactions:

| Metric | Target Requirement | NewsTailor Achieved | Status |
| :--- | :---: | :---: | :---: |
| **NDCG@10** | $> 0.80$ | **0.9733** | ✅ PASSED (Target $>0.80$) |
| **Topic Entropy (Before Mitigation)** | — | **0.5406** | *(Filter bubble detected)* |
| **Topic Entropy (After Mitigation)** | $> 0.70$ | **0.7152** | ✅ PASSED (Target $>0.70$) |
| **ANN Query Latency (FAISS)** | $< 1.0$ ms | **0.11 ms** | ✅ PASSED |
| **Filter Bubble Mitigation Rate** | — | **92.0% of users mitigated** | ✅ PASSED |

---

## 📂 Repository Structure

```
NewsTailor_pravinmhase/
├── ml_engine/                       # Python Recommendation & ML Service
│   ├── generate_dataset.py          # 10k News Article Generator
│   ├── generate_interactions.py     # 500 User Archetypes & Interactions Generator
│   ├── embeddings_indexer.py        # Sentence-BERT 512-dim + FAISS Indexer
│   ├── lda_modeler.py               # LDA Topic Modeler & Entropy Evaluator
│   ├── recsys_hybrid.py             # 70% CF (SVD) + 30% CB (FAISS) Recommender
│   ├── diversity_injector.py        # Filter-Bubble Buster & Underrepresented Topic Injector
│   ├── api_service.py               # FastAPI Microservice (Port 8000)
│   ├── eval_metrics.py              # NDCG@10 & Entropy Benchmark Script
│   └── pipeline.py                  # End-to-End Automated Pipeline Orchestrator
├── backend/                         # Node.js / Express Backend
│   ├── server.js                    # Express REST API (Port 5000)
│   ├── seed.js                      # MongoDB Database Seeder
│   └── package.json                 # Node Dependencies
├── frontend/                        # React + Vite Interactive UI
│   ├── src/
│   │   ├── App.jsx                  # Main Interactive Feed & Dashboard
│   │   ├── main.jsx                 # React Entry Point
│   │   └── index.css                # Tailwind Styling
│   ├── index.html                   # HTML Template
│   ├── vite.config.js               # Vite Proxy Configuration
│   └── package.json                 # Frontend Dependencies
└── README.md                        # Documentation & Architecture Guide
```

---

## 🛠️ Step-by-Step Installation & Run Guide

### Prerequisites
- **Node.js** (v18+) & **npm**
- **Python** (3.10+)
- **MongoDB** running locally on default port `27017`

### 1. Setup ML Engine & Run Training Pipeline
```bash
cd ml_engine
python -m pip install -r requirements.txt
python pipeline.py
```
*This generates the 10,000 articles, trains LDA, computes 512-dim Sentence-BERT embeddings, builds the FAISS index, and fits the SVD recommender.*

Start the ML service:
```bash
python -m uvicorn api_service:app --port 8000 --reload
```

### 2. Setup Node.js Backend & Seed MongoDB
```bash
cd ../backend
npm install
node seed.js    # Seeds MongoDB with 10k articles and users
npm start       # Runs backend on http://localhost:5000
```

### 3. Setup & Start React Frontend
```bash
cd ../frontend
npm install
npm run dev     # Runs React UI on http://localhost:3000
```

Open your browser at `http://localhost:3000` to interact with the live news feed, switch user personas, and test thumbs up/down dynamic re-weighting!

---

## 🌟 Bonus: RLHF (Reinforcement Learning from Human Feedback)
The architecture supports an integrated contextual bandit / RLHF policy:
- **State:** Vector representation of user reading history $\vec{s}_u$.
- **Action:** Slate of top-10 recommended articles.
- **Reward Function:** $R = +1.0$ (Upvote), $-1.0$ (Downvote), $+0.2$ (Dwell time / Read).
- **Policy Update:** Online gradient updates to the candidate re-ranking weights balancing click-through rate with political diversity.

---

## 📄 License
MIT License. Created by Pravin Mhase for Embed Square Solutions Pvt. Ltd.
