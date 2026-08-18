import json
import logging
from typing import Dict, Any, List
from datetime import datetime
import uuid

from src.rag.providers.base import LLMProvider
from src.rag.models.evidence import EvidencePack, RCAResponse, Fact, ConfirmedFinding, CorrelatedFinding, LikelyCause

logger = logging.getLogger(__name__)

class RCAGenerator:
    """
    Coordinates grounded RCA generation, enforcing strict LLM rules and deterministic confidence/severity.
    """
    
    SYSTEM_PROMPT = """
    You are the DataSentinel Root Cause Analysis (RCA) Engine.
    Your sole purpose is to explain and correlate the structured pipeline telemetry, 
    business rule violations, and statistical anomalies provided in the Evidence Pack.
    
    CRITICAL RULES:
    1. NEVER invent anomalies, telemetry, or metrics that are not in the Evidence Pack.
    2. NEVER invent a root cause without supporting evidence.
    3. If the evidence does not clearly establish what happened, you MUST state "Insufficient evidence to determine root cause" in the what_happened and recommended_investigation fields.
    4. You MUST respond with a strict JSON object matching the exact schema below.
    5. SEPARATE FACTS FROM CORRELATION AND CAUSE:
       - 'facts': Direct observations from evidence (e.g., "Duration increased to 15s").
       - 'confirmed_findings': Direct deterministic proof of failure (e.g., "Missing CLM_ID failed DQ rule").
       - 'correlated_findings': Events occurring together without proven causality.
       - 'likely_causes': Explanations ONLY when evidence strongly supports the cause. If not, LEAVE EMPTY.
    6. Every finding must contain a list of supporting_evidence_ids that exist in the Evidence Pack.
    
    JSON SCHEMA:
    {
        "summary": "string (1 sentence summary of the issue)",
        "what_happened": "string (detailed explanation)",
        "facts": [{"description": "string", "evidence_ids": ["string"]}],
        "confirmed_findings": [{"description": "string", "evidence_ids": ["string"]}],
        "correlated_findings": [{"description": "string", "evidence_ids": ["string"]}],
        "likely_causes": [{"cause": "string", "supporting_evidence_ids": ["string"]}],
        "recommended_investigation": "string (what should a human check next?)"
    }
    """
    
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        
    def _calculate_deterministic_severity(self, evidence_pack: EvidencePack) -> str:
        """Computes severity deterministically from EvidencePack."""
        if not evidence_pack.evidence:
            return "INFO"
            
        severities = [e.severity for e in evidence_pack.evidence]
        
        if "CRITICAL" in severities:
            return "CRITICAL"
        if "ERROR" in severities:
            return "ERROR"
        if "WARNING" in severities:
            return "WARNING"
        return "INFO"
        
    def _calculate_deterministic_confidence(self, evidence_pack: EvidencePack) -> str:
        """Computes confidence deterministically from EvidencePack."""
        if not evidence_pack.evidence:
            return "ZERO"
            
        has_dq = any(e.evidence_type == 'rule_violation' for e in evidence_pack.evidence)
        has_pipeline_fail = any(e.evidence_type == 'pipeline_failure' for e in evidence_pack.evidence)
        has_ml = any(e.evidence_type == 'statistical_anomaly' for e in evidence_pack.evidence)
        has_sla = any(e.evidence_type == 'sla_status' for e in evidence_pack.evidence)
        
        # Direct deterministic failure evidence
        if has_dq or has_pipeline_fail:
            return "HIGH"
            
        # Multiple independent signals
        signals = sum([has_ml, has_sla])
        if signals >= 2:
            return "MEDIUM"
            
        # Only statistical or indirect
        if has_ml or has_sla:
            return "LOW"
            
        return "ZERO"

    def generate(self, evidence_pack: EvidencePack) -> RCAResponse:
        """
        Executes the generation process and returns a validated RCAResponse.
        """
        if not evidence_pack.evidence:
            logger.warning("Attempted to generate RCA with empty evidence pack.")
            
        evidence_json = evidence_pack.model_dump_json()
        
        # 1. Deterministic properties
        severity = self._calculate_deterministic_severity(evidence_pack)
        confidence = self._calculate_deterministic_confidence(evidence_pack)
        
        run_id = evidence_pack.evidence[0].run_id if evidence_pack.evidence else "UNKNOWN"
        hospital_id = evidence_pack.evidence[0].hospital_id if evidence_pack.evidence else "UNKNOWN"
        batch_id = evidence_pack.evidence[0].batch_id if evidence_pack.evidence else "UNKNOWN"
        affected_stage = evidence_pack.evidence[0].stage if evidence_pack.evidence else "UNKNOWN"
        
        sla_obs = [e for e in evidence_pack.evidence if e.evidence_type == 'sla_status']
        sla_status = sla_obs[0].observed_value if sla_obs else "UNKNOWN"
        
        anomaly_types = list(set([e.evidence_type for e in evidence_pack.evidence]))
        status = "OPEN"
        created_at = datetime.utcnow().isoformat()
        
        base_response_kwargs = {
            "incident_id": f"INC-{uuid.uuid4().hex[:8]}",
            "run_id": run_id,
            "hospital_id": hospital_id,
            "batch_id": batch_id,
            "affected_stage": affected_stage,
            "anomaly_types": anomaly_types,
            "severity": severity,
            "status": status,
            "confidence": confidence,
            "sla_status": sla_status,
            "created_at": created_at,
            "source_references": [e.evidence_id for e in evidence_pack.evidence],
            "evidence": [{"evidence_id": e.evidence_id, "description": str(e.observed_value)} for e in evidence_pack.evidence]
        }
        
        try:
            # We pass the schema directly through the provider since the provider 
            # is responsible for enforcing the JSON constraint.
            response_dict = self.provider.generate_structured_rca(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=evidence_pack.query,
                evidence_pack_json=evidence_json
            )
            
            # Merge LLM dict with our deterministic fields
            response_dict.update(base_response_kwargs)
            
            # Validate output against Pydantic schema
            rca_response = RCAResponse(**response_dict)
            
            # Post-validation for hallucinations
            from src.rag.validators.citation_validator import CitationValidator
            rca_response = CitationValidator.validate(rca_response, evidence_pack)
            
            return rca_response
            
        except Exception as e:
            logger.error(f"RCA Generation failed: {str(e)}")
            # Fallback for Gemini failure / Missing API key
            fallback_response = RCAResponse(
                summary="Gemini API unavailable. Evidence collected successfully." if evidence_pack.evidence else "Insufficient evidence to determine root cause.",
                what_happened="Insufficient evidence to determine root cause due to LLM failure." if evidence_pack.evidence else "Insufficient evidence.",
                facts=[],
                confirmed_findings=[],
                correlated_findings=[],
                likely_causes=[],
                recommended_investigation="Insufficient evidence to determine root cause.",
                **base_response_kwargs
            )
            
            return fallback_response
