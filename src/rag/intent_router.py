from typing import Dict, Any, Tuple

class IntentRouter:
    def route(self, query: str) -> str:
        """
        Determines whether a query is STRUCTURED, RAG, or MIXED.
        """
        query_lower = query.lower()
        
        structured_keywords = ["status", "severity", "confidence", "score", "sla", "date", "dataset", "detector"]
        rag_keywords = ["mean", "why", "procedure", "occurred before", "history", "documentation", "runbook", "action", "remediation", "what should"]
        
        has_structured = any(kw in query_lower for kw in structured_keywords)
        has_rag = any(kw in query_lower for kw in rag_keywords)
        
        if has_structured and has_rag:
            return "MIXED"
        elif has_structured:
            return "STRUCTURED"
        elif has_rag:
            return "RAG"
        else:
            # Default to RAG if ambiguous
            return "RAG"
