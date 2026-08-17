import json
import logging
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from rag.routing.router import QueryRouter

def evaluate_router(dataset_path: str):
    with open(dataset_path, "r") as f:
        data = json.load(f)
        
    router = QueryRouter()
    correct = 0
    total = len(data["queries"])
    
    for q in data["queries"]:
        strategy, intent, params = router.route_query(q["query"])
        
        expected_intent = q.get("expected_intent")
        if expected_intent == intent:
            correct += 1
        else:
            print(f"FAILED: {q['query']}")
            print(f"  Expected: {expected_intent}, Got: {intent}")
            
    print(f"\nRouter Evaluation: {correct}/{total} ({(correct/total)*100:.2f}%)")

if __name__ == "__main__":
    evaluate_router("data/rag/golden_dataset.json")
