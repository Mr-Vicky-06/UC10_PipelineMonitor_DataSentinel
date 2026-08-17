import json
import logging
from typing import Dict, Any

from rag.providers.base import LLMProvider
from rag.models.evidence import EvidencePack, RCAResponse

logger = logging.getLogger(__name__)

class RCAGenerator:
    """
    Coordinates grounded RCA generation, enforcing strict LLM rules.
    """
    
    SYSTEM_PROMPT = """
    You are the DataSentinel Root Cause Analysis (RCA) Engine.
    Your sole purpose is to explain and correlate the structured pipeline telemetry, 
    business rule violations, and statistical anomalies provided in the Evidence Pack.
    
    CRITICAL RULES:
    1. NEVER invent anomalies, telemetry, or metrics that are not in the Evidence Pack.
    2. NEVER invent a root cause without supporting evidence.
    3. If the evidence does not clearly establish what happened, you MUST state "Insufficient evidence to determine root cause" in the what_happened and recommended_investigation fields, and provide empty likely_causes.
    4. You MUST respond with a strict JSON object matching the exact schema below.
    5. Every 'likely_cause' MUST contain a list of supporting_evidence_ids that exist in the Evidence Pack.
    6. Summarize the severity as the highest severity among the evidence (INFO, WARNING, ERROR, CRITICAL).
    
    JSON SCHEMA:
    {
        "incident_id": "string (generate a short INC- UUID)",
        "summary": "string (1 sentence summary of the issue)",
        "severity": "string (INFO, WARNING, ERROR, CRITICAL)",
        "affected_hospital": "string",
        "affected_batch": "string",
        "affected_stage": "string",
        "what_happened": "string (detailed explanation)",
        "evidence": [
            { "evidence_id": "string", "description": "string (short description)" }
        ],
        "likely_causes": [
            {
                "cause": "string (explanation)",
                "supporting_evidence_ids": ["string"]
            }
        ],
        "confidence": "string (HIGH, MEDIUM, LOW)",
        "recommended_investigation": "string (what should a human check next?)",
        "source_references": ["string"]
    }
    """
    
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        
    def generate(self, evidence_pack: EvidencePack) -> RCAResponse:
        """
        Executes the generation process and returns a validated RCAResponse.
        """
        if not evidence_pack.evidence:
            logger.warning("Attempted to generate RCA with empty evidence pack.")
            
        evidence_json = evidence_pack.model_dump_json()
        
        try:
            # We pass the schema directly through the provider since the provider 
            # is responsible for enforcing the JSON constraint.
            response_dict = self.provider.generate_structured_rca(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=evidence_pack.query,
                evidence_pack_json=evidence_json
            )
            
            # Validate output against Pydantic schema
            rca_response = RCAResponse(**response_dict)
            return rca_response
            
        except Exception as e:
            logger.error(f"RCA Generation failed: {str(e)}")
            raise
