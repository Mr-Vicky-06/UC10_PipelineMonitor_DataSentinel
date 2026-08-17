import duckdb
import os
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class ReadOnlyDuckDBClient:
    """
    Provides strictly read-only access to the three authoritative DuckDB instances:
    1. pipeline_telemetry.duckdb
    2. processed_claims.duckdb
    3. metrics_repository.duckdb
    """
    
    def __init__(self, workspace_dir: str = "outputs/pipeline_workspace"):
        self.workspace_dir = workspace_dir
        
        self.telemetry_db_path = os.path.join(workspace_dir, "pipeline_telemetry.duckdb")
        self.claims_db_path = os.path.join(workspace_dir, "processed_claims.duckdb")
        self.metrics_db_path = os.path.join(workspace_dir, "metrics_repository.duckdb")
        
        # We don't keep long-running connections by default to avoid locks,
        # but we can provide helper methods that open read-only connections.
        
    def _execute_read_only(self, db_path: str, query: str, parameters: tuple = ()) -> List[Dict[str, Any]]:
        """
        Executes a parameterized query against a DuckDB database in read-only mode.
        """
        if not os.path.exists(db_path):
            logger.warning(f"Database not found: {db_path}")
            return []
            
        try:
            # Note: DuckDB's read_only flag ensures no modifications can happen
            with duckdb.connect(db_path, read_only=True) as conn:
                # Convert results to a list of dicts
                cursor = conn.execute(query, parameters)
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return results
        except Exception as e:
            logger.error(f"Error executing read-only query on {db_path}: {str(e)}")
            raise
            
    def query_telemetry(self, query: str, parameters: tuple = ()) -> List[Dict[str, Any]]:
        return self._execute_read_only(self.telemetry_db_path, query, parameters)
        
    def query_claims(self, query: str, parameters: tuple = ()) -> List[Dict[str, Any]]:
        return self._execute_read_only(self.claims_db_path, query, parameters)
        
    def query_metrics(self, query: str, parameters: tuple = ()) -> List[Dict[str, Any]]:
        return self._execute_read_only(self.metrics_db_path, query, parameters)

