import struct
import time

# V4 Delta-CRDT Struct definitions

def pack_delta(agent_id: int, payload: str) -> bytes:
    """Packs a CRDT delta into a C-aligned struct."""
    payload_bytes = payload.encode('utf-8')
    # id(4 bytes), timestamp(8 bytes), payload(variable)
    fmt = f"id{len(payload_bytes)}s"
    return struct.pack(fmt, agent_id, time.time(), payload_bytes)

def unpack_delta(data: bytes) -> tuple:
    """Unpacks a C-aligned CRDT delta from bytes."""
    payload_len = len(data) - 12 # 4 (int) + 8 (double)
    fmt = f"id{payload_len}s"
    agent_id, timestamp, payload_bytes = struct.unpack(fmt, data)
    return agent_id, timestamp, payload_bytes.decode('utf-8')
