from multiprocessing import shared_memory
from src.engram.v4_structs import pack_delta, unpack_delta

SHM_NAME = "engram_v4_arena"
SHM_SIZE = 1024 * 1024 * 20  # 20 MB
PARTITION_SIZE = 1024 * 1024 * 2 # 2 MB per agent

class V4MemoryManager:
    def __init__(self, agent_id: int, create=False):
        self.agent_id = agent_id
        self.partition_start = agent_id * PARTITION_SIZE
        self.current_offset = 0
        try:
            self.shm = shared_memory.SharedMemory(name=SHM_NAME, create=create, size=SHM_SIZE)
        except FileExistsError:
            self.shm = shared_memory.SharedMemory(name=SHM_NAME)
            
    def write_delta(self, payload: str) -> tuple:
        """Writes delta CRDT to shared memory ring buffer."""
        packed = pack_delta(self.agent_id, payload)
        data_len = len(packed)
        
        if self.current_offset + data_len > PARTITION_SIZE:
            self.current_offset = 0 # Ring wrap
            
        abs_offset = self.partition_start + self.current_offset
        self.shm.buf[abs_offset:abs_offset + data_len] = packed
        
        # Return signaling offset for ZeroMQ/Queue
        signal_offset = self.current_offset
        self.current_offset += data_len
        return (self.agent_id, abs_offset, data_len)
        
    def read_delta(self, abs_offset: int, length: int) -> str:
        """Reads a delta CRDT from memory."""
        raw = bytes(self.shm.buf[abs_offset:abs_offset + length])
        _, _, payload = unpack_delta(raw)
        return payload
        
    def close(self):
        self.shm.close()
