import pandas as pd
import numpy as np
import joblib
import time
import warnings

warnings.filterwarnings('ignore', category=UserWarning)
from src.ml.models.v2.candidates import EWMAVolumeModel, KSDistributionModel, SklearnOperationalModel

def test_performance_and_stability():
    print("=== MODEL STABILITY AND PERFORMANCE TEST ===")
    
    test_df = pd.read_csv('outputs/ml/acceptance/data/test.csv')
    
    models = {
        "VOLUME": joblib.load('outputs/ml/models/v2/volume_ewma_v2.joblib'),
        "OPERATIONAL": joblib.load('outputs/ml/models/v2/operational_isolationforest_v2.joblib'),
        "DISTRIBUTION": joblib.load('outputs/ml/models/v2/distribution_ks_v2.joblib')
    }
    
    print("\n--- STABILITY TEST ---")
    # Run 5 times and check if output is exactly identical
    for domain, model in models.items():
        preds_1 = model.predict(test_df)
        preds_2 = model.predict(test_df)
        preds_3 = model.predict(test_df)
        
        if np.array_equal(preds_1, preds_2) and np.array_equal(preds_2, preds_3):
            print(f"{domain} Model: STABLE (Deterministic across 3 runs)")
        else:
            print(f"{domain} Model: UNSTABLE (Non-deterministic output detected)")

    print("\n--- PERFORMANCE TEST ---")
    # We will simulate 10, 100, 1000 batches by repeating the test dataset
    
    # 10 batches (approx length of test_df is 200, so 10 is length 10)
    sizes = [10, 100, 1000]
    
    for domain, model in models.items():
        print(f"\n{domain} Performance:")
        for size in sizes:
            # Create a dataframe of `size` batches
            df_perf = test_df.sample(n=size, replace=True, random_state=42)
            
            start_time = time.time()
            model.predict(df_perf)
            end_time = time.time()
            
            total_latency_ms = (end_time - start_time) * 1000
            per_batch_latency_ms = total_latency_ms / size
            
            print(f"  {size} batches -> Total: {total_latency_ms:.2f}ms | Per-Batch: {per_batch_latency_ms:.4f}ms")

if __name__ == "__main__":
    test_performance_and_stability()
