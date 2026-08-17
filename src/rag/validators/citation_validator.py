import logging
from rag.models.evidence import EvidencePack, RCAResponse

logger = logging.getLogger(__name__)

class CitationValidator:
    """
    Programmatic validation layer after LLM generation to prevent hallucinated citations.
    """
    
    @staticmethod
    def validate(rca: RCAResponse, pack: EvidencePack) -> RCAResponse:
        """
        Validates that all evidence cited by the RCA actually exists in the EvidencePack.
        Modifies the RCA (or raises an error/flags it) if hallucinated citations are found.
        """
        valid_evidence_ids = {ev.evidence_id for ev in pack.evidence}
        
        # 1. Check likely_causes
        for cause in rca.likely_causes:
            for cited_id in cause.supporting_evidence_ids:
                if cited_id not in valid_evidence_ids:
                    logger.warning(f"Hallucinated citation detected: {cited_id} not in EvidencePack.")
                    # Either drop it, flag it, or reject entirely. 
                    # For prototype, we'll append a warning to the recommended_investigation
                    rca.recommended_investigation = (
                        f"[WARNING: LLM hallucinated evidence citation {cited_id}] " + 
                        rca.recommended_investigation
                    )
                    rca.confidence = "LOW"
                    
        # 2. Check general evidence block matches pack
        for item in rca.evidence:
            cited_id = item.get("evidence_id")
            if cited_id and cited_id not in valid_evidence_ids:
                logger.warning(f"Hallucinated evidence block item: {cited_id}")
                rca.confidence = "LOW"
                
        # 3. Handle 'Insufficient evidence' rule
        if not pack.evidence:
            if "insufficient evidence" not in rca.what_happened.lower():
                logger.error("LLM failed to declare insufficient evidence when pack was empty.")
                rca.what_happened = "Insufficient evidence to determine root cause."
                rca.likely_causes = []
                rca.confidence = "LOW"
                rca.severity = "INFO"

        return rca
