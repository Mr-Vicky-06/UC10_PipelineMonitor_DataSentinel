import os
import sys
import logging
from src.pipeline.orchestrator import PipelineOrchestrator
from src.rag.retrieval.duckdb_client import ReadOnlyDuckDBClient
from src.rag.retrieval.query_catalog import QueryCatalog
from src.rag.retrieval.retriever import EvidenceRetriever
from src.rag.routing.router import QueryRouter
from src.rag.generation.rca_generator import RCAGenerator
from src.rag.providers.gemini import GeminiProvider
from src.action.engine import ActionEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Live Telemetry Test Flow...")
    
    # 1. Run Pipeline
    orchestrator = PipelineOrchestrator()
    import uuid
    run_id = f"test_run_{uuid.uuid4().hex[:8]}"
    orchestrator.run(source_directory="data/claims", run_id=run_id)
    logger.info(f"Pipeline completed with run_id: {run_id}")
    
    # 2. Retrieve Evidence Pack
    db_client = ReadOnlyDuckDBClient()
    catalog = QueryCatalog(db_client)
    router = QueryRouter()
    retriever = EvidenceRetriever(catalog, router)
    
    # Query for the recent run to trigger _get_rca_analysis
    pack = retriever.retrieve_evidence_pack(f"Provide a root cause analysis for run_id {run_id}")
    
    # Check SLA evidence
    sla_obs = [e for e in pack.evidence if e.evidence_type == "sla_status"]
    logger.info(f"Retrieved {len(sla_obs)} SLA observations from telemetry")
    
    sla_status = "UNKNOWN"
    if sla_obs:
        sla_status = sla_obs[0].observed_value
        logger.info(f"Primary SLA status: {sla_status}")
    
    # 3. Generate RCA
    provider = GeminiProvider()
    rca_gen = RCAGenerator(provider)
    rca_response = rca_gen.generate(pack)
    logger.info(f"RCA Generated: {rca_response.summary}")
    
    # 4. Action Engine
    action_engine = ActionEngine()
    alert = action_engine.evaluate_and_alert(
        incident_id=rca_response.incident_id,
        run_id=run_id,
        batch_id=rca_response.affected_batch,
        stage=rca_response.affected_stage,
        rca_summary=rca_response.summary,
        evidence_ids=[e.evidence_id for e in pack.evidence],
        sla_status=sla_status,
        anomaly_type="SYSTEM_EVALUATION"
    )
    
    if alert:
        logger.info(f"Alert generated: Priority={alert.severity}, Type={alert.alert_type}")
    else:
        logger.info("No alert generated or deduplicated.")
        
    print("LIVE TELEMETRY TEST SUCCESSFUL")

if __name__ == "__main__":
    main()
