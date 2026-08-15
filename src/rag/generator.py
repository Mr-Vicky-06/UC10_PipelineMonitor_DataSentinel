import abc
from typing import Dict, Any, List

class BaseGenerator(abc.ABC):
    @abc.abstractmethod
    def generate(self, anomaly_event: Dict[str, Any], retrieved_docs: List[Dict[str, Any]], user_query: str = None) -> Dict[str, Any]:
        pass

class MockGenerator(BaseGenerator):
    def generate(self, anomaly_event: Dict[str, Any], retrieved_docs: List[Dict[str, Any]], user_query: str = None) -> Dict[str, Any]:
        """
        Mock generation that returns templated grounded responses to validate the pipeline.
        """
        # Determine sources
        sources = []
        for doc in retrieved_docs:
            sources.append(f"{doc['source_document']} ({doc['source_type']})")
        
        sources_str = ", ".join(sources) if sources else "None"
        
        # Determine remediation action
        if retrieved_docs:
            # We just pull a mock summary of the recommended steps from the runbook text.
            recommended_action = "Follow the documented remediation steps in the retrieved runbook to investigate and resolve the anomaly."
        else:
            recommended_action = "No documented remediation procedure was found for this anomaly type."
            
        # Format the grounded explanation
        explanation = f"OBSERVED EVIDENCE:\n"
        explanation += f"Anomaly Type: {anomaly_event.get('anomaly_type', 'NOT_AVAILABLE')}\n"
        explanation += f"Evidence: {anomaly_event.get('observed_evidence', 'NOT_AVAILABLE')}\n\n"
        
        explanation += f"RETRIEVED KNOWLEDGE:\n"
        if retrieved_docs:
            explanation += f"Found applicable knowledge in {sources_str}. The documentation outlines operational procedures for this anomaly.\n\n"
        else:
            explanation += f"No specific documentation found.\n\n"
            
        explanation += f"INFERENCE:\n"
        explanation += f"Based on the observed evidence and retrieved runbooks, an upstream issue or pipeline degradation may be a contributing factor. Please refer to the recommended action."

        return {
            "grounded_explanation": explanation,
            "recommended_action": recommended_action,
            "sources": sources_str
        }

class RealLLMGenerator(BaseGenerator):
    def __init__(self):
        # Initialize google-genai or vertexai here if credentials exist
        pass
        
    def generate(self, anomaly_event: Dict[str, Any], retrieved_docs: List[Dict[str, Any]], user_query: str = None) -> Dict[str, Any]:
        """
        Placeholder for the real LLM call.
        """
        return {
            "grounded_explanation": "REAL LLM NOT CONFIGURED YET",
            "recommended_action": "REAL LLM NOT CONFIGURED YET",
            "sources": "None"
        }
