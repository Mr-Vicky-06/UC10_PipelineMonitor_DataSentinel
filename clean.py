import os
import shutil

dirs_to_create = [
    'data/raw/beneficiary',
    'data/raw/claims',
    'data/raw/pde',
    'data/optional/provider_drug',
    'data/supporting/puf',
    'data/features',
    'src/features',
    'configs',
    'outputs/profiling',
    'outputs/features',
    'outputs/anomaly',
    'docs/architecture_analysis',
    'tests',
    'archive/scratch'
]

for d in dirs_to_create:
    os.makedirs(d, exist_ok=True)

def move_files(src_dir, dest_dir):
    if not os.path.exists(src_dir): return
    for item in os.listdir(src_dir):
        s = os.path.join(src_dir, item)
        d = os.path.join(dest_dir, item)
        if not os.path.exists(d):
            shutil.move(s, d)

# Move datasets
move_files('DataBase/Beneficiary', 'data/raw/beneficiary')
move_files('DataBase/Claims', 'data/raw/claims')
if os.path.exists('DataBase/pde.csv') and not os.path.exists('data/raw/pde/pde.csv'):
    shutil.move('DataBase/pde.csv', 'data/raw/pde/pde.csv')
move_files('DataBase/Medicare Part D Prescribers - by Provider and Drug/2024', 'data/optional/provider_drug')
move_files('DataBase/puf', 'data/supporting/puf')

# Move scratch
move_files('scratch', 'archive/scratch')

# Remove image
if os.path.exists('ChatGPT Image Aug 14, 2026, 01_23_24 PM.png'):
    os.remove('ChatGPT Image Aug 14, 2026, 01_23_24 PM.png')

# Move markdown files
for item in os.listdir('.'):
    if item.endswith('.md') and item not in ['00_PROJECT_CLEANUP_REPORT.md', '00_CLEANUP_MANIFEST.md']:
        shutil.move(item, os.path.join('docs', item))

print("Cleanup script completed successfully via Python.")
