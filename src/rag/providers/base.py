from abc import ABC, abstractmethod
from typing import Dict, Any

class LLMProvider(ABC):
    """
    Abstract base class for LLM Providers (e.g. Gemini, Claude).
    Ensures that the rest of the RAG system does not depend directly
    on a specific provider's API.
    """
    
    @abstractmethod
    def generate_structured_rca(self, system_prompt: str, user_prompt: str, evidence_pack_json: str) -> Dict[str, Any]:
        """
        Generates a structured JSON response matching the RCAResponse contract.
        
        Args:
            system_prompt: High-level instructions (e.g. strict grounding rules)
            user_prompt: The user's query
            evidence_pack_json: JSON string of the EvidencePack
            
        Returns:
            A dictionary representing the RCAResponse.
        """
        pass
