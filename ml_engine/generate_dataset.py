import json
import random
import os
from datetime import datetime, timedelta

CATEGORIES = {
    "Politics": {
        "topics": [
            "Election Reform and Campaign Finance",
            "Congressional Hearing on Antitrust Regulations",
            "Supreme Court Landmark Ruling on Privacy Rights",
            "Federal Fiscal Budget and Deficit Projections",
            "Bipartisan Infrastructure and Clean Energy Bill",
            "Immigration Policy Reforms and Border Security",
            "Voting Rights Legislation in Swing Districts",
            "Defense Spending Authorization and Global Alliances",
            "Healthcare Subsidy Expansion and Drug Pricing",
            "State Legislature Tax Incentive Overhauls"
        ],
        "keywords": ["policy", "legislation", "senate", "congress", "governance", "bipartisan", "voters", "reform"]
    },
    "Technology": {
        "topics": [
            "Next-Gen Artificial Intelligence Foundation Models",
            "Quantum Computing Breakthrough in Cryptography",
            "Semiconductor Fabrication and Supply Chain Autonomy",
            "Autonomous Electric Vehicles and LiDAR Sensor Tech",
            "Cybersecurity Zero-Day Vulnerability Mitigations",
            "Cloud Native Infrastructure and Serverless Scaling",
            "Neuromorphic Computing Chips for Edge Devices",
            "Commercial Space Launch Vehicles and Satellite Constellations",
            "Decentralized Data Architectures and Web3 Systems",
            "Augmented Reality Optical Waveguides and Display Hardware"
        ],
        "keywords": ["ai", "chips", "computing", "software", "innovation", "algorithms", "robotics", "cyber"]
    },
    "Economy & Finance": {
        "topics": [
            "Central Bank Benchmark Interest Rate Adjustments",
            "Global Inflation Indices and Consumer Spending Metrics",
            "Sovereign Debt Markets and Treasury Yield Curve",
            "Venture Capital Investments in Renewable Energy",
            "Commodities Supercycle: Crude Oil, Copper, and Lithium",
            "Fintech Digital Payments and Cross-Border Settlements",
            "Corporate Mergers, Acquisitions, and Antitrust Review",
            "Commercial Real Estate Refinancing and Vacancy Rates",
            "Labor Market Participation and Wage Growth Indicators",
            "Stock Market Volatility and Algorithmic Trading Trends"
        ],
        "keywords": ["markets", "gdp", "interest rates", "inflation", "banking", "equities", "treasury", "assets"]
    },
    "Climate & Environment": {
        "topics": [
            "Renewable Grid Integration and Battery Storage Capacity",
            "Carbon Capture Sequestration Facilities and Tax Credits",
            "Arctic Ice Cap Melt Rates and Sea Level Modeling",
            "Ocean Acidification Impact on Marine Ecosystems",
            "Global Reforestation Initiatives and Biodiversity Corridors",
            "Drought Management and Desalination Technologies",
            "Wildfire Mitigation Sensors and Predictive AI Models",
            "Electric Grid Resiliency in Extreme Weather Events",
            "Sustainable Agriculture and Precision Irrigation Systems",
            "Plastics Circular Economy and Biodegradable Polymers"
        ],
        "keywords": ["climate", "emissions", "renewable", "carbon", "ecology", "biodiversity", "conservation", "green"]
    },
    "Healthcare & Science": {
        "topics": [
            "mRNA Cancer Vaccine Clinical Trial Phase III Outcomes",
            "CRISPR Gene Editing for Rare Genetic Disorders",
            "Neurodegenerative Disease Biomarkers in Early Screening",
            "Synthetic Biology and Engineered Microbial Enzymes",
            "Deep Space Telescope Discoveries of Habitable Exoplanets",
            "Nuclear Fusion Energy Net Gain Milestone",
            "Global Pandemic Preparedness and Genomic Surveillance",
            "Bio-compatible Neural Interfaces for Paralysis Rehabilitation",
            "Antibiotic Resistance Countermeasures and Phage Therapy",
            "Stem Cell Regenerative Medicine in Cardiology"
        ],
        "keywords": ["medicine", "clinical", "genetics", "biotech", "neuroscience", "cardiology", "therapeutics", "astrophysics"]
    },
    "World & Diplomacy": {
        "topics": [
            "Multilateral Trade Agreement Negotiations and Tariffs",
            "United Nations General Assembly Climate Accords",
            "Diplomatic Summits in Asia-Pacific Maritime Security",
            "Cross-Border Humanitarian Aid Distribution and Logistics",
            "European Union Regulatory Framework for Data Sovereignty",
            "African Continental Free Trade Area Expansion",
            "Middle East Strategic Energy Corridors and Diplomacy",
            "South American Lithium Triangle Mining Accords",
            "Global Supply Chain Re-shoring and Near-shoring Initiatives",
            "International Court of Justice Maritime Boundary Rulings"
        ],
        "keywords": ["treaty", "allies", "summit", "geopolitics", "diplomacy", "ambassador", "sanctions", "international"]
    }
}

