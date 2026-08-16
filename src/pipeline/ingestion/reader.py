import datetime
import polars as pl
from .models import DiscoveredBatchSource, IngestedBatch
from .errors import FileFormatError

class BatchReader:
    """
    Reads CSV files into Polars DataFrames while preserving the exact source schema.
    """
    @staticmethod
    def read(source: DiscoveredBatchSource) -> IngestedBatch:
        """
        Reads the discovered source file into an IngestedBatch contract.
        All columns are explicitly read as String types to prevent silent business-level transformations.
        """
        ingestion_timestamp = datetime.datetime.now()

        try:
            # infer_schema_length=0 forces all columns to be read as Pl.String, 
            # fulfilling the "preserve source representation" rule.
            df = pl.read_csv(
                source.source_file,
                separator=source.delimiter,
                infer_schema_length=0,
                null_values=["", "NA", "NULL"]
            )
        except Exception as e:
            # Catch polars parsing errors (e.g. malformed delimiter)
            raise FileFormatError(f"Failed to read file {source.source_file}: {e}")

        records_in = df.height
        source_columns = df.columns

        return IngestedBatch(
            batch_id=source.batch_id,
            hospital_id=source.hospital_id,
            source_file=source.source_file,
            service_date=source.service_date,
            ingestion_timestamp=ingestion_timestamp,
            records_in=records_in,
            dataframe=df,
            source_format=source.file_format,
            source_delimiter=source.delimiter,
            source_columns=source_columns,
            ingestion_status="SUCCESS"
        )
