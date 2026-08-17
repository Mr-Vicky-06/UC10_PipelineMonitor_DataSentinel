import re
from typing import Dict, Any, Tuple

class QueryRouter:
    """
    Deterministic Query Router that maps natural language queries to 
    structured SQL intents (or semantic search) and extracts parameters.
    """
    
    def __init__(self):
        # Very simple deterministic routing based on regex for prototype
        # Match specific patterns or anything after "run "
        self.run_id_pattern = re.compile(r"run\s+([a-zA-Z0-9_-]+)|(RUN_[a-zA-Z0-9_-]+|[\w-]{36}|clean_\d{8}_\d{6}_[a-f0-9]{6})", re.IGNORECASE)
        self.batch_id_pattern = re.compile(r"batch\s+([a-zA-Z0-9_-]+)|(BATCH_[a-zA-Z0-9_-]+)", re.IGNORECASE)
        
    def route_query(self, query: str) -> Tuple[str, str, Dict[str, Any]]:
        """
        Returns:
            retrieval_strategy: 'STRUCTURED', 'SEMANTIC', or 'HYBRID'
            intent: The SQL intent if STRUCTURED or HYBRID
            params: Extracted parameters (e.g. run_id)
        """
        query_lower = query.lower()
        
        # Extract common entities
        run_id_match = self.run_id_pattern.search(query)
        batch_id_match = self.batch_id_pattern.search(query)
        
        params = {}
        if run_id_match:
            params['run_id'] = run_id_match.group(1) or run_id_match.group(2)
        if batch_id_match:
            params['batch_id'] = batch_id_match.group(1) or batch_id_match.group(2)
            
        # RCA or general "what happened"
        if any(keyword in query_lower for keyword in ["what happened", "root cause", "rca", "why did"]):
            if "run_id" in params:
                return "HYBRID", "RCA_ANALYSIS", params
            else:
                # If no run_id is found, we might have to rely purely on semantic search
                return "SEMANTIC", "UNKNOWN", params
                
        # Specific rule failures
        if any(keyword in query_lower for keyword in ["rule", "violation", "failed rules", "dq"]):
            if "run_id" in params:
                return "STRUCTURED", "RULE_VIOLATIONS", params
                
        # Stage performance
        if "stage" in query_lower and ("slow" in query_lower or "latency" in query_lower or "performance" in query_lower):
            if "run_id" in params:
                # For prototype, we'll route to RCA analysis if we don't extract the specific stage name
                return "STRUCTURED", "RCA_ANALYSIS", params
                
        # Anomalies
        if "anomal" in query_lower or "flagged" in query_lower:
            if "run_id" in params:
                return "STRUCTURED", "ANOMALY_SUMMARY", params
                
        # General run summary
        if "run_id" in params:
            return "STRUCTURED", "RUN_SUMMARY", params
            
        if "batch_id" in params:
            return "STRUCTURED", "BATCH_SUMMARY", params

        # Default fallback to Semantic
        return "SEMANTIC", "UNKNOWN", params

