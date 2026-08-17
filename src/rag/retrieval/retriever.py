from typing import List, Dict, Any
from rag.models.evidence import Evidence, EvidencePack
from rag.retrieval.query_catalog import QueryCatalog
from rag.routing.router import QueryRouter

class EvidenceRetriever:
    """
    Coordinates routing, querying, and packing of canonical evidence.
    """
    def __init__(self, catalog: QueryCatalog, router: QueryRouter):
        self.catalog = catalog
        self.router = router
        
    def retrieve_evidence_pack(self, query: str) -> EvidencePack:
        """
        Takes a natural language query, routes it, executes retrievals,
        and returns a strict EvidencePack.
        """
        strategy, intent, params = self.router.route_query(query)
        
        evidence: List[Evidence] = []
        
        # Phase 1/B only implements STRUCTURED queries. 
        # Semantic/Hybrid will be added in Phase E.
        if strategy in ["STRUCTURED", "HYBRID"]:
            structured_evidence = self.catalog.execute_intent(intent, params)
            evidence.extend(structured_evidence)
            
        return EvidencePack(
            query=query,
            intent=intent,
            evidence=evidence,
            metadata={
                "strategy": strategy,
                "extracted_params": params
            }
        )

