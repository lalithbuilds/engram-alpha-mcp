import struct
from engram.v4_core import V4MemoryManager, PARTITION_SIZE, MAX_AGENTS
from engram.v4_structs import unpack_delta
import zmq
import os

class V4ZeroMQServer:
    def __init__(self):
        self.ctx = zmq.Context.instance()
        self.pull_socket = self.ctx.socket(zmq.PULL)
        self.pull_socket.setsockopt(zmq.RCVHWM, 1000000)
        ipc_path = "/tmp/engram_v4.ipc"
        if os.path.exists(ipc_path):
            try: os.remove(ipc_path)
            except: pass
        self.pull_socket.bind(f"ipc://{ipc_path}")
        
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
        
        poller = zmq.Poller()
        poller.register(self.pull_socket, zmq.POLLIN)
        
        while processed < expected:
            events = dict(poller.poll(timeout=10)) # 10ms timeout for sweeps
            
            agents_to_check = set()
            if self.pull_socket in events:
                while True:
                    try:
                        msg = self.pull_socket.recv(zmq.NOBLOCK)
                        agents_to_check.add(struct.unpack('I', msg)[0])
                    except zmq.Again:
                        break
            else:
                # Timeout sweep to catch reordered flushes
                agents_to_check = set(range(MAX_AGENTS))
                
            for agent_id in agents_to_check:
                partition_start = agent_id * PARTITION_SIZE
                write_offset, read_offset = struct.unpack_from('ii', mm.shm.buf, partition_start)
                
                while read_offset != write_offset and processed < expected:
                    data_len = struct.unpack_from('i', mm.shm.buf, partition_start + read_offset)[0]
                    if data_len == 0:
                        break # ARM64 Memory Reordering detected. Yield and retry on next sweep.
                    if data_len == -1:
                        read_offset = 8
                        struct.pack_into('i', mm.shm.buf, partition_start + 4, read_offset)
                        write_offset = struct.unpack_from('i', mm.shm.buf, partition_start)[0]
                        continue
                        
                    raw = bytes(mm.shm.buf[partition_start + read_offset + 4 : partition_start + read_offset + 4 + data_len])
                    aid, timestamp, vector, payload = unpack_delta(raw)
                    results.append((aid, payload))
                    
                    processed += 1
                    read_offset += 4 + data_len
                    struct.pack_into('i', mm.shm.buf, partition_start + 4, read_offset)
                    write_offset = struct.unpack_from('i', mm.shm.buf, partition_start)[0]
                        
        mm.close()
        return results
