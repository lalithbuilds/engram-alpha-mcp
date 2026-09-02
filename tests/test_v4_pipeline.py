from src.engram.v4_core import V4MemoryManager, SHM_NAME, SHM_SIZE
from src.engram.v4_server import V4ZeroMQServer
from multiprocessing import shared_memory
import threading

def test_pipeline():
    try:
        shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=SHM_SIZE)
    except FileExistsError:
        shm = shared_memory.SharedMemory(name=SHM_NAME)
        shm.unlink()
        shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=SHM_SIZE)
        
    server = V4ZeroMQServer()
    
    t1 = threading.Thread(target=server.start_producer, args=(0, ["hello", "world"]))
    t1.start()
    t1.join()
    
    results = server.consume(2)
    assert results[0][1] == "hello"
    assert results[1][1] == "world"
    
    shm.close()
    shm.unlink()
    print("V4 Pipeline OK")
