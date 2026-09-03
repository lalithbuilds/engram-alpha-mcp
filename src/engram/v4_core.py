from multiprocessing import shared_memory, resource_tracker
import struct
from engram.v4_structs import pack_delta, unpack_delta
import time
import zmq
import sys

# Monkey-patch resource_tracker to prevent unlinking of shared_memory on exit
def _remove_shm_from_resource_tracker():
    def fix_register(name, rtype):
        if rtype == "shared_memory":
            return
        return resource_tracker._resource_tracker.register(name, rtype)
    resource_tracker.register = fix_register

    def fix_unregister(name, rtype):
        if rtype == "shared_memory":
            return
        return resource_tracker._resource_tracker.unregister(name, rtype)
    resource_tracker.unregister = fix_unregister

    if "shared_memory" in resource_tracker._CLEANUP_FUNCS:
        del resource_tracker._CLEANUP_FUNCS["shared_memory"]

if sys.platform != "win32":
    _remove_shm_from_resource_tracker()

SHM_NAME = "engram_v4_arena"
SHM_SIZE = 1024 * 1024 * 50  # 50 MB
PARTITION_SIZE = 1024 * 1024 * 5 # 5 MB per agent
MAX_AGENTS = 10
ZMQ_ENDPOINT = "tcp://127.0.0.1:55557" if sys.platform == "win32" else "ipc:///tmp/engram_v4.ipc"

class V4MemoryManager:
    def __init__(self, agent_id: int, create=False, zmq_context=None):
        self.agent_id = agent_id
        self.partition_start = agent_id * PARTITION_SIZE
        try:
            self.shm = shared_memory.SharedMemory(name=SHM_NAME, create=create, size=SHM_SIZE)
            if create:
                for i in range(MAX_AGENTS):
                    struct.pack_into('ii', self.shm.buf, i * PARTITION_SIZE, 8, 8)
        except FileExistsError:
            self.shm = shared_memory.SharedMemory(name=SHM_NAME)
            
        self.ctx = zmq_context or zmq.Context.instance()
        self.pub_socket = self.ctx.socket(zmq.PUSH)
        # HWM prevents producer blocking if server goes away briefly
        self.pub_socket.setsockopt(zmq.SNDHWM, 100000)
        self.pub_socket.setsockopt(zmq.LINGER, 0)
        self.pub_socket.connect(ZMQ_ENDPOINT)
            
    def write_delta(self, payload: str, vector: list):
        packed = pack_delta(self.agent_id, payload, vector)
        data_len = len(packed)
        
        while True:
            write_offset, read_offset = struct.unpack_from('ii', self.shm.buf, self.partition_start)
            
            if write_offset >= read_offset:
                available = PARTITION_SIZE - write_offset
                if available < data_len + 8:
                    struct.pack_into('i', self.shm.buf, self.partition_start + write_offset, -1)
                    struct.pack_into('i', self.shm.buf, self.partition_start, 8)
                    continue
            else:
                available = read_offset - write_offset
                if available <= data_len + 4:
                    time.sleep(0.0001)
                    continue
            break
            
        struct.pack_into('i', self.shm.buf, self.partition_start + write_offset, data_len)
        self.shm.buf[self.partition_start + write_offset + 4 : self.partition_start + write_offset + 4 + data_len] = packed
        
        new_write_offset = write_offset + 4 + data_len
        struct.pack_into('i', self.shm.buf, self.partition_start, new_write_offset)
        
        # ZMQ signal acts as a write memory barrier (WMB) and wakes epoll consumer
        try:
            self.pub_socket.send(struct.pack('I', self.agent_id), zmq.NOBLOCK)
        except zmq.Again:
            pass # Socket queue full, consumer is behind but will eventually catch up
            
    def close(self):
        self.pub_socket.close()
        self.shm.close()
