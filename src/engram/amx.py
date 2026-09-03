import sys
import math
import struct
import os
import ctypes
import threading
from typing import List

try:
    import numpy as np
except ImportError:
    np = None

_BLAS_LIB = None
_cblas_sdot = None
_cblas_snrm2 = None

def _init_cblas():
    global _BLAS_LIB, _cblas_sdot, _cblas_snrm2
    try:
        if sys.platform == "darwin":
            _BLAS_LIB = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/Accelerate.framework/Accelerate")
        elif sys.platform.startswith("linux"):
            _BLAS_LIB = ctypes.cdll.LoadLibrary("libopenblas.so.0")
        elif sys.platform == "win32":
            _BLAS_LIB = ctypes.cdll.LoadLibrary("mkl_rt.dll")
    except Exception:
        pass

    if _BLAS_LIB is not None:
        try:
            _cblas_sdot = _BLAS_LIB.cblas_sdot
            _cblas_sdot.argtypes = [
                ctypes.c_int,
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_int,
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_int,
            ]
            _cblas_sdot.restype = ctypes.c_float

            _cblas_snrm2 = _BLAS_LIB.cblas_snrm2
            _cblas_snrm2.argtypes = [
                ctypes.c_int,
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_int,
            ]
            _cblas_snrm2.restype = ctypes.c_float
        except Exception:
            _cblas_sdot = None
            _cblas_snrm2 = None

_init_cblas()

EMBEDDING_DIM = int(os.environ.get("ENGRAM_EMBEDDING_DIM", "384"))

def compute_similarity_pure_python(vec_a: List[float], vec_b: List[float]) -> float:
    try:
        dot = sum(x * y for x, y in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(x * x for x in vec_a))
        norm_b = math.sqrt(sum(y * y for y in vec_b))
        if norm_a == 0.0 or norm_b == 0.0 or math.isnan(norm_a) or math.isnan(norm_b):
            return 0.0
        val = float(dot / (norm_a * norm_b))
        return 0.0 if (math.isnan(val) or math.isinf(val)) else val
    except Exception:
        return 0.0

def amx_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    n = len(vec_a)
    if n == 0 or len(vec_b) != n:
        return 0.0

    if _cblas_sdot is not None and _cblas_snrm2 is not None:
        try:
            arr_a = (ctypes.c_float * n)(*vec_a)
            arr_b = (ctypes.c_float * n)(*vec_b)
            dot = _cblas_sdot(n, arr_a, 1, arr_b, 1)
            norm_a = _cblas_snrm2(n, arr_a, 1)
            norm_b = _cblas_snrm2(n, arr_b, 1)
            if norm_a == 0.0 or norm_b == 0.0 or math.isnan(norm_a) or math.isnan(norm_b):
                return 0.0
            val = float(dot / (norm_a * norm_b))
            return 0.0 if (math.isnan(val) or math.isinf(val)) else val
        except Exception:
            pass

    if np is not None:
        try:
            a = np.array(vec_a, dtype=np.float32)
            b = np.array(vec_b, dtype=np.float32)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(np.dot(a, b) / (norm_a * norm_b))
        except Exception:
            pass

    return compute_similarity_pure_python(vec_a, vec_b)

def amx_batch_cosine_similarity(
    query_vec: List[float], candidate_matrix: List[List[float]]
) -> List[float]:
    if not candidate_matrix or not query_vec:
        return []

    # Fix: dispatch to C-BLAS if available (was missing previously)
    if _cblas_sdot is not None and _cblas_snrm2 is not None and np is None:
        try:
            n = len(query_vec)
            q_arr = (ctypes.c_float * n)(*query_vec)
            q_norm = _cblas_snrm2(n, q_arr, 1)
            scores = []
            if q_norm == 0.0:
                return [0.0] * len(candidate_matrix)
            for cand in candidate_matrix:
                c_arr = (ctypes.c_float * n)(*cand)
                c_norm = _cblas_snrm2(n, c_arr, 1)
                if c_norm == 0.0:
                    scores.append(0.0)
                else:
                    dot = _cblas_sdot(n, q_arr, 1, c_arr, 1)
                    scores.append(float(dot / (q_norm * c_norm)))
            return scores
        except Exception:
            pass

    if np is not None:
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

            scores = np.dot(mat_unit, q_unit)
            return scores.tolist()
        except Exception:
            pass

    return [compute_similarity_pure_python(query_vec, cand) for cand in candidate_matrix]

