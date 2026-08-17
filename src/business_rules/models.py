from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import pandas as pd
from datetime import datetime

class RuleStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"
    AUTHORIZED = "AUTHORIZED"
    NO_AUTHORIZATION = "NO_AUTHORIZATION"
    EXPIRED_AUTHORIZATION = "EXPIRED_AUTHORIZATION"
    NOT_YET_EFFECTIVE = "NOT_YET_EFFECTIVE"
    INVALID_STATUS = "INVALID_STATUS"
    AMBIGUOUS_AUTH = "AMBIGUOUS_AUTH"

class RuleSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class BusinessRuleViolation:
    rule_id: str
    rule_name: str
    clm_id: str
    clm_line_num: str
    severity: str
    status: str
    message: str
    field_values: Dict[str, Any]

@dataclass
class BusinessRuleResult:
    dataframe: pd.DataFrame
    violations: List[BusinessRuleViolation]
    execution_timestamp: str
    metrics: Dict[str, Any]
    status: str
