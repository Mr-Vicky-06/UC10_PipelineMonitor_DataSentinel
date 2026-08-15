from typing import Dict, Any

class StructuredQueryEngine:
    def __init__(self):
        pass
        
    def answer(self, query: str, anomaly_event: Dict[str, Any]) -> str:
        """
        Provides direct answers based on structured data.
        """
        query_lower = query.lower()
        
        response = ""
        if "severity" in query_lower:
            response += f"Severity: {anomaly_event.get('severity', 'NOT_AVAILABLE')}\n"
        if "confidence" in query_lower:
            response += f"Confidence: {anomaly_event.get('confidence', 'NOT_AVAILABLE')}\n"
        if "sla" in query_lower:
            response += f"SLA Status: {anomaly_event.get('SLA_status', 'NOT_AVAILABLE')} (Margin: {anomaly_event.get('SLA_margin', 'NOT_AVAILABLE')}s)\n"
        if "score" in query_lower:
            response += f"Evidence Score: {anomaly_event.get('evidence_score', 'NOT_AVAILABLE')}\n"
        if "date" in query_lower:
            response += f"Anomaly Date: {anomaly_event.get('window_date', 'NOT_AVAILABLE')}\n"
        if "dataset" in query_lower:
            response += f"Affected Dataset: {anomaly_event.get('dataset', 'NOT_AVAILABLE')}\n"
            
        if not response:
            response = "Structured answer NOT_AVAILABLE for this specific query."
            
        return response
