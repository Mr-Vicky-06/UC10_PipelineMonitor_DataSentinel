import csv
import json

def get_delimiter(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        line = f.readline()
        if '|' in line: return '|'
        if '\t' in line: return '\t'
        return ','

def extract_fields(filepath):
    try:
        delim = get_delimiter(filepath)
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f, delimiter=delim)
            headers = next(reader)
            # Try to infer types from the first data row
            row = next(reader, None)
            fields = []
            for i, h in enumerate(headers):
                val = row[i] if row and i < len(row) else ""
                dtype = "Numeric" if val.replace('.','',1).isdigit() else "String"
                if "DT" in h or "DATE" in h: dtype = "Date"
                fields.append((h, dtype))
            return fields
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []

datasets = {
    "Beneficiary": "data/raw/beneficiary/beneficiary_2024.csv",
    "PDE": "data/raw/pde/pde.csv",
    "Inpatient Claims": "data/raw/claims/inpatient.csv",
    "Outpatient Claims": "data/raw/claims/outpatient.csv",
    "Carrier Claims": "data/raw/claims/carrier.csv"
}

print("Extracting fields...")
all_fields = {}
for name, path in datasets.items():
    all_fields[name] = extract_fields(path)

# Map fields to categories based on heuristics
def categorize_field(name, ds_name):
    name = name.upper()
    if name in ["BENE_ID", "CLM_ID", "PDE_ID"]: return "IDENTITY FIELDS"
    if "NPI" in name or "PRVDR" in name or "PRSCRBR" in name: return "PROVIDER FIELDS"
    if "NDC" in name or "DRUG" in name or "GNRC" in name or "BRND" in name: return "DRUG FIELDS"
    if "DT" in name or "DATE" in name: return "TEMPORAL FIELDS"
    if "AMT" in name or "CST" in name or "PMT" in name or "CHRG" in name: return "FINANCIAL FIELDS"
    if "CD" in name or "IND" in name or "STUS" in name: return "CATEGORICAL FIELDS"
    return "NUMERIC FIELDS" if "NUM" in name or "CNT" in name or "QTY" in name else "CATEGORICAL FIELDS"

md_content = """# 01 Available Fields

This document classifies all extracted fields from the raw CMS Synthetic datasets.

"""

for ds_name, fields in all_fields.items():
    md_content += f"## {ds_name}\n\n"
    md_content += "| Field | Type | Classification | Feature Potential |\n"
    md_content += "|---|---|---|---|\n"
    for f, dtype in fields:
        cat = categorize_field(f, ds_name)
        feat_pot = "High" if cat in ["TEMPORAL FIELDS", "FINANCIAL FIELDS", "NUMERIC FIELDS"] or "ID" in f else "Low"
        if f == "BENE_ID": feat_pot = "Critical Join Key"
        md_content += f"| `{f}` | {dtype} | {cat} | {feat_pot} |\n"
    md_content += "\n"

with open("docs/01_AVAILABLE_FIELDS.md", "w", encoding="utf-8") as out:
    out.write(md_content)

print("01_AVAILABLE_FIELDS.md generated.")
