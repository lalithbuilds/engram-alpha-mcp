import struct
import time

def pack_delta(agent_id: int, payload: str) -> bytes:
    payload_bytes = payload.encode('utf-8')
    fmt = f"=id{len(payload_bytes)}s"
    return struct.pack(fmt, agent_id, time.time(), payload_bytes)

def unpack_delta(data: bytes) -> tuple:
    payload_len = len(data) - 12
    fmt = f"=id{payload_len}s"
    agent_id, timestamp, payload_bytes = struct.unpack(fmt, data)
    return agent_id, timestamp, payload_bytes.decode('utf-8')
