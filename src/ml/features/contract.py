from typing import List, Dict, Any

class FeatureContract:
    """
    Defines the standard 18-feature contract for the AI/ML detection layer.
    """
    
    # Complete 18-feature list
    FEATURES = [
        "claim_volume",
        "beneficiary_volume",
        "provider_volume",
        "duplicate_rate",
        "null_rate",
        "invalid_format_rate",
        "logic_failure_rate",
        "claim_amount_total",
        "claim_amount_mean",
        "claim_amount_median",
        "processing_duration",
        "throughput",
        "failure_rate",
        "pde_count",
        "claim_pde_ratio",
        "median_rx_cost",
        "median_days_supply",
        "backlog"
    ]
    
    # Features explicitly missing from the source dataset
    UNAVAILABLE_FEATURES = {
        "pde_count": "No PDE data in source (inpatient claims only).",
        "claim_pde_ratio": "No PDE data in source.",
        "median_rx_cost": "No Rx cost data in source.",
        "median_days_supply": "No Rx days supply in source.",
        "backlog": "Not tracked by orchestrator."
    }
    
    @classmethod
    def get_available_features(cls) -> List[str]:
        """Return the list of features that can be legitimately computed."""
        return [f for f in cls.FEATURES if f not in cls.UNAVAILABLE_FEATURES]

    @classmethod
    def get_feature_matrix(cls) -> List[Dict[str, Any]]:
        """Return a structured feature availability matrix for reporting."""
        matrix = []
        for feature in cls.FEATURES:
            available = feature not in cls.UNAVAILABLE_FEATURES
            matrix.append({
                "feature": feature,
                "available": available,
                "training_ready": available,
                "used_by_model": available,
                "reason_if_excluded": cls.UNAVAILABLE_FEATURES.get(feature, "")
            })
        return matrix