_EMBEDDING_MODEL = None
_EMBEDDING_LOCK = threading.Lock()
_FASTEMBED_PROBED = False
_EMBEDDING_PID = None

def get_embedding_model():
    global _EMBEDDING_MODEL, _FASTEMBED_PROBED, _EMBEDDING_PID
    
    current_pid = os.getpid()
    
    # CRUCIAL FIX: Reset lock if fork detected, to prevent fork/mutex deadlock
    if _EMBEDDING_PID != current_pid:
        _EMBEDDING_MODEL = None
        _FASTEMBED_PROBED = False
        _EMBEDDING_PID = current_pid
        if _EMBEDDING_LOCK.locked():
            try:
                _EMBEDDING_LOCK.release()
            except RuntimeError:
                pass

    if _FASTEMBED_PROBED and _EMBEDDING_MODEL is None:
        return None
        
    if _EMBEDDING_MODEL is None:
        with _EMBEDDING_LOCK:
            if _EMBEDDING_MODEL is None and not _FASTEMBED_PROBED:
                try:
                    os.environ["OMP_NUM_THREADS"] = "1"
                    os.environ["TOKENIZERS_PARALLELISM"] = "false"
                    sys.stderr.write("[engram] Initializing local embedding engine (BAAI/bge-small-en-v1.5)...\n")
                    sys.stderr.flush()
                    from fastembed import TextEmbedding
                    _EMBEDDING_MODEL = TextEmbedding(model_name="BAAI/bge-small-en-v1.5", threads=1)
                    sys.stderr.write("[engram] Local embedding engine ready.\n")
                    sys.stderr.flush()
                except Exception as e:
                    sys.stderr.write(f"[engram] FastEmbed unavailable ({e}), using deterministic fallback.\n")
                    sys.stderr.flush()
                    _EMBEDDING_MODEL = None
                finally:
                    _FASTEMBED_PROBED = True
    return _EMBEDDING_MODEL

def _deterministic_fallback(text: str, dim: int) -> List[float]:
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

def generate_dense_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    model = get_embedding_model()
    if model is not None:
        try:
            gen = model.embed([text])
            embeddings = list(gen)
            return [float(x) for x in embeddings[0]]
        except Exception:
            pass
    return _deterministic_fallback(text, dim)

def pack_vector(vec: List[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)

def unpack_vector(blob: bytes, dim: int = EMBEDDING_DIM) -> List[float]:
    if not blob:
        return [0.0] * dim
    try:
        valid_len = (len(blob) // 4) * 4
        count = valid_len // 4
        if count == 0:
            return [0.0] * dim
        unpacked = list(struct.unpack(f"{count}f", blob[:valid_len]))
        return [0.0 if (math.isnan(x) or math.isinf(x)) else x for x in unpacked]
    except Exception:
        return [0.0] * dim

def generate_dense_embeddings_batch(texts: List[str], dim: int = EMBEDDING_DIM) -> List[List[float]]:
    if not texts:
        return []
    model = get_embedding_model()
    if model is not None:
        try:
            gen = model.embed(texts)
            embeddings = list(gen)
            return [[float(x) for x in emb] for emb in embeddings]
        except Exception:
            pass
    return [_deterministic_fallback(t, dim) for t in texts]

def is_amx_hardware_available() -> bool:
    return _cblas_sdot is not None

def get_acceleration_tier() -> str:
    if _cblas_sdot is not None:
        if sys.platform == "darwin":
            return "Tier 1: Apple Silicon AMX (Accelerate.framework)"
        else:
            return f"Tier 1: Native C-BLAS Hardware Acceleration ({sys.platform})"
    elif np is not None:
        return f"Tier 2: Universal NumPy BLAS ({sys.platform})"
    else:
        return "Tier 3: Pure Python Standard Library (Zero-Dependency Universal)"
