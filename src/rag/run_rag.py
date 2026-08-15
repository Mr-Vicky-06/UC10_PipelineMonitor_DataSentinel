import os
import pandas as pd
from typing import Dict, Any

from src.rag import DocumentRetriever, MockGenerator, IntentRouter, StructuredQueryEngine

class RAGPipeline:
    def __init__(self, docs_dir: str = "docs"):
        self.retriever = DocumentRetriever(docs_dir=docs_dir)
        # Using MockGenerator for MVP to avoid external dependencies
        self.generator = MockGenerator()
        self.router = IntentRouter()
        self.structured_engine = StructuredQueryEngine()

    def process_query(self, anomaly_event: Dict[str, Any], user_query: str = None) -> Dict[str, Any]:
        """
        Process a query about an anomaly event, or generate a standard explanation if no query.
        """
        response_type = "STANDARD_REPORT"
        if user_query:
            response_type = self.router.route(user_query)

        structured_ans = ""
        if response_type in ["STRUCTURED", "MIXED"]:
            structured_ans = self.structured_engine.answer(user_query, anomaly_event)

        rag_response = {
            "grounded_explanation": "NOT_AVAILABLE",
            "recommended_action": "NOT_AVAILABLE",
            "sources": "None",
            "retrieval_method": "NONE"
        }

        if response_type in ["RAG", "MIXED", "STANDARD_REPORT"]:
            # Retrieve knowledge
            docs = self.retriever.retrieve(
                anomaly_type=anomaly_event.get('anomaly_type'), 
                user_query=user_query
            )
            
            retrieval_method = docs[0].get('retrieval_method', 'NONE') if docs else "NONE"
            
            # Generate explanation
            rag_response = self.generator.generate(
                anomaly_event=anomaly_event,
                retrieved_docs=docs,
                user_query=user_query
            )
            rag_response['retrieval_method'] = retrieval_method

        # Combine answers
        final_explanation = ""
        if structured_ans:
            final_explanation += f"STRUCTURED DATA:\n{structured_ans}\n"
        if rag_response.get("grounded_explanation") != "NOT_AVAILABLE":
            final_explanation += rag_response.get("grounded_explanation")

        return {
            "anomaly_id": anomaly_event.get("anomaly_id", "UNKNOWN"),
            "user_query": user_query if user_query else "STANDARD EXPLANATION",
            "grounded_explanation": final_explanation.strip(),
            "recommended_action": rag_response.get("recommended_action"),
            "sources": rag_response.get("sources"),
            "retrieval_method": rag_response.get("retrieval_method", "NONE"),
            "response_type": response_type
        }

def run_batch_harness():
    """Event-driven RAG harness."""
    input_path = "outputs/anomaly/anomaly_assessment.parquet"
    output_dir = "outputs/rag"
    output_path = os.path.join(output_dir, "rag_responses.parquet")
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading assessments from {input_path}...")
    df = pd.read_parquet(input_path)
    
    # Prioritize events based on rules
    mask = (df['severity'].isin(['MEDIUM', 'HIGH', 'CRITICAL'])) | (df['SLA_status'] != 'MET')
    priority_df = df[mask]
    
    print(f"Processing {len(priority_df)} priority events...")
    
    pipeline = RAGPipeline()
    responses = []
    
    for _, row in priority_df.iterrows():
        event = row.to_dict()
        res = pipeline.process_query(event)
        responses.append(res)
        
    res_df = pd.DataFrame(responses)
    res_df.to_parquet(output_path, index=False)
    print(f"Saved RAG responses to {output_path}")
    return df, pipeline

if __name__ == "__main__":
    df, pipeline = run_batch_harness()
    
    print("\n--- VALIDATION QUERIES ---")
    
    # Grab one low severity to test Interactive Chatbot rule
    low_sev = df[(df['severity'] == 'LOW') & (df['SLA_status'] == 'MET')].iloc[0].to_dict()
    
    queries = [
        # Structured only
        ("What is the SLA status?", low_sev),
        # RAG only
        ("Why was this rule triggered and what procedure applies?", low_sev),
        # Mixed
        ("What is the severity, and has this type of issue occurred before?", low_sev),
        # Missing info
        ("Which specific beneficiary ID was affected?", low_sev)
    ]
    
    for q_text, event in queries:
        print(f"\nQuery: {q_text}")
        print("-" * 40)
        res = pipeline.process_query(event, user_query=q_text)
        print(f"Response Type: {res['response_type']}")
        print(f"Explanation:\n{res['grounded_explanation']}")
        print(f"Recommended Action: {res['recommended_action']}")
        print(f"Sources: {res['sources']}")
