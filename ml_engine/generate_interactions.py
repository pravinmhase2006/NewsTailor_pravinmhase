import json
import random
import os

def generate_interactions(articles_path="articles_10k.json", num_users=500, output_path="interactions.json"):
    print(f"Generating synthetic user reading & rating interactions for {num_users} users...")
    random.seed(42)
    
    with open(articles_path, "r", encoding="utf-8") as f:
        articles = json.load(f)
        
    categories = list(set(a["category"] for a in articles))
    alignments = list(set(a["political_alignment"] for a in articles))
    
    users = []
    # Create archetypes so collaborative filtering discovers authentic clusters:
    # 1. Tech & Innovation Enthusiasts
    # 2. Left-leaning Politics & Climate
    # 3. Right-leaning Politics & Economy
    # 4. Global Diplomacy & World News
    # 5. Centrist All-Rounder
    archetypes = [
        {"name": "Tech Enthusiast", "pref_cats": ["Technology", "Healthcare & Science"], "pref_align": ["Center", "Center-Left"]},
        {"name": "Progressive Eco-Advocate", "pref_cats": ["Climate & Environment", "Politics"], "pref_align": ["Left", "Center-Left"]},
        {"name": "Market & Fiscal Conservative", "pref_cats": ["Economy & Finance", "Politics"], "pref_align": ["Right", "Center-Right"]},
        {"name": "Diplomacy & Global Affairs", "pref_cats": ["World & Diplomacy", "Economy & Finance"], "pref_align": ["Center", "Center-Left", "Center-Right"]},
        {"name": "General News Reader", "pref_cats": categories, "pref_align": alignments}
    ]
    
    for u in range(1, num_users + 1):
        arch = random.choice(archetypes)
        users.append({
            "user_id": f"usr_{u:04d}",
            "username": f"reader_{u}",
            "archetype": arch["name"],
            "pref_cats": arch["pref_cats"],
            "pref_align": arch["pref_align"]
        })
        
    interactions = []
    
    # Index articles by category and alignment for fast lookup
    cat_align_pool = {}
    for a in articles:
        key = (a["category"], a["political_alignment"])
        if key not in cat_align_pool:
            cat_align_pool[key] = []
        cat_align_pool[key].append(a["id"])
        
    for u in users:
        # Each user interacts with between 25 and 70 articles
        num_interactions = random.randint(25, 70)
        
        # 75% in-preference articles, 25% random exploration
        for _ in range(num_interactions):
            if random.random() < 0.75:
                cat = random.choice(u["pref_cats"])
                align = random.choice(u["pref_align"])
                key = (cat, align)
                pool = cat_align_pool.get(key, [])
                if not pool:
                    art_id = random.choice(articles)["id"]
                else:
                    art_id = random.choice(pool)
                # In-preference: high chance of like (rating 4 or 5 / upvote)
                rating = 5 if random.random() < 0.8 else 4
                action = "like" if rating >= 4 else "dislike"
            else:
                art = random.choice(articles)
                art_id = art["id"]
                # Out of preference: 50% chance like, 50% dislike/neutral (rating 1-3)
                rating = random.choice([1, 2, 3, 4, 5])
                action = "like" if rating >= 4 else "dislike"
                
            interactions.append({
                "user_id": u["user_id"],
                "article_id": art_id,
                "rating": rating,
                "action": action
            })
            
    # Save users and interactions
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)
        
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(interactions, f, indent=2)
        
    print(f"Generated {len(users)} users and {len(interactions)} interactions -> {output_path}")
    return users, interactions

if __name__ == "__main__":
    generate_interactions()
