import logging
from src.rag.models.evidence import EvidencePack, RCAResponse

logger = logging.getLogger(__name__)

class CitationValidator:
    """
    Programmatic validation layer after LLM generation to prevent hallucinated citations.
    """
    
    @staticmethod
    def validate(rca: RCAResponse, pack: EvidencePack) -> RCAResponse:
        """
        Validates that all evidence cited by the RCA actually exists in the EvidencePack.
        Raises ValueError if hallucinated citations are found.
        """
        valid_evidence_ids = {ev.evidence_id for ev in pack.evidence}
        
        # Helper to check lists of dict-like models or dicts
        def validate_evidence_ids(field_name, items):
            for item in items:
                # Can be a dict or a BaseModel
                evidence_ids = getattr(item, "evidence_ids", [])
                if hasattr(item, "supporting_evidence_ids"):
                    evidence_ids = getattr(item, "supporting_evidence_ids")
                    
                for cited_id in evidence_ids:
                    if cited_id not in valid_evidence_ids:
                        raise ValueError(f"Hallucinated citation in {field_name}: {cited_id} not in EvidencePack.")
        
        # 1. Check facts
        validate_evidence_ids("facts", rca.facts)
        
        # 2. Check confirmed_findings
        validate_evidence_ids("confirmed_findings", rca.confirmed_findings)
        
        # 3. Check correlated_findings
        validate_evidence_ids("correlated_findings", rca.correlated_findings)
        
        # 4. Check likely_causes
        validate_evidence_ids("likely_causes", rca.likely_causes)

        # 5. Check general evidence block matches pack
        for item in rca.evidence:
            cited_id = item.get("evidence_id")
            if cited_id and cited_id not in valid_evidence_ids:
                raise ValueError(f"Hallucinated evidence block item: {cited_id}")
                
        # 6. Check source_references
        for ref in rca.source_references:
            if ref not in valid_evidence_ids:
                raise ValueError(f"Hallucinated source reference: {ref}")
                
        # 7. Handle 'Insufficient evidence' rule
        if not pack.evidence:
            if "insufficient evidence" not in rca.what_happened.lower():
                raise ValueError("LLM failed to declare insufficient evidence when pack was empty.")

        return rca
