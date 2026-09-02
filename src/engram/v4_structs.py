import struct
import time
from typing import List

# 4 bytes (int) + 8 bytes (double) + 384 * 4 bytes (floats) = 1548 bytes fixed header
FIXED_HEADER_FMT = "=id1536s"

def pack_delta(agent_id: int, payload: str, vector: List[float]) -> bytes:
    payload_bytes = payload.encode('utf-8')
    vec_bytes = struct.pack("384f", *vector)
    
    # 4 byte len of payload + payload_bytes
    fmt = f"=id1536si{len(payload_bytes)}s"
    return struct.pack(fmt, agent_id, time.time(), vec_bytes, len(payload_bytes), payload_bytes)

def unpack_delta(data: bytes) -> tuple:
    agent_id, timestamp, vec_bytes, payload_len = struct.unpack_from("=id1536si", data, 0)
    payload_bytes = struct.unpack_from(f"={payload_len}s", data, 1552)[0]
    vector = list(struct.unpack("384f", vec_bytes))
    return agent_id, timestamp, vector, payload_bytes.decode('utf-8')
