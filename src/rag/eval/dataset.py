from pydantic import BaseModel, Field
from typing import List, Optional

class GoldenQuery(BaseModel):
    query_id: str
    query: str
    expected_intent: str
    expected_run_id: Optional[str]
    expected_batch_id: Optional[str]
    expected_severity: Optional[str]

class GoldenDataset(BaseModel):
    queries: List[GoldenQuery]
