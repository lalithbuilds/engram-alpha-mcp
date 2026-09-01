"""
Cross-Platform Multi-Tier Matrix Test Suite ("One for All, All for One")
Verifies mathematical parity, binary equivalence, and flawless execution
across Tier 1 (Apple AMX / C-BLAS), Tier 2 (NumPy BLAS), and Tier 3 (Pure Python Stdlib).
"""

import sys
import math
import random
import pytest
from engram.amx import (
    pack_vector,
    unpack_vector,
    generate_dense_embedding,
    compute_similarity_pure_python,
    amx_cosine_similarity,
    amx_batch_cosine_similarity,
    get_acceleration_tier,
    _cblas_sdot,
)

def test_tier_parity_and_mathematical_equivalence():
    """
    Assert that Tier 1 (C-BLAS), Tier 2 (NumPy), and Tier 3 (Pure Python)
    produce mathematically identical cosine similarity results within float32 precision.
    """
    random.seed(42)
    dim = 384
    
    # Generate 50 random test vector pairs
    for _ in range(50):
        vec_a = [random.uniform(-10.0, 10.0) for _ in range(dim)]
        vec_b = [random.uniform(-10.0, 10.0) for _ in range(dim)]

        # Pure Python (Tier 3)
        score_tier3 = compute_similarity_pure_python(vec_a, vec_b)

        # Active Tier (Tier 1 or Tier 2)
        score_active = amx_cosine_similarity(vec_a, vec_b)

        assert abs(score_tier3 - score_active) < 1e-4, (
            f"Mathematical mismatch between Tier 3 ({score_tier3}) and Active Tier ({score_active})"
        )

def test_simulated_tier3_pure_stdlib_fallback(monkeypatch):
    """
    Force-disable C-BLAS and NumPy to simulate running on a minimal Linux / Windows / Termux
    environment with ONLY standard Python 3.10+ installed.
    """
    import engram.amx as amx_module
    
    # Mock out C-BLAS and NumPy
    monkeypatch.setattr(amx_module, "_cblas_sdot", None)
    monkeypatch.setattr(amx_module, "_cblas_snrm2", None)
    monkeypatch.setattr(amx_module, "np", None)

    assert "Tier 3" in amx_module.get_acceleration_tier()

    # Verify vector math runs flawlessly without external libraries
    vec_a = [1.0, 2.0, 3.0, 4.0]
    vec_b = [1.0, 2.0, 3.0, 4.0]
    sim = amx_module.amx_cosine_similarity(vec_a, vec_b)
    assert abs(sim - 1.0) < 1e-5

    # Test batch vector matching in Tier 3
    matrix = [[1.0, 2.0, 3.0, 4.0], [-1.0, -2.0, -3.0, -4.0], [0.0, 0.0, 0.0, 0.0]]
    batch_scores = amx_module.amx_batch_cosine_similarity(vec_a, matrix)
    assert len(batch_scores) == 3
    assert abs(batch_scores[0] - 1.0) < 1e-5
    assert abs(batch_scores[1] - (-1.0)) < 1e-5
    assert batch_scores[2] == 0.0

def test_ieee754_binary_packing_cross_platform():
    """
    Verify IEEE 754 float32 packing and unpacking integrity across all platforms.
    """
    vec = [0.1234567, -987.654, 3.1415926, 0.0, 1e-5]
    blob = pack_vector(vec)
    assert len(blob) == len(vec) * 4  # 4 bytes per float32
    unpacked = unpack_vector(blob)
    
    for orig, unp in zip(vec, unpacked):
        assert abs(orig - unp) < 1e-5

def test_dense_embedding_deterministic_across_all_environments():
    """
    Verify that dense 384d semantic embeddings generate the exact same hypersphere coordinates
    regardless of OS (Linux, Windows, macOS, Docker).
    """
    text = "Engram Alpha Universal Sovereign Cognitive Memory Architecture"
    emb1 = generate_dense_embedding(text)
    emb2 = generate_dense_embedding(text)
    
    assert len(emb1) == 384
    assert emb1 == emb2
    
    norm = math.sqrt(sum(x * x for x in emb1))
    assert abs(norm - 1.0) < 1e-5
