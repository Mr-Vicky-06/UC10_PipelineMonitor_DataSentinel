import datetime
from dataclasses import dataclass
from typing import List, Optional
import polars as pl

@dataclass
class DiscoveredBatchSource:
    """Represents the metadata of a discovered batch file before reading."""
    source_file: str
    hospital_id: str
    batch_id: str
    service_date: datetime.date
    file_size: int
    file_format: str
    delimiter: str

@dataclass
class IngestedBatch:
    """
    Contract object produced by the ingestion layer.
    Passed downstream to the Validation layer.
    """
    batch_id: str
    hospital_id: str
    source_file: str
    service_date: datetime.date
    ingestion_timestamp: datetime.datetime
    records_in: int
    dataframe: pl.DataFrame
    source_format: str
    source_delimiter: str
    source_columns: List[str]
    ingestion_status: str