POLITICAL_ALIGNMENTS = [
    {"label": "Left", "weight": 0.22, "sources": ["Progressive Herald", "The Guardian Voice", "Metro Tribune", "Daily Vanguard"]},
    {"label": "Center-Left", "weight": 0.23, "sources": ["Atlantic Post", "Global Monitor", "City Chronicle", "State Sentinel"]},
    {"label": "Center", "weight": 0.20, "sources": ["Reuters Wire", "Associated News Network", "Neutral Observer", "Financial Times Standard"]},
    {"label": "Center-Right", "weight": 0.20, "sources": ["National Review Point", "Market Courier", "Capital Gazette", "The Standard Echo"]},
    {"label": "Right", "weight": 0.15, "sources": ["Liberty Telegraph", "Daily Pioneer", "Federalist Press", "The American Patriot"]}
]

ANGLES = [
    "Comprehensive Analysis and Expert Perspectives",
    "Key Takeaways and Policy Implications for 2026",
    "Special Investigation: What the Data Reveals",
    "A Closer Look at the Strategic and Socio-Economic Tradeoffs",
    "Industry Leaders and Officials Weigh in on Next Steps",
    "Inside the High-Stakes Negotiations and Decision Points",
    "Economic Impact Report: Who Benefits and What Lies Ahead",
    "Global Repercussions and Future Trends"
]

def generate_articles(total_count=10000, output_path="articles_10k.json"):
    print(f"Generating {total_count} synthetic news articles with varied topics and political alignments...")
    random.seed(42)
    articles = []
    
    start_date = datetime.now() - timedelta(days=90)
    
    alignment_labels = [a["label"] for a in POLITICAL_ALIGNMENTS]
    alignment_weights = [a["weight"] for a in POLITICAL_ALIGNMENTS]
    alignment_map = {a["label"]: a["sources"] for a in POLITICAL_ALIGNMENTS}
    
    cat_keys = list(CATEGORIES.keys())
    
    for i in range(1, total_count + 1):
        cat = random.choice(cat_keys)
        topic_info = CATEGORIES[cat]
        topic = random.choice(topic_info["topics"])
        angle = random.choice(ANGLES)
        
        alignment = random.choices(alignment_labels, weights=alignment_weights, k=1)[0]
        source = random.choice(alignment_map[alignment])
        
        # Publish date jitter
        days_offset = random.randint(0, 90)
        pub_date = (start_date + timedelta(days=days_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59))).isoformat()
        
        headline = f"{topic}: {angle}"
        
        # Build contextual snippet & body
        snippet = (
            f"An in-depth report on {topic.lower()} from {source}. "
            f"This piece explores how recent developments in {cat.lower()} affect policy, market dynamics, and public interest from a {alignment.lower()} perspective."
        )
        
        selected_kws = random.sample(topic_info["keywords"], k=min(4, len(topic_info["keywords"])))
        tags = [cat.lower(), alignment.lower()] + selected_kws
        
        content = (
            f"{headline}. {snippet} "
            f"Analysts highlight that {topic.lower()} continues to reshape the landscape across {cat}. "
            f"Key stakeholders emphasize critical tradeoffs involving sustainability, regulatory oversight, and economic viability. "
            f"Further developments will likely determine long-term trajectory and public trust as new data emerges."
        )
        
        articles.append({
            "id": f"art_{i:05d}",
            "article_id": i,
            "title": headline,
            "snippet": snippet,
            "content": content,
            "category": cat,
            "political_alignment": alignment,
            "source": source,
            "published_at": pub_date,
            "tags": tags,
            "reads_count": random.randint(50, 15000),
            "upvotes": random.randint(5, 1200),
            "downvotes": random.randint(0, 300)
        })
        
        if i % 2500 == 0:
            print(f"Generated {i}/{total_count} articles...")
            
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2)
        
    print(f"Successfully generated and saved {len(articles)} articles to {output_path}!")
    return articles

if __name__ == "__main__":
    import sys
    out = "articles_10k.json"
    if len(sys.argv) > 1:
        out = sys.argv[1]
    generate_articles(10000, out)
