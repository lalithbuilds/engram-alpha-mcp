import os
import time
import uuid
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from engram.server import save_memory, search_memory, save_graph_relation

os.environ["ENGRAM_DB_PATH"] = "simulation.sqlite"

AGENTS = ["FABLE", "GEMINI", "KIMI", "SOUL", "DEEP", "GLM", "O1"]
TOPICS = ["Quantum Computing", "Genomics", "GraphRAG", "Nuclear Fusion", "CRISPR", "Neural Networks", "SpaceX", "Memory Eviction"]

def agent_worker(agent_name, iterations):
    successes = 0
    errors = {}
    
    for i in range(iterations):
        try:
            action = random.choice(["save", "search", "graph"])
            topic = random.choice(TOPICS)
            
            if action == "save":
                text = f"[{agent_name}] Discovered new insight about {topic} at {time.time()}."
                save_memory(text)
            elif action == "search":
                search_memory(topic, limit=3)
            elif action == "graph":
                save_graph_relation(agent_name, "studied", topic)
                
            successes += 1
            # Add micro-sleep to simulate real agent cadence and allow OS context switching
            time.sleep(random.uniform(0.01, 0.05))
            
        except Exception as e:
            err_msg = str(e)
            if err_msg not in errors:
                errors[err_msg] = 0
            errors[err_msg] += 1
            
    return agent_name, successes, errors

def main():
    print(f"Starting Model Council Simulation on Engram Alpha...")
    if os.path.exists("simulation.sqlite"):
        os.remove("simulation.sqlite")
        
    start_time = time.time()
    iterations_per_agent = 1000  # Total 7000 DB hits
    
    results = []
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {executor.submit(agent_worker, agent, iterations_per_agent): agent for agent in AGENTS}
        for future in as_completed(futures):
            results.append(future.result())
            
    elapsed = time.time() - start_time
    print(f"\n--- Simulation Complete in {elapsed:.2f} seconds ---")
    
    total_success = 0
    total_errors = 0
    for agent, succ, errs in results:
        print(f"\nAgent {agent}:")
        print(f"  Successes: {succ}")
        if errs:
            print(f"  Errors:")
            for e_msg, count in errs.items():
                print(f"    - [{count}x] {e_msg}")
                total_errors += count
        total_success += succ
        
    print(f"\nFinal Tally: {total_success} successful operations, {total_errors} errors.")
    
if __name__ == "__main__":
    main()
