# Technology Stack

The currently approved technology direction:

- **Programming:** Python
- **Data processing:** Polars (Pandas where compatibility is required)
- **Storage:** Parquet, DuckDB
- **Validation:** Pandera
- **Containerization:** Docker
- **Orchestration:** Airflow OR Dagster (subject to final pipeline-design decision)
- **Telemetry:** OpenTelemetry
- **Metrics:** Prometheus
- **Visualization:** Grafana
- **Testing:** Pytest
- **Version control:** Git + GitHub
- **CI/CD:** GitHub Actions
- **Anomaly detection:** scikit-learn, SciPy
- **RCA / graph:** NetworkX where appropriate

**Important Constraint:** Do NOT introduce Kubernetes, Firebase, or another technology merely because it is available. A technology must have a demonstrated architectural purpose.
