import os
import shutil

categories = {
    'architecture': [
        '03_ARCHITECTURE_A_B_COMPARISON.md',
        '06_RECOMMENDED_DATA_ARCHITECTURE.md',
        '07_UC10_MINIMUM_DATA_MODEL.md',
        '08_DATASET_UC10_CAPABILITY_MATRIX.md',
        '02_DATASET_RELATIONSHIP_ANALYSIS.md',
        '04_CROSS_DATASET_RELATIONSHIPS.md'
    ],
    'data_profiling': [
        '01_DATASET_INVENTORY.md',
        '02_KEY_AND_GRAIN_ANALYSIS.md',
        '04_INFORMATION_LOSS_ANALYSIS.md',
        '05_UC10_DATASET_SUITABILITY_MATRIX.md',
        '03_UC10_DQ_RULE_CATALOG.md',
        '02_RELATIONSHIP_VALIDATION.md'
    ],
    'feature_engineering': [
        'FINAL_ML_FEATURE_SET.md',
        '05_ISOLATION_FOREST_FEATURE_MATRIX.md',
        '01_AVAILABLE_FIELDS.md',
        '05_FEATURE_ENGINEERING_ARCHITECTURE.md',
        'feature_engineering_summary.md'
    ],
    'anomaly_detection': [
        'PRE_ANOMALY_DETECTION_AUDIT.md',
        '06_EVIDENCE_FUSION_DESIGN.md',
        '07_RCA_EVIDENCE_MAP.md',
        '08_ANOMALY_DEMONSTRATION_PLAN.md'
    ],
    'project_management': [
        'EXECUTIVE_SUMMARY.md',
        '09_DATASET_ANALYSIS_EXECUTIVE_SUMMARY.md',
        '09_TWO_DAY_IMPLEMENTATION_PLAN.md',
        '02_UC10_ANOMALY_FRAMEWORK.md',
        '03_UC10_RAG_SCOPE.md',
        '01_UC10_MASTER_KNOWLEDGE.md'
    ],
    'literature': [
        'UC10_Literature_Review_1.md'
    ]
}

# Create category folders in docs/
for cat in categories.keys():
    os.makedirs(os.path.join('docs', cat), exist_ok=True)

def move_to_category(filename, source_dir):
    src_path = os.path.join(source_dir, filename)
    if not os.path.exists(src_path): return False
    
    for cat, files in categories.items():
        if filename in files:
            shutil.move(src_path, os.path.join('docs', cat, filename))
            return True
            
    # If not explicitly categorized but is markdown, put in project_management as fallback
    if filename.endswith('.md'):
        shutil.move(src_path, os.path.join('docs', 'project_management', filename))
        return True
    return False

# Move from docs/ root
for item in os.listdir('docs'):
    if os.path.isfile(os.path.join('docs', item)):
        move_to_category(item, 'docs')

# Move from data analysis/
if os.path.exists('data analysis'):
    for item in os.listdir('data analysis'):
        if os.path.isfile(os.path.join('data analysis', item)):
            move_to_category(item, 'data analysis')
        elif os.path.isdir(os.path.join('data analysis', item)):
            # Move subfolders
            if item in ['anomaly_scenarios', 'dq_results']:
                shutil.move(os.path.join('data analysis', item), os.path.join('docs', 'anomaly_detection', item))
            elif item in ['dataset_profiles', 'feature_analysis']:
                shutil.move(os.path.join('data analysis', item), os.path.join('docs', 'data_profiling', item))
                
# Remove old data analysis if empty
if os.path.exists('data analysis') and not os.listdir('data analysis'):
    os.rmdir('data analysis')

print("Documentation organized successfully.")
