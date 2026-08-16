"""
Schema loader for loading centralized schema definitions.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union
import yaml

from .models import FieldSchema, SchemaContract


def load_schema_from_dict(data: Dict[str, Any]) -> SchemaContract:
    """Instantiate a SchemaContract from a raw dictionary."""
    fields_dict: Dict[str, FieldSchema] = {}
    for f in data.get("fields", []):
        field_schema = FieldSchema(
            name=f["name"],
            type=f.get("type", "string").lower(),
            required=f.get("required", True),
            nullable=f.get("nullable", False),
            date_formats=f.get("date_formats", []),
            allowed_values=f.get("allowed_values"),
            description=f.get("description", ""),
        )
        fields_dict[field_schema.name] = field_schema

    return SchemaContract(
        dataset_name=data.get("dataset_name", "unknown"),
        version=data.get("version", "1.0.0"),
        description=data.get("description", ""),
        primary_key=data.get("primary_key", []),
        default_delimiter=data.get("default_delimiter", ","),
        allow_additional_columns=data.get("allow_additional_columns", True),
        strict_mode=data.get("strict_mode", False),
        fields=fields_dict,
    )


def load_schema_from_yaml(file_path: Union[str, Path]) -> SchemaContract:
    """Load and parse a YAML schema definition file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found at: {path.resolve()}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid schema file format in {path}: expected YAML mapping")

    return load_schema_from_dict(data)


def load_schema_by_name(dataset_name: str, schemas_dir: Optional[Union[str, Path]] = None) -> SchemaContract:
    """
    Find and load a schema by dataset name (e.g., 'claims', 'authorization')
    from the default or specified schemas directory.
    """
    if schemas_dir is None:
        # Default to configs/schemas relative to project root
        schemas_dir = Path(__file__).resolve().parent.parent.parent / "configs" / "schemas"
    else:
        schemas_dir = Path(schemas_dir)

    yaml_candidates = [
        schemas_dir / f"{dataset_name}_schema.yaml",
        schemas_dir / f"{dataset_name}_schema.yml",
        schemas_dir / f"{dataset_name}.yaml",
        schemas_dir / f"{dataset_name}.yml",
    ]

    for candidate in yaml_candidates:
        if candidate.exists():
            return load_schema_from_yaml(candidate)

    raise FileNotFoundError(
        f"Could not locate schema for dataset '{dataset_name}' in {schemas_dir}. "
        f"Checked candidates: {[str(c) for c in yaml_candidates]}"
    )
