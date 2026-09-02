from multiprocessing import shared_memory
import struct
from engram.v4_structs import pack_delta, unpack_delta
import time

SHM_NAME = "engram_v4_arena"
SHM_SIZE = 1024 * 1024 * 50  # 50 MB
PARTITION_SIZE = 1024 * 1024 * 5 # 5 MB per agent

class V4MemoryManager:
    def __init__(self, agent_id: int, create=False):
        self.agent_id = agent_id
        self.partition_start = agent_id * PARTITION_SIZE
        try:
            self.shm = shared_memory.SharedMemory(name=SHM_NAME, create=create, size=SHM_SIZE)
            if create:
                for i in range(7):
                    struct.pack_into('ii', self.shm.buf, i * PARTITION_SIZE, 8, 8)
        except FileExistsError:
            self.shm = shared_memory.SharedMemory(name=SHM_NAME)
            
    def write_delta(self, payload: str, vector: list):
        packed = pack_delta(self.agent_id, payload, vector)
        data_len = len(packed)
        
        while True:
            write_offset, read_offset = struct.unpack_from('ii', self.shm.buf, self.partition_start)
            
            if write_offset >= read_offset:
                available = PARTITION_SIZE - write_offset
                if available < data_len + 8:
                    struct.pack_into('i', self.shm.buf, self.partition_start + write_offset, -1)
                    # Memory barrier would go here
                    struct.pack_into('i', self.shm.buf, self.partition_start, 8)
                    continue
            else:
                available = read_offset - write_offset
                # Wait! We must leave at least 1 byte so write_offset never == read_offset when full
                if available <= data_len + 4:
                    time.sleep(0.0001)
                    continue
            break
            
        struct.pack_into('i', self.shm.buf, self.partition_start + write_offset, data_len)
        self.shm.buf[self.partition_start + write_offset + 4 : self.partition_start + write_offset + 4 + data_len] = packed
        # Simulating a write memory barrier (WMB)
        struct.pack_into('i', self.shm.buf, self.partition_start, write_offset + 4 + data_len)
        
    def close(self):
        self.shm.close()
