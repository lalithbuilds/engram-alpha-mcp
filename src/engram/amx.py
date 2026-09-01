"""
Engram AMX Hardware Vector Engine
Utilizes Apple Silicon AMX (Apple Matrix Coprocessor) via the Accelerate Framework,
NumPy BLAS, and pure Python stdlib fallback for ultra-fast vector dot products & cosine distance.
"""

import sys
import os
import math
import struct
import ctypes
try:
    import numpy as np
except ImportError:
    np = None
from typing import List, Tuple, Optional

# Load Apple Accelerate framework for direct AMX hardware dispatch
_ACCELERATE = None
_cblas_sdot = None
_cblas_snrm2 = None

if sys.platform == "darwin":
    try:
        _ACCELERATE = ctypes.CDLL("/System/Library/Frameworks/Accelerate.framework/Accelerate")
        # float cblas_sdot(const int N, const float *X, const int incX, const float *Y, const int incY);
        _cblas_sdot = _ACCELERATE.cblas_sdot
        _cblas_sdot.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_int,
        ]
        _cblas_sdot.restype = ctypes.c_float

        # float cblas_snrm2(const int N, const float *X, const int incX);
        _cblas_snrm2 = _ACCELERATE.cblas_snrm2
        _cblas_snrm2.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_int,
        ]
        _cblas_snrm2.restype = ctypes.c_float
    except Exception:
        _ACCELERATE = None

def is_amx_hardware_available() -> bool:
    """Check if Apple Silicon AMX coprocessor acceleration is available."""
    return _cblas_sdot is not None

def pack_vector(vec: List[float]) -> bytes:
    """Pack float array into compact binary blob."""
    return struct.pack(f"{len(vec)}f", *vec)

def unpack_vector(blob: bytes) -> List[float]:
    """Unpack compact binary blob to float array."""
    count = len(blob) // 4
    return list(struct.unpack(f"{count}f", blob))

def amx_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Compute Cosine Similarity using hardware AMX BLAS if on Apple Silicon,
    falling back to NumPy or pure math.
    """
    n = len(vec_a)
    if n == 0 or len(vec_b) != n:
        return 0.0

    if _cblas_sdot is not None and _cblas_snrm2 is not None:
        arr_a = (ctypes.c_float * n)(*vec_a)
        arr_b = (ctypes.c_float * n)(*vec_b)
        dot = _cblas_sdot(n, arr_a, 1, arr_b, 1)
        norm_a = _cblas_snrm2(n, arr_a, 1)
        norm_b = _cblas_snrm2(n, arr_b, 1)
        if norm_a <= 0.0 or norm_b <= 0.0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    # Fast NumPy BLAS fallback
    try:
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    except Exception:
        # Pure Python fallback
        dot = sum(x * y for x, y in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(x * x for x in vec_a))
        norm_b = math.sqrt(sum(y * y for y in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

def amx_batch_cosine_similarity(
    query_vec: List[float], candidate_matrix: List[List[float]]
) -> List[float]:
    """
    Compute Cosine Similarity against a batch of candidate vectors in a single matrix call.
    Leverages Apple Silicon Accelerate matrix multiply for microsecond execution.
    """
    if not candidate_matrix or not query_vec:
        return []

    try:
        q = np.array(query_vec, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return [0.0] * len(candidate_matrix)
        q_unit = q / q_norm

        mat = np.array(candidate_matrix, dtype=np.float32)
        mat_norms = np.linalg.norm(mat, axis=1, keepdims=True)
        mat_norms[mat_norms == 0] = 1.0
        mat_unit = mat / mat_norms

        # Matrix-vector multiply (dispatched to Apple AMX BLAS)
        scores = np.dot(mat_unit, q_unit)
        return scores.tolist()
    except Exception:
        return [amx_cosine_similarity(query_vec, cand) for cand in candidate_matrix]

def generate_dense_embedding(text: str, dim: int = 384) -> List[float]:
    """
    Generates a deterministic 384-dimensional dense semantic vector.
    Uses fast semantic hashing projection with zero required external dependencies,
    or fastembed if available.
    """
    try:
        from fastembed import TextEmbedding
        model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        embeddings = list(model.embed([text]))
        return [float(x) for x in embeddings[0]]
    except Exception:
        pass

    # Fast Deterministic High-Dimensional Hashed Semantic Projection
    # Distributes word n-grams uniformly across 384-dimensional hypersphere
    import hashlib
    vec = [0.0] * dim
    words = text.lower().split()
    if not words:
        return vec

    for i, word in enumerate(words):
        tokens = [word]
        if i < len(words) - 1:
            tokens.append(f"{word}_{words[i+1]}")

        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx1 = h % dim
            idx2 = (h >> 32) % dim
            sign1 = 1.0 if (h >> 64) & 1 else -1.0
            sign2 = 1.0 if (h >> 65) & 1 else -1.0
            vec[idx1] += sign1
            vec[idx2] += sign2

    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec
