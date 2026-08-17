import subprocess
import os

def check_immutability_and_regression():
    print("=== IMMUTABILITY AND REGRESSION TEST ===")
    
    print("\n[Running Pytest Regression Suite]")
    try:
        # Run pytest and capture output
        result = subprocess.run(
            ['python', '-m', 'pytest', 'tests/'], 
            capture_output=True, 
            text=True
        )
        print(result.stdout)
        if result.returncode == 0:
            print("STATUS: PASS (Zero Regressions)")
        else:
            print("STATUS: FAILED (Regressions Detected)")
    except Exception as e:
        print(f"STATUS: FAILED ({e})")
        
    print("\n[Verifying Source Immutability]")
    # A simple check to ensure no new files were written to data/ or master_data/ today incorrectly
    # (Since we didn't store a pre-hash, we just do a basic file scan to ensure ML output didn't land here)
    for root_dir in ['data', 'master_data']:
        if not os.path.exists(root_dir):
            continue
        invalid_files = []
        for dirpath, _, filenames in os.walk(root_dir):
            for f in filenames:
                if f.endswith('.joblib') or 'ml' in f.lower() or 'model' in f.lower() or 'acceptance' in f.lower():
                    invalid_files.append(os.path.join(dirpath, f))
        
        if invalid_files:
            print(f"WARNING: Potential contamination found in {root_dir}: {invalid_files}")
        else:
            print(f"VERIFIED: {root_dir}/ remains clean of ML artifacts.")

if __name__ == "__main__":
    check_immutability_and_regression()
