import struct
from src.engram.v4_core import V4MemoryManager, PARTITION_SIZE
from src.engram.v4_structs import unpack_delta

class V4ZeroMQServer:
    def __init__(self):
        pass # ZeroMQ is deprecated in favor of raw atomic pointers!
        
    def start_producer(self, agent_id: int, payloads: list):
        mm = V4MemoryManager(agent_id)
        for p in payloads:
            mm.write_delta(p)
        mm.close()
        
    def consume(self, expected: int):
        mm = V4MemoryManager(99) # Observer
        results = []
        processed = 0
        
        while processed < expected:
            for agent_id in range(7):
                partition_start = agent_id * PARTITION_SIZE
                write_offset, read_offset = struct.unpack_from('ii', mm.shm.buf, partition_start)
                
                while read_offset != write_offset and processed < expected:
                    data_len = struct.unpack_from('i', mm.shm.buf, partition_start + read_offset)[0]
                    if data_len == -1:
                        read_offset = 8
                        struct.pack_into('i', mm.shm.buf, partition_start + 4, read_offset)
                        continue
                        
                    raw = bytes(mm.shm.buf[partition_start + read_offset + 4 : partition_start + read_offset + 4 + data_len])
                    _, _, payload = unpack_delta(raw)
                    results.append((agent_id, payload))
                    
                    processed += 1
                    read_offset += 4 + data_len
                    struct.pack_into('i', mm.shm.buf, partition_start + 4, read_offset)
                    write_offset = struct.unpack_from('i', mm.shm.buf, partition_start)[0]
                    
        mm.close()
        return results
