"""
Configuration loader for the Data Cleaning Module.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union
import yaml

from .models import CleaningConfig


def load_cleaning_config_from_dict(data: Dict[str, Any]) -> CleaningConfig:
    """Instantiate a CleaningConfig from a dictionary."""
    return CleaningConfig(
        dataset_name=data.get("dataset_name", "unknown"),
        version=data.get("version", "1.1.0"),
        description=data.get("description", ""),
        null_representations=data.get(
            "null_representations",
            ["", " ", "NULL", "null", "None", "NONE", "N/A", "NA", "NaN", "nan", "."],
        ),
        canonical_null=data.get("canonical_null", ""),
        mandatory_fields=data.get("mandatory_fields", []),
        canonical_date_format=data.get("canonical_date_format", "%Y-%m-%d"),
        accepted_date_formats=data.get(
            "accepted_date_formats",
            ["%d-%b-%Y", "%Y-%m-%d", "%Y%m%d"],
        ),
        date_fields=data.get("date_fields", []),
        identifier_fields=data.get("identifier_fields", []),
        code_fields=data.get("code_fields", []),
        numeric_fields=data.get("numeric_fields", []),
        categorical_fields=data.get("categorical_fields", []),
        free_text_fields=data.get("free_text_fields", []),
        primary_key=data.get("primary_key", []),
        output_delimiter=data.get("output_delimiter", ","),
    )


def load_cleaning_config(file_path: Union[str, Path]) -> CleaningConfig:
    """Load a YAML cleaning configuration file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Cleaning config file not found at: {path.resolve()}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid cleaning config in {path}: expected YAML mapping")

    return load_cleaning_config_from_dict(data)


def load_cleaning_config_by_name(
    dataset_name: str, config_dir: Optional[Union[str, Path]] = None
) -> CleaningConfig:
    """Find and load cleaning configuration by dataset name."""
    if config_dir is None:
        config_dir = Path(__file__).resolve().parent.parent.parent / "configs" / "cleaning"
    else:
        config_dir = Path(config_dir)

    candidates = [
        config_dir / f"{dataset_name}_cleaning.yaml",
        config_dir / f"{dataset_name}_cleaning.yml",
        config_dir / f"{dataset_name}.yaml",
        config_dir / f"{dataset_name}.yml",
    ]

    for candidate in candidates:
        if candidate.exists():
            return load_cleaning_config(candidate)

    raise FileNotFoundError(
        f"Could not locate cleaning config for dataset '{dataset_name}' in {config_dir}. "
        f"Checked candidates: {[str(c) for c in candidates]}"
    )
