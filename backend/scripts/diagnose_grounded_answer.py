import os
from precis.graph.store import FactStore
from precis.pipeline.orchestrator import query_pipeline
from precis.pipeline.hardware import profile_hardware

def diagnose():
    store = FactStore(persist_dir="./chroma_data")
    hardware = profile_hardware()
    print(f"Store fact count: {store.count()}")
    
    query = "What did the government approve and what was excluded?"
    print(f"Running query: {query}")
    
    res = query_pipeline(
        query=query,
        store=store,
        hardware=hardware,
        stream=False,
    )
    print("--- Pipeline Result ---")
    print(f"Answer: {repr(res.answer)}")
    print(f"Inference tokens: {res.inference_tokens}")
    print(f"Latency: {res.latency_ms}ms")
    print(f"Facts used: {len(res.facts_used)}")

if __name__ == "__main__":
    diagnose()
