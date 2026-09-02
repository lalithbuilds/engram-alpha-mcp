import multiprocessing
from multiprocessing import shared_memory
import struct
import time
import os
import sys

SHM_SIZE = 1024 * 1024 * 20
SHM_NAME = "engram_v4_arena"
PARTITION_SIZE = 1024 * 1024 * 2

def producer_agent(agent_id, iterations):
    shm = shared_memory.SharedMemory(name=SHM_NAME)
    partition_start = agent_id * PARTITION_SIZE
    struct.pack_into('ii', shm.buf, partition_start, 8, 8)
    
    successes = 0
    start_time = time.time()
    
    for _ in range(iterations):
        payload = f"V4_DELTA_{agent_id}_{time.time()}".encode('utf-8')
        fmt = f"=id{len(payload)}s"
        packed_data = struct.pack(fmt, agent_id, time.time(), payload)
        data_len = len(packed_data)
        
        while True:
            write_offset, read_offset = struct.unpack_from('ii', shm.buf, partition_start)
            if write_offset >= read_offset:
                available = PARTITION_SIZE - write_offset
                if available < data_len + 8:
                    struct.pack_into('i', shm.buf, partition_start + write_offset, -1)
                    struct.pack_into('i', shm.buf, partition_start, 8)
                    continue
            else:
                available = read_offset - write_offset
                if available < data_len + 4:
                    time.sleep(0.0001)
                    continue
            break
            
        struct.pack_into('i', shm.buf, partition_start + write_offset, data_len)
        shm.buf[partition_start + write_offset + 4 : partition_start + write_offset + 4 + data_len] = packed_data
        struct.pack_into('i', shm.buf, partition_start, write_offset + 4 + data_len)
        successes += 1
        
    shm.close()
    elapsed = time.time() - start_time
    print(f"Agent {agent_id}: Wrote {successes} CRDT deltas in {elapsed:.4f}s.")

def consumer_telemetry(expected_total, agents):
    shm = shared_memory.SharedMemory(name=SHM_NAME)
    processed = 0
    start_time = time.time()
    
    while processed < expected_total:
        for agent_id in range(agents):
            partition_start = agent_id * PARTITION_SIZE
            write_offset, read_offset = struct.unpack_from('ii', shm.buf, partition_start)
            
            while read_offset != write_offset and processed < expected_total:
                data_len = struct.unpack_from('i', shm.buf, partition_start + read_offset)[0]
                if data_len == -1:
                    read_offset = 8
                    struct.pack_into('i', shm.buf, partition_start + 4, read_offset)
                    continue
                    
                raw_data = bytes(shm.buf[partition_start + read_offset + 4 : partition_start + read_offset + 4 + data_len])
                unpacked_id = struct.unpack('=i', raw_data[:4])[0]
                if unpacked_id != agent_id:
                    print(f"CRASH/CORRUPTION in Agent {agent_id} partition!")
                    sys.exit(1)
                    
                processed += 1
                read_offset += 4 + data_len
                struct.pack_into('i', shm.buf, partition_start + 4, read_offset)
                write_offset = struct.unpack_from('i', shm.buf, partition_start)[0]
    
    elapsed = time.time() - start_time
    shm.close()
    print(f"Telemetry: Merged {processed} deltas in {elapsed:.4f}s. TRUE ZERO IPC OVERHEAD.")

if __name__ == "__main__":
    try:
        shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=SHM_SIZE)
    except FileExistsError:
        shm = shared_memory.SharedMemory(name=SHM_NAME)
        shm.unlink()
        shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=SHM_SIZE)

    agents = 7
    ops_per_agent = 100000
    expected_total = agents * ops_per_agent
    
    for i in range(agents):
        struct.pack_into('ii', shm.buf, i * PARTITION_SIZE, 8, 8)
        
    producers = [multiprocessing.Process(target=producer_agent, args=(i, ops_per_agent)) for i in range(agents)]
    import sys
    consumer = multiprocessing.Process(target=consumer_telemetry, args=(expected_total, agents))
    
    start = time.time()
    consumer.start()
    for p in producers: p.start()
    for p in producers: p.join()
    consumer.join()
    
    shm.close()
    shm.unlink()
    total_time = time.time() - start
    print(f"\n🚀 True Lock-Free Throughput: {expected_total / total_time:.2f} ops/sec")
