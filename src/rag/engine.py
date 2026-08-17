import logging
import os
from rag.retrieval.duckdb_client import ReadOnlyDuckDBClient
from rag.retrieval.query_catalog import QueryCatalog
from rag.routing.router import QueryRouter
from rag.retrieval.retriever import EvidenceRetriever
from rag.providers.gemini import GeminiProvider
from rag.generation.rca_generator import RCAGenerator
from rag.validators.citation_validator import CitationValidator
from rag.models.evidence import RCAResponse

logger = logging.getLogger(__name__)

class RAGEngine:
    """
    Main entry point for the DataSentinel RAG Engine.
    Coordinates retrieval, generation, and validation.
    """
    
    def __init__(self, workspace_dir: str = "outputs/pipeline_workspace"):
        self.db_client = ReadOnlyDuckDBClient(workspace_dir)
        self.catalog = QueryCatalog(self.db_client)
        self.router = QueryRouter()
        self.retriever = EvidenceRetriever(self.catalog, self.router)
        
        # Configure Gemini Provider (expects GEMINI_API_KEY in env)
        self.provider = GeminiProvider(temperature=0.0)
        self.generator = RCAGenerator(self.provider)
        self.validator = CitationValidator()
        
    def ask(self, query: str) -> RCAResponse:
        """
        End-to-end RAG workflow for a user query.
        """
        logger.info(f"RAG Engine processing query: {query}")
        
        # 1. Retrieval Phase
        evidence_pack = self.retriever.retrieve_evidence_pack(query)
        logger.info(f"Retrieved {len(evidence_pack.evidence)} evidence items.")
        
        # 2. Generation Phase
        raw_rca = self.generator.generate(evidence_pack)
        
        # 3. Validation Phase
        validated_rca = self.validator.validate(raw_rca, evidence_pack)
        
        return validated_rca
