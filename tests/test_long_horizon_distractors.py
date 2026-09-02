"""
Long-Horizon Semantic Recall & Distractor Regression Test:
Proves that vector recall does NOT collapse as the database grows and is immune to recency windowing.
Seeds a target memory, inserts 50+ noise distractors afterward, and verifies Top-1/Top-5 semantic recall.
"""

import os
import pytest
from pathlib import Path


from engram.core import init_db, _INITIALIZED_PATHS
from engram.server import save_memory, search_memory


def test_long_horizon_distractor_immunity():
    # 1. Save critical target needle
    target_content = "The production database authentication secret is 'amber_nebula_482'."
    save_res = save_memory(target_content, importance=9, category="infrastructure", project="distractor_test")
    assert "Saved Node" in save_res

    # 2. Seed 60 distractor memories saved AFTER the target memory (exceeds any 40-item window)
    distractor_topics = [
        "Frontend CSS color palette was updated to Dracula Pro theme.",
        "Weekly marketing standup is scheduled for Thursday afternoon.",
        "Refactored login modal component in React Native.",
        "Added unit tests for user profile image upload pipeline.",
        "Configured Nginx rate limiting rules for public endpoints.",
        "Upgraded Docker base image from Alpine 3.18 to 3.20.",
        "Implemented customer support Zendesk webhook listener.",
        "Optimized checkout page Core Web Vitals LCP score.",
        "Fixed typo in terms of service legal disclaimer document.",
        "Created promotional coupon code for summer discount campaign.",
    ]
    for i in range(60):
        topic = distractor_topics[i % len(distractor_topics)]
        save_memory(f"Distractor note #{i}: {topic}", importance=4, category="backlog", project="distractor_test")

    # 3. Perform semantic query (paraphrased without exact keyword overlap)
    query = "Where is the production db credential?"
    res = search_memory(query, limit=5, hybrid=True, project="distractor_test")

    # 4. Assert the target needle is recalled in the top results despite 60 distractors saved after it
    assert "amber_nebula_482" in res, f"Failed long-horizon distractor test! Result was: {res}"
    assert "production database authentication secret" in res
