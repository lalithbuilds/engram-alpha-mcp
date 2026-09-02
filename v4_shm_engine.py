import multiprocessing
from multiprocessing import shared_memory
import struct
import time
import os
import sys
import zmq

SHM_SIZE = 1024 * 1024 * 50
SHM_NAME = "engram_v4_arena"
PARTITION_SIZE = 1024 * 1024 * 5
MAX_AGENTS = 10

def _remove_shm_from_resource_tracker():
    from multiprocessing import resource_tracker
    def fix_register(name, rtype):
        if rtype == "shared_memory": return
        return resource_tracker._resource_tracker.register(name, rtype)
    resource_tracker.register = fix_register

    def fix_unregister(name, rtype):
        if rtype == "shared_memory": return
        return resource_tracker._resource_tracker.unregister(name, rtype)
    resource_tracker.unregister = fix_unregister

    if "shared_memory" in getattr(resource_tracker, '_CLEANUP_FUNCS', {}):
        del resource_tracker._CLEANUP_FUNCS["shared_memory"]

if sys.platform != "win32":
    _remove_shm_from_resource_tracker()

def producer_agent(agent_id, iterations):
    shm = shared_memory.SharedMemory(name=SHM_NAME)
    partition_start = agent_id * PARTITION_SIZE
    
    ctx = zmq.Context.instance()
    pub = ctx.socket(zmq.PUSH)
    pub.setsockopt(zmq.SNDHWM, 1000000)
    pub.setsockopt(zmq.LINGER, 0)
    pub.connect("ipc:///tmp/engram_v4.ipc")
    
    successes = 0
    start_time = time.time()
    
    for _ in range(iterations):
        payload = f"V4_DELTA_{agent_id}_{time.time()}".encode('utf-8')
        vec = [0.0] * 384
        vec_bytes = struct.pack("384f", *vec)
        
        fmt = f"=id1536si{len(payload)}s"
        packed_data = struct.pack(fmt, agent_id, time.time(), vec_bytes, len(payload), payload)
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
                if available <= data_len + 4:
                    time.sleep(0.0001)
                    continue
            break
            
        struct.pack_into('i', shm.buf, partition_start + write_offset, data_len)
        shm.buf[partition_start + write_offset + 4 : partition_start + write_offset + 4 + data_len] = packed_data
        struct.pack_into('i', shm.buf, partition_start, write_offset + 4 + data_len)
        
        try:
            pub.send(struct.pack('I', agent_id), zmq.NOBLOCK)
        except zmq.Again:
            pass
            
        successes += 1
        
    shm.close()
    pub.close()
    elapsed = time.time() - start_time
    print(f"Agent {agent_id}: Wrote {successes} CRDT deltas in {elapsed:.4f}s.")

def consumer_telemetry(expected_total):
    shm = shared_memory.SharedMemory(name=SHM_NAME)
    processed = 0
    
    ctx = zmq.Context.instance()
    pull = ctx.socket(zmq.PULL)
    pull.setsockopt(zmq.RCVHWM, 1000000)
    ipc_path = "/tmp/engram_v4.ipc"
    if os.path.exists(ipc_path):
        try: os.remove(ipc_path)
        except: pass
    pull.bind(f"ipc://{ipc_path}")
    
    poller = zmq.Poller()
    poller.register(pull, zmq.POLLIN)
    
    start_time = time.time()
    
    while processed < expected_total:
        events = dict(poller.poll(timeout=10))
        
        agents_to_check = set()
        if pull in events:
            while True:
                try:
                    msg = pull.recv(zmq.NOBLOCK)
                    agents_to_check.add(struct.unpack('I', msg)[0])
                except zmq.Again:
                    break
        else:
            agents_to_check = set(range(MAX_AGENTS))
            
        for agent_id in agents_to_check:
            partition_start = agent_id * PARTITION_SIZE
            write_offset, read_offset = struct.unpack_from('ii', shm.buf, partition_start)
            
            while read_offset != write_offset and processed < expected_total:
                data_len = struct.unpack_from('i', shm.buf, partition_start + read_offset)[0]
                if data_len == 0:
                    break # ARM64 Reordering! Wait for sweep.
                if data_len == -1:
                    read_offset = 8
                    struct.pack_into('i', shm.buf, partition_start + 4, read_offset)
                    write_offset = struct.unpack_from('i', shm.buf, partition_start)[0]
                    continue
                    
                processed += 1
                read_offset += 4 + data_len
                struct.pack_into('i', shm.buf, partition_start + 4, read_offset)
                write_offset = struct.unpack_from('i', shm.buf, partition_start)[0]
    
    elapsed = time.time() - start_time
    shm.close()
    pull.close()
    print(f"Telemetry: Merged {processed} deltas in {elapsed:.4f}s via ZeroMQ Event Loop.")

if __name__ == "__main__":
    _remove_shm_from_resource_tracker()
    
    try:
        shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=SHM_SIZE)
    except FileExistsError:
        shm = shared_memory.SharedMemory(name=SHM_NAME)
        shm.unlink()
        shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=SHM_SIZE)

    agents = 7
    ops_per_agent = 100000
    expected_total = agents * ops_per_agent
    
    for i in range(MAX_AGENTS):
        struct.pack_into('ii', shm.buf, i * PARTITION_SIZE, 8, 8)
        
    producers = [multiprocessing.Process(target=producer_agent, args=(i, ops_per_agent)) for i in range(agents)]
    consumer = multiprocessing.Process(target=consumer_telemetry, args=(expected_total,))
    
    start = time.time()
    consumer.start()
    time.sleep(0.1)
    
    for p in producers: p.start()
    for p in producers: p.join()
    consumer.join()
    
    shm.close()
    shm.unlink()
    total_time = time.time() - start
    print(f"\n🚀 True Lock-Free ZeroMQ Throughput: {expected_total / total_time:.2f} ops/sec")
