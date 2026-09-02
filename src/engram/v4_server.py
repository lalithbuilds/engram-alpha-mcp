import struct
from engram.v4_core import V4MemoryManager, PARTITION_SIZE
from engram.v4_structs import unpack_delta
import time

class V4ZeroMQServer:
    def __init__(self):
        pass 
        
    def start_producer(self, agent_id: int, payloads: list, vectors: list = None):
        mm = V4MemoryManager(agent_id)
        if vectors is None:
            vectors = [[0.0]*384 for _ in payloads]
        for p, v in zip(payloads, vectors):
            mm.write_delta(p, v)
        mm.close()
        
    def consume(self, expected: int):
        mm = V4MemoryManager(99)
        results = []
        processed = 0
        
        while processed < expected:
            for agent_id in range(10): # 10 agents max
                partition_start = agent_id * PARTITION_SIZE
                write_offset, read_offset = struct.unpack_from('ii', mm.shm.buf, partition_start)
                
                while read_offset != write_offset and processed < expected:
                    data_len = struct.unpack_from('i', mm.shm.buf, partition_start + read_offset)[0]
                    if data_len == -1:
                        read_offset = 8
                        struct.pack_into('i', mm.shm.buf, partition_start + 4, read_offset)
                        # CRUCIAL FIX: Re-read write_offset after wrapping!
                        write_offset = struct.unpack_from('i', mm.shm.buf, partition_start)[0]
                        continue
                        
                    raw = bytes(mm.shm.buf[partition_start + read_offset + 4 : partition_start + read_offset + 4 + data_len])
                    
                    # Unpack and verify
                    # Note: unpack_delta parses out the 384-dimensional vector natively!
                    aid, timestamp, vector, payload = unpack_delta(raw)
                    results.append((aid, payload))
                    
                    processed += 1
                    read_offset += 4 + data_len
                    struct.pack_into('i', mm.shm.buf, partition_start + 4, read_offset)
                    write_offset = struct.unpack_from('i', mm.shm.buf, partition_start)[0]
                    
        mm.close()
        return results
