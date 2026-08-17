from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np

class BaseModel(ABC):
    """
    Abstract base class for all AI/ML detection models.
    """
    
    def __init__(self, feature_columns: List[str], **hyperparameters):
        self.feature_columns = feature_columns
        self.hyperparameters = hyperparameters
        self.is_trained = False
        
    @abstractmethod
    def fit(self, df_train: pd.DataFrame) -> None:
        """
        Train the model on historical baseline data.
        """
        pass
        
    @abstractmethod
    def predict(self, df_test: pd.DataFrame) -> pd.DataFrame:
        """
        Predict anomalies on test data.
        Returns a DataFrame with identical rows to df_test, plus:
        - is_anomaly (bool)
        - anomaly_score (float)
        - expected_value (float, optional)
        - baseline_value (float, optional)
        """
        pass
        
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "model_class": self.__class__.__name__,
            "features": self.feature_columns,
            "hyperparameters": self.hyperparameters,
            "is_trained": self.is_trained
        }
