import multiprocessing
from src.engram.v4_core import V4MemoryManager

class V4ZeroMQServer:
    def __init__(self):
        # We use multiprocessing.Queue to simulate ZeroMQ's IPC signaling
        self.offset_queue = multiprocessing.Queue()
        
    def start_producer(self, agent_id: int, payloads: list):
        mm = V4MemoryManager(agent_id)
        for p in payloads:
            signal = mm.write_delta(p)
            self.offset_queue.put(signal)
        mm.close()
        
    def consume(self, expected: int):
        mm = V4MemoryManager(99) # Observer
        results = []
        for _ in range(expected):
            agent_id, offset, length = self.offset_queue.get()
            payload = mm.read_delta(offset, length)
            results.append((agent_id, payload))
        mm.close()
        return results
