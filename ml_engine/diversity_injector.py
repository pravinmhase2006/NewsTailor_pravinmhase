import numpy as np

class DiversityInjector:
    def __init__(self, target_entropy=0.72, max_topic_dominance=0.45):
        self.target_entropy = target_entropy
        self.max_topic_dominance = max_topic_dominance

    def inject_diversity(self, hybrid_candidates, lda_modeler, articles_map, slate_size=10):
        """
        Actively monitors topics & political bias in top candidate slate.
        If the slate falls into a filter bubble (entropy < target or dominance > threshold),
        forcibly injects high-quality articles from underrepresented / opposing topics.
        """
        if not hybrid_candidates:
            return [], 0.0, False, "Empty candidates"

        # Start with the pure Top-K candidates
        current_slate = [dict(c) for c in hybrid_candidates[:slate_size]]
        for item in current_slate:
            item["is_injected"] = False
            item["injected_reason"] = None

        slate_ids = [c["article_id"] for c in current_slate]
        initial_entropy, initial_topic_probs = lda_modeler.calculate_slate_entropy(slate_ids)
        
        # Check topic concentration
        max_topic_prob = max(initial_topic_probs) if initial_topic_probs else 0
        needs_injection = (initial_entropy < self.target_entropy) or (max_topic_prob > self.max_topic_dominance)
        
        if not needs_injection:
            return current_slate, round(initial_entropy, 4), False, "Feed already diverse (Entropy >= 0.70)"

        # Pool of reserve candidates (from rank slate_size onwards)
        reserve_pool = [dict(c) for c in hybrid_candidates[slate_size:]]
        
        # Determine dominant political alignment
        alignments = [articles_map.get(cid, {}).get("political_alignment", "Center") for cid in slate_ids]
        dominant_align = max(set(alignments), key=alignments.count) if alignments else "Center"
        
        # Map opposing alignments
        opposing_alignments = {
            "Left": ["Center-Right", "Right", "Center"],
            "Center-Left": ["Right", "Center-Right", "Center"],
            "Right": ["Center-Left", "Left", "Center"],
            "Center-Right": ["Left", "Center-Left", "Center"],
            "Center": ["Left", "Right"]
        }.get(dominant_align, ["Center"])

        # Determine underrepresented topics
        underrepresented_topics = [
            t_idx for t_idx, p in enumerate(initial_topic_probs) if p < (1.0 / lda_modeler.n_topics)
        ]

        mitigation_applied = False
        iteration = 0
        max_injections = 4 # Inject up to 4 items out of 10 to balance relevance with diversity

        while iteration < max_injections:
            current_ids = [c["article_id"] for c in current_slate]
            curr_entropy, curr_probs = lda_modeler.calculate_slate_entropy(current_ids)
            
            if curr_entropy >= self.target_entropy and max(curr_probs) <= (self.max_topic_dominance + 0.05):
                break

            # Find best reserve article from underrepresented topic or opposing viewpoint
            best_candidate_idx = None
            candidate_reason = None

            for r_idx, r_item in enumerate(reserve_pool):
                r_id = r_item["article_id"]
                r_art = articles_map.get(r_id, {})
                r_dom_topic = lda_modeler.article_dominant_topic.get(r_id)
                r_align = r_art.get("political_alignment", "Center")

                if r_dom_topic in underrepresented_topics and r_align in opposing_alignments:
                    best_candidate_idx = r_idx
                    candidate_reason = f"Diversity Injected: Balanced {r_art.get('category')} ({r_align}) from underrepresented Topic {r_dom_topic}"
                    break
                elif r_dom_topic in underrepresented_topics:
                    best_candidate_idx = r_idx
                    candidate_reason = f"Diversity Injected: Broadened topic exposure ({r_art.get('category')}, Topic {r_dom_topic})"
                    break
                elif r_align in opposing_alignments:
                    best_candidate_idx = r_idx
                    candidate_reason = f"Diversity Injected: Counter-perspective ({r_align} angle on {r_art.get('category')})"
                    break

            if best_candidate_idx is not None:
                injected_article = reserve_pool.pop(best_candidate_idx)
                injected_article["is_injected"] = True
                injected_article["injected_reason"] = candidate_reason

                # Replace the lowest-scoring non-injected item that belongs to the most dominant topic
                dominant_topic = int(np.argmax(curr_probs))
                replaceable_idx = None

                for s_idx in range(len(current_slate) - 1, -1, -1):
                    item = current_slate[s_idx]
                    if not item.get("is_injected", False):
                        item_topic = lda_modeler.article_dominant_topic.get(item["article_id"])
                        if item_topic == dominant_topic:
                            replaceable_idx = s_idx
                            break

                if replaceable_idx is None:
                    # Fallback to replacing lowest scoring non-injected item
                    for s_idx in range(len(current_slate) - 1, -1, -1):
                        if not current_slate[s_idx].get("is_injected", False):
                            replaceable_idx = s_idx
                            break

                if replaceable_idx is not None:
                    current_slate[replaceable_idx] = injected_article
                    mitigation_applied = True
                else:
                    break
            else:
                break

            iteration += 1

        final_ids = [c["article_id"] for c in current_slate]
        final_entropy, final_probs = lda_modeler.calculate_slate_entropy(final_ids)
        
        status_msg = (
            f"Filter bubble mitigated: Injected {iteration} diverse articles. "
            f"Diversity Entropy increased from {initial_entropy:.3f} to {final_entropy:.3f} (>0.70 achieved)"
            if mitigation_applied else f"Feed diversity score: {final_entropy:.3f}"
        )

        return current_slate, round(final_entropy, 4), mitigation_applied, status_msg
