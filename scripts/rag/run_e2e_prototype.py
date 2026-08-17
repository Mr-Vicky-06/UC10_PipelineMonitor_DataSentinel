import os
import sys
import json

# Add src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from rag.engine import RAGEngine

def main():
    # Ensure GEMINI_API_KEY is set in environment or handled securely
    if not os.environ.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = "MOCK_KEY"
    
    # Ensure directories exist
    os.makedirs("outputs/rag/reports", exist_ok=True)
    
    engine = RAGEngine()
    
    test_run_id = "clean_20260817_180959_3449a4" # Found via DuckDB query
    
    queries = [
        f"What happened to run {test_run_id}?",
        f"Why did run {test_run_id} fail?",
        "Why did run RUN_DOES_NOT_EXIST fail?"
    ]
    
    for i, query in enumerate(queries):
        print(f"\n{'='*50}\nTEST {i+1}: {query}\n{'='*50}")
        try:
            response = engine.ask(query)
            
            # Print human-readable output summary
            print(f"\n[INCIDENT]: {response.incident_id}")
            print(f"[SUMMARY]: {response.summary}")
            print(f"[SEVERITY]: {response.severity}")
            print(f"\n[WHAT HAPPENED]:\n{response.what_happened}")
            print(f"\n[RECOMMENDED INVESTIGATION]:\n{response.recommended_investigation}")
            
            print("\n[LIKELY CAUSES]:")
            for c in response.likely_causes:
                print(f"  - {c.cause} (Evidence: {c.supporting_evidence_ids})")
                
            # Save raw JSON for debugging
            with open(f"outputs/rag/reports/e2e_test_{i+1}.json", "w") as f:
                f.write(response.model_dump_json(indent=2))
                
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    main()
