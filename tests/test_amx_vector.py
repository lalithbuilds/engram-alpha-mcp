"""
Tests for Engram AMX Hardware Vector Engine
"""

import pytest
import math
from engram.amx import (
    is_amx_hardware_available,
    pack_vector,
    unpack_vector,
    amx_cosine_similarity,
    amx_batch_cosine_similarity,
    generate_dense_embedding,
)

def test_hardware_availability():
    # Apple Silicon should report True for Accelerate cblas_sdot
    available = is_amx_hardware_available()
    print(f"AMX Hardware Available: {available}")
    assert isinstance(available, bool)

def test_pack_unpack_vector():
    vec = [0.1, -0.5, 0.999, 12.345, 0.0]
    blob = pack_vector(vec)
    assert len(blob) == len(vec) * 4
    unpacked = unpack_vector(blob)
    assert len(unpacked) == len(vec)
    for a, b in zip(vec, unpacked):
        assert abs(a - b) < 1e-5

def test_amx_cosine_similarity():
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    vec_c = [0.0, 1.0, 0.0]
    vec_d = [-1.0, 0.0, 0.0]

    # Identical
    assert abs(amx_cosine_similarity(vec_a, vec_b) - 1.0) < 1e-4
    # Orthogonal
    assert abs(amx_cosine_similarity(vec_a, vec_c) - 0.0) < 1e-4
    # Opposite
    assert abs(amx_cosine_similarity(vec_a, vec_d) - (-1.0)) < 1e-4

def test_amx_batch_cosine_similarity():
    query = [1.0, 0.0, 0.0]
    matrix = [
        [1.0, 0.0, 0.0],  # 1.0
        [0.0, 1.0, 0.0],  # 0.0
        [0.7071, 0.7071, 0.0],  # ~0.7071
        [-1.0, 0.0, 0.0], # -1.0
    ]
    scores = amx_batch_cosine_similarity(query, matrix)
    assert len(scores) == 4
    assert abs(scores[0] - 1.0) < 1e-3
    assert abs(scores[1] - 0.0) < 1e-3
    assert abs(scores[2] - 0.7071) < 1e-2
    assert abs(scores[3] - (-1.0)) < 1e-3

def test_dense_embedding_generation():
    text1 = "Engram memory architecture on Apple Silicon"
    text2 = "Engram memory architecture on Apple Silicon"
    text3 = "Completely unrelated quantum astrophysics concept"

    v1 = generate_dense_embedding(text1)
    v2 = generate_dense_embedding(text2)
    v3 = generate_dense_embedding(text3)

    assert len(v1) == 384
    assert len(v2) == 384
    assert len(v3) == 384

    # Identical texts yield identical vectors
    sim_identical = amx_cosine_similarity(v1, v2)
    assert abs(sim_identical - 1.0) < 1e-4

    # Different texts yield lower similarity
    sim_diff = amx_cosine_similarity(v1, v3)
    assert sim_diff < 0.95
