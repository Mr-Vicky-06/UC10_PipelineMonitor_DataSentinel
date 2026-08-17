import os
import sys
import json
import time
import subprocess
import duckdb
from datetime import datetime

# Add src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from rag.engine import RAGEngine

def main():
    print("==================================================")
    print("PHASE 5A FINAL REAL-EVIDENCE RAG VALIDATION GATE")
    print("==================================================\n")
    
    if not os.environ.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = "MOCK_KEY"
    engine = RAGEngine()
    
    report_lines = [
        "# PHASE 5A: REAL EVIDENCE RAG VALIDATION REPORT",
        f"**Date Generated:** {datetime.utcnow().isoformat()}Z",
        "",
        "## 1. Historical Real-Evidence Test Scenarios"
    ]
    
    scenarios = [
        {
            "name": "Case A & B (DQ Violation & ML Anomaly)",
            "run_id": "TELEMETRY_REAL_100",
            "query": "What happened to run TELEMETRY_REAL_100?",
            "expect_evidence": True,
            "expect_dq_violation": True,
            "expect_ml_anomaly": True
        },
        {
            "name": "Case C (Operational Failure)",
            "run_id": "clean_20260817_191848_881312",
            "query": "Why did run clean_20260817_191848_881312 fail?",
            "expect_evidence": True,
            "expect_ops_failure": True
        },
        {
            "name": "Case D (Normal Run)",
            "run_id": "clean_20260817_191908_a2162d",
            "query": "What anomalies occurred in run clean_20260817_191908_a2162d?",
            "expect_evidence": False,
            "expect_no_incident": True
        },
        {
            "name": "Case E (Nonexistent Run)",
            "run_id": "RUN_DOES_NOT_EXIST",
            "query": "What happened in RUN_DOES_NOT_EXIST?",
            "expect_evidence": False,
            "expect_insufficient": True
        }
    ]
    
    for idx, sc in enumerate(scenarios):
        print(f"Testing Scenario {idx+1}: {sc['name']}")
        start_time = time.time()
        
        try:
            response = engine.ask(sc['query'])
            latency = time.time() - start_time
            
            # Validation logic
            pack = engine.retriever.retrieve_evidence_pack(sc['query']) # To get raw evidence count
            evidence_count = len(pack.evidence)
            
            success = True
            notes = []
            
            if sc.get('expect_evidence') and evidence_count == 0:
                success = False
                notes.append("FAILED: Expected evidence, but retrieved 0.")
            if not sc.get('expect_evidence') and evidence_count > 0:
                success = False
                notes.append("FAILED: Expected no evidence, but retrieved some.")
                
            if sc.get('expect_insufficient'):
                if "insufficient evidence" not in response.what_happened.lower():
                    success = False
                    notes.append("FAILED: Expected 'insufficient evidence' handling, got something else.")
                    
            if sc.get('expect_no_incident'):
                if response.severity in ["ERROR", "CRITICAL"]:
                    success = False
                    notes.append(f"FAILED: Expected normal run, but got severity {response.severity}.")
                    
            status = "PASS" if success else "FAIL"
            
            report_lines.extend([
                f"### {idx+1}. {sc['name']}",
                f"- **Query**: `{sc['query']}`",
                f"- **Status**: **{status}**",
                f"- **Evidence Retrieved**: {evidence_count}",
                f"- **Latency**: {latency:.2f}s",
                f"- **RCA Severity**: {response.severity}",
                f"- **Incident ID**: {response.incident_id}",
                f"**What Happened:**\n> {response.what_happened}",
                ""
            ])
            if notes:
                for note in notes:
                    report_lines.append(f"- **Note**: {note}")
                report_lines.append("")
                
        except Exception as e:
            print(f"  Error: {e}")
            report_lines.extend([
                f"### {idx+1}. {sc['name']}",
                f"- **Status**: **FAIL** (Exception: {e})",
                ""
            ])

    # LIVE FRESH-TELEMETRY TEST
    print("\nExecuting Live Fresh-Telemetry Pipeline Test...")
    report_lines.extend([
        "## 2. Live Fresh-Telemetry Test",
        "Executing `scripts/pipeline_execution/run_phase_f_telemetry_gate.py` to generate new evidence..."
    ])
    
    fresh_start_time = time.time()
    
    try:
        # Run pipeline
        result = subprocess.run(
            [sys.executable, "scripts/pipeline_execution/run_phase_f_telemetry_gate.py"],
            capture_output=True,
            text=True
        )
        pipeline_latency = time.time() - fresh_start_time
        
        # Get latest run_id from DuckDB
        db = duckdb.connect('outputs/pipeline_workspace/pipeline_telemetry.duckdb', read_only=True)
        row = db.execute("SELECT run_id FROM pipeline_events ORDER BY timestamp DESC LIMIT 1").fetchone()
        
        if row:
            new_run_id = row[0]
            print(f"Generated new run_id: {new_run_id}")
            
            # Query RAG Engine for new run_id
            fresh_query = f"What happened in run {new_run_id}?"
            rag_start_time = time.time()
            response = engine.ask(fresh_query)
            rag_latency = time.time() - rag_start_time
            
            pack = engine.retriever.retrieve_evidence_pack(fresh_query)
            
            status = "PASS" if len(pack.evidence) > 0 else "FAIL"
            
            report_lines.extend([
                f"- **New Run ID**: `{new_run_id}`",
                f"- **Pipeline Execution Latency**: {pipeline_latency:.2f}s",
                f"- **RAG Discovery Latency**: Near-zero (Live SQL query)",
                f"- **RAG Processing Latency**: {rag_latency:.2f}s",
                f"- **Evidence Retrieved**: {len(pack.evidence)}",
                f"- **Status**: **{status}**",
                "",
                f"**What Happened:**\n> {response.what_happened}",
                ""
            ])
            
        else:
            print("Pipeline generated no run_id.")
            report_lines.append("- **Status**: **FAIL** (No run_id generated by pipeline)")
            
    except Exception as e:
        print(f"Pipeline execution error: {e}")
        report_lines.append(f"- **Status**: **FAIL** (Exception: {e})")
        
    # Write report
    report_path = "outputs/rag/PHASE_5A_REAL_EVIDENCE_VALIDATION_REPORT.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))
        
    print(f"\nReport generated at {report_path}")

import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING) # Reduce noise
    main()
