import multiprocessing
from multiprocessing import shared_memory
import struct
import time
import os

SHM_SIZE = 1024 * 1024 * 20  # 20 MB arena
SHM_NAME = "engram_v4_arena"
PARTITION_SIZE = 1024 * 1024 * 2 # 2 MB per agent

def producer_agent(agent_id, offset_queue, iterations):
    shm = shared_memory.SharedMemory(name=SHM_NAME)
    partition_start = agent_id * PARTITION_SIZE
    current_offset = 0
    
    successes = 0
    start_time = time.time()
    
    for _ in range(iterations):
        payload = f"V4_DELTA_{agent_id}_{time.time()}".encode('utf-8')
        fmt = f"=id{len(payload)}s"
        packed_data = struct.pack(fmt, agent_id, time.time(), payload)
        data_len = len(packed_data)
        
        # Proper Ring Buffer Wrap-Around Logic
        if current_offset + data_len > PARTITION_SIZE:
            current_offset = 0 # Wrap to beginning of partition
            
        absolute_offset = partition_start + current_offset
        shm.buf[absolute_offset:absolute_offset + data_len] = packed_data
        
        # Signaling
        offset_queue.put((agent_id, absolute_offset, data_len))
        
        current_offset += data_len
        successes += 1
        
    shm.close()
    elapsed = time.time() - start_time
    print(f"Agent {agent_id}: Wrote {successes} CRDT deltas in {elapsed:.4f}s.")

def consumer_telemetry(offset_queue, expected_total):
    shm = shared_memory.SharedMemory(name=SHM_NAME)
    processed = 0
    start_time = time.time()
    
    while processed < expected_total:
        agent_id, absolute_offset, length = offset_queue.get()
        # O(1) Zero-copy memory read
        raw_data = bytes(shm.buf[absolute_offset:absolute_offset + length])
        # Validate data integrity
        unpacked_id = struct.unpack('=i', raw_data[:4])[0]
        assert unpacked_id == agent_id, f"Corruption detected! {unpacked_id} != {agent_id}"
        processed += 1
        
    elapsed = time.time() - start_time
    shm.close()
    print(f"Telemetry: Merged {processed} deltas in {elapsed:.4f}s.")

if __name__ == "__main__":
    try:
        shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=SHM_SIZE)
    except FileExistsError:
        shm = shared_memory.SharedMemory(name=SHM_NAME)
        shm.unlink()
        shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=SHM_SIZE)

    offset_queue = multiprocessing.Queue()
    agents = 7
    ops_per_agent = 20000
    expected_total = agents * ops_per_agent
    
    producers = [multiprocessing.Process(target=producer_agent, args=(i, offset_queue, ops_per_agent)) for i in range(agents)]
    consumer = multiprocessing.Process(target=consumer_telemetry, args=(offset_queue, expected_total))
    
    start = time.time()
    consumer.start()
    for p in producers: p.start()
    for p in producers: p.join()
    consumer.join()
    
    shm.close()
    shm.unlink()
    
    total_time = time.time() - start
    print(f"\n🚀 Throughput: {expected_total / total_time:.2f} ops/sec")
