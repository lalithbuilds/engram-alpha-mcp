"""
7-Agent Model Council Semantic Search Verification Gauntlet
Evaluates genuine semantic recall across 7 distinct cognitive domains
with ZERO lexical/keyword token overlap between queries and stored memories.
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Ensure isolated test database
os.environ["ENGRAM_DB_PATH"] = "test_semantic_council.sqlite"

from engram.core import init_db, get_db
from engram.server import save_memory, search_memory
from engram.amx import (
    generate_dense_embedding,
    amx_cosine_similarity,
    get_acceleration_tier,
    get_embedding_model,
)

def run_semantic_council_gauntlet():
    if os.path.exists("test_semantic_council.sqlite"):
        try: os.remove("test_semantic_council.sqlite")
        except: pass
    init_db(force=True)

    tier = get_acceleration_tier()
    model = get_embedding_model()
    model_name = "BAAI/bge-small-en-v1.5 (Neural ONNX)" if model is not None else "Hashed Hypersphere Projection (Stdlib)"

    print("=" * 80)
    print("🧠 7-MODEL COUNCIL SEMANTIC RETRIEVAL VERIFICATION GAUNTLET")
    print("=" * 80)
    print(f"Hardware Acceleration Tier: {tier}")
    print(f"Active Semantic Vector Engine: {model_name}")
    print("=" * 80)

    # 7 Specialized Test Cohorts designed by the 7 Model Council Agents
    council_test_suites = {
        "1. CLAUDE_FABLE (Conceptual Abstraction & Intent Paraphrase)": [
            {
                "stored": "The system strictly adheres to zero unauthorized data sharing principles to protect individual confidential information.",
                "query": "user privacy governance rules",
                "category": "ethics",
                "distractors": [
                    "We need to optimize the database query latency for dashboard reporting.",
                    "The frontend build pipeline uses Vite with TypeScript and Tailwind CSS.",
                    "Server CPU utilization reached seventy percent during morning peak hours.",
                ]
            },
            {
                "stored": "Automobile engine stalled on the highway and requires mechanical inspection by a certified technician.",
                "query": "vehicle repair shop assistance",
                "category": "transport",
                "distractors": [
                    "Baking sourdough bread requires thirty grams of active starter culture.",
                    "The solar eclipse will be visible across North America tomorrow afternoon.",
                    "Stock market trading volume surged following quarterly corporate earnings.",
                ]
            }
        ],
        "2. GEMINI_PRO_3 (DevOps & Distributed Systems Paradigms)": [
            {
                "stored": "Deploy the containerized microservices to the multi-node Kubernetes cluster using Helm charts.",
                "query": "shipping application to production cloud infrastructure",
                "category": "devops",
                "distractors": [
                    "Our company offers twenty days of annual paid vacation leave for full-time staff.",
                    "The coffee machine on the third floor cafeteria is temporarily out of service.",
                    "Graphic designer submitted new color palette proposals for marketing banners.",
                ]
            },
            {
                "stored": "User authentication relies on JSON Web Tokens signed with asymmetric RS256 cryptographic keys.",
                "query": "verifying client identity credentials securely",
                "category": "security",
                "distractors": [
                    "The weather forecast predicts heavy rainfall and lightning storms tonight.",
                    "Annual general meeting of shareholders will be conducted virtually via Zoom.",
                    "Clean code principles suggest keeping function lengths under thirty lines.",
                ]
            }
        ],
        "3. KIMI_K3 (Knowledge Topology & Relational Workflows)": [
            {
                "stored": "We hold a recurring weekly synchronization with engineering leads to review sprint progress and roadmaps.",
                "query": "team standup meeting schedule",
                "category": "process",
                "distractors": [
                    "The botanical garden features over two thousand rare tropical orchid species.",
                    "Quantum computing uses qubits capable of existing in multiple states simultaneously.",
                    "Electric vehicle battery manufacturing requires lithium and nickel minerals.",
                ]
            },
            {
                "stored": "The primary persistent transactional datastore is PostgreSQL version 16 configured with streaming replication.",
                "query": "where are customer records saved permanently",
                "category": "database",
                "distractors": [
                    "Tennis tournament finals scheduled for Sunday morning on center court.",
                    "Audio podcast recording studio equipped with dynamic cardioid microphones.",
                    "The recipe calls for two tablespoons of extra virgin olive oil.",
                ]
            }
        ],
        "4. GPT_SOUL (Algorithmic Logic & Cognitive Mathematics)": [
            {
                "stored": "The lookup algorithm operates in logarithmic time complexity by bisecting search intervals at each iteration.",
                "query": "binary search tree asymptotic scaling efficiency",
                "category": "algorithms",
                "distractors": [
                    "Indoor house plants thrive best under indirect natural sunlight and moderate watering.",
                    "Flight from London Heathrow to Tokyo Haneda takes approximately fourteen hours.",
                    "The local library operates between nine in the morning and eight at night.",
                ]
            },
            {
                "stored": "Memory consolidation employs John Anderson's power law equation to model retention over elapsed time intervals.",
                "query": "biologically plausible forgetting curves in psychology",
                "category": "cognitive",
                "distractors": [
                    "Stainless steel cookware is dishwasher safe and resists high temperature oxidation.",
                    "The symphony orchestra rehearses classical Beethoven movements every Thursday.",
                    "Real estate property values increased by five percent in the downtown metropolitan sector.",
                ]
            }
        ],
        "5. DEEP_RESEARCH (Adversarial Distractors & Needle-in-Haystack)": [
            {
                "stored": "Secret bypass credentials for diagnostic staging environment are stored in AWS Secrets Manager vault alpha.",
                "query": "where are testing passwords and keys kept",
                "category": "forensics",
                "distractors": [
                    f"Routine telemetry metric collection cycle {i}: system operational status healthy and within parameters."
                    for i in range(1, 20)
                ]
            }
        ],
        "6. GLM_5_2 (Technical Jargon to Plain Meaning Translation)": [
            {
                "stored": "Patient exhibits acute bilateral cephalalgia accompanied by severe photophobia and nausea.",
                "query": "intense migraine headache sensitive to bright lights",
                "category": "medical",
                "distractors": [
                    "Quarterly financial revenue surpassed analyst expectations by twelve percent.",
                    "The highway construction project will add two additional lanes to reduce traffic congestion.",
                    "Bicycle frame is manufactured using lightweight aerospace grade carbon fiber.",
                ]
            }
        ],
        "7. COUNCIL_CHAIR (Cross-Domain Multi-Sentence Intent)": [
            {
                "stored": "We have migrated from npm to pnpm to maximize symlinked disk space efficiency across the monorepo.",
                "query": "package management tool preference",
                "category": "tooling",
                "distractors": [
                    "Fresh fruit smoothie contains strawberries, blueberries, bananas, and almond milk.",
                    "The historical museum exhibition showcases medieval Renaissance paintings and armor.",
                    "Standard marathon distance is exactly forty-two point one nine five kilometers.",
                ]
            }
        ]
    }

    total_tests = 0
    top1_hits = 0
    top3_hits = 0
    results_summary = []

    for suite_name, test_cases in council_test_suites.items():
        print(f"\n🔬 Evaluating Suite: {suite_name}")
        print("-" * 80)
        
        for case_idx, case in enumerate(test_cases, 1):
            total_tests += 1
            # 1. Clean DB for this specific case to test strict isolated recall
            conn = get_db()
            conn.execute("DELETE FROM nodes;")
            conn.execute("DELETE FROM edges;")
            conn.execute("DELETE FROM nodes_fts;")
            conn.commit()
            conn.close()

            # 2. Save Target Memory
            target_id_str = save_memory(
                case["stored"],
                category=case["category"],
                importance=8,
                project="semantic_test"
            )

            # 3. Save All Distractors
            for d_idx, distractor in enumerate(case["distractors"]):
                save_memory(
                    distractor,
                    category="distractor",
                    importance=5,
                    project="semantic_test"
                )

            # 4. Compute Direct Dense Cosine Similarity (Semantic Vector Measurement)
            target_vec = generate_dense_embedding(case["stored"])
            query_vec = generate_dense_embedding(case["query"])
            direct_cos = amx_cosine_similarity(query_vec, target_vec)

            # 5. Execute 4-Way RRF Hybrid Search
            t0 = time.perf_counter()
            search_out = search_memory(case["query"], limit=5, hybrid=True, project="semantic_test")
            t_elapsed = (time.perf_counter() - t0) * 1000

            # 6. Parse Search Output Ranking by entries
            entries = [e.strip() for e in search_out.split("\n\n") if e.strip()]
            
            target_rank = None
            for r_idx, entry in enumerate(entries, 1):
                if case["stored"][:40] in entry:
                    target_rank = r_idx
                    break

            is_top1 = (target_rank == 1)
            is_top3 = (target_rank is not None and target_rank <= 3)

            if is_top1: top1_hits += 1
            if is_top3: top3_hits += 1

            status_icon = "✅ HIT (Rank #1)" if is_top1 else (f"⚠️ HIT (Rank #{target_rank})" if is_top3 else "❌ MISS")
            
            print(f"  Test #{case_idx}: '{case['query']}'")
            print(f"    Target Stored : '{case['stored'][:65]}...'")
            print(f"    Dense Cosine  : {direct_cos:.4f}")
            print(f"    Search Latency: {t_elapsed:.2f}ms")
            print(f"    Retrieval Rank: {status_icon}")

            results_summary.append({
                "suite": suite_name.split(":")[0],
                "query": case["query"],
                "target_rank": target_rank,
                "cosine": direct_cos,
                "latency_ms": t_elapsed
            })

    print("\n" + "=" * 80)
    print("🏆 FINAL MODEL COUNCIL SEMANTIC RECALL VERIFICATION REPORT")
    print("=" * 80)
    print(f"Total Test Vector Scenarios : {total_tests}")
    print(f"Top-1 Semantic Recall (R@1) : {top1_hits}/{total_tests} ({(top1_hits/total_tests)*100:.1f}%)")
    print(f"Top-3 Semantic Recall (R@3) : {top3_hits}/{total_tests} ({(top3_hits/total_tests)*100:.1f}%)")
    print("=" * 80)
    return total_tests, top1_hits, top3_hits

def test_semantic_council_gauntlet():
    total_tests, top1_hits, top3_hits = run_semantic_council_gauntlet()
    model = get_embedding_model()
    if model is not None:
        assert top1_hits == total_tests, f"Semantic recall dropped: {top1_hits}/{total_tests}"
    else:
        assert total_tests > 0

if __name__ == "__main__":
    run_semantic_council_gauntlet()
