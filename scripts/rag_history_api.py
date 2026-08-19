import pandas as pd
import json
import sys
import argparse
import os

def load_history(limit=50, offset=0):
    try:
        rag_path = 'outputs/rag/rag_responses.parquet'
        anomaly_path = 'outputs/anomaly/anomaly_events.parquet'
        
        if not os.path.exists(rag_path):
            return json.dumps({"status": "error", "reason": "RAG history file not found."})
            
        df_rag = pd.read_parquet(rag_path)
        
        # Load anomaly events to join for metadata
        if os.path.exists(anomaly_path):
            df_anomaly = pd.read_parquet(anomaly_path)
            # Merge on anomaly_id
            df_merged = pd.merge(df_rag, df_anomaly[['anomaly_id', 'window_date', 'dataset', 'anomaly_type', 'severity']], on='anomaly_id', how='left')
        else:
            df_merged = df_rag
            df_merged['window_date'] = None
            df_merged['dataset'] = "UNKNOWN"
            df_merged['anomaly_type'] = "UNKNOWN"
            df_merged['severity'] = "UNKNOWN"
            
        # Convert window_date to string
        if 'window_date' in df_merged.columns:
            df_merged['window_date'] = df_merged['window_date'].dt.strftime('%Y-%m-%dT%H:%M:%SZ').fillna("UNKNOWN")
        
        # Apply pagination
        total = len(df_merged)
        df_paged = df_merged.iloc[offset:offset+limit]
        
        # Fill nan to prevent JSON serialization errors
        df_paged = df_paged.fillna("UNKNOWN")
        records = df_paged.to_dict(orient='records')
        
        return json.dumps({
            "status": "success",
            "total": total,
            "data": records
        })
    except Exception as e:
        return json.dumps({"status": "error", "reason": str(e)})

def load_detail(anomaly_id):
    try:
        rag_path = 'outputs/rag/rag_responses.parquet'
        anomaly_path = 'outputs/anomaly/anomaly_events.parquet'
        
        if not os.path.exists(rag_path):
            return json.dumps({"status": "error", "reason": "RAG history file not found."})
            
        df_rag = pd.read_parquet(rag_path)
        record_rag = df_rag[df_rag['anomaly_id'] == anomaly_id]
        
        if record_rag.empty:
             return json.dumps({"status": "error", "reason": "Analysis not found for provided anomaly_id."})
             
        record_dict = record_rag.iloc[0].fillna("UNKNOWN").to_dict()
        
        # Append context if available
        if os.path.exists(anomaly_path):
            df_anomaly = pd.read_parquet(anomaly_path)
            anomaly_ctx = df_anomaly[df_anomaly['anomaly_id'] == anomaly_id]
            if not anomaly_ctx.empty:
                ctx_dict = anomaly_ctx.iloc[0].fillna("UNKNOWN").to_dict()
                if ctx_dict.get('window_date') and ctx_dict.get('window_date') != "UNKNOWN":
                     ctx_dict['window_date'] = ctx_dict['window_date'].strftime('%Y-%m-%dT%H:%M:%SZ')
                record_dict['context'] = ctx_dict
        
        return json.dumps({
            "status": "success",
            "data": record_dict
        })
        
    except Exception as e:
        return json.dumps({"status": "error", "reason": str(e)})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["history", "detail"], required=True)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--id", type=str)
    
    args = parser.parse_args()
    
    if args.action == "history":
        print(load_history(args.limit, args.offset))
    elif args.action == "detail":
        if not args.id:
            print(json.dumps({"status": "error", "reason": "Missing ID parameter"}))
        else:
            print(load_detail(args.id))
