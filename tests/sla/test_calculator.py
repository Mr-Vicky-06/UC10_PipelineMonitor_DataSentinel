import pytest
from src.sla.config import SLAConfig
from src.sla.calculator import SLACalculator

@pytest.fixture
def default_config():
    return SLAConfig(
        sla_id="test_sla_1",
        pipeline_name="uc10",
        stage="INGESTION",
        target_duration_seconds=100.0,
        warning_margin_seconds=20.0
    )

def test_sla_calculator_on_track(default_config):
    # 50 records in 10 seconds -> 5 records/sec
    # 100 expected, 50 remaining -> 10s remaining
    # Total ETA 20s. Deadline 100s. Threshold 80s.
    obs = SLACalculator.calculate(
        config=default_config,
        run_id="run_1",
        start_time=0.0,
        current_time=10.0,
        expected_records=100,
        processed_records=50,
        stage_status="RUNNING"
    )
    assert obs.status == "ON_TRACK"
    assert obs.estimated_completion_time == 20.0
    assert obs.estimated_remaining_seconds == 10.0
    assert obs.remaining_records == 50
    assert obs.throughput == 5.0

def test_sla_calculator_at_risk(default_config):
    # Deadline 100s. Warning 80s.
    # 10 records in 10 seconds -> 1 rec/sec
    # 100 expected, 90 remaining -> 90s remaining
    # ETA = 10 + 90 = 100s. (100 > 80, 100 <= 100) -> AT_RISK
    obs = SLACalculator.calculate(
        config=default_config,
        run_id="run_1",
        start_time=0.0,
        current_time=10.0,
        expected_records=100,
        processed_records=10,
        stage_status="RUNNING"
    )
    assert obs.status == "AT_RISK"
    assert obs.estimated_completion_time == 100.0

def test_sla_calculator_breached(default_config):
    # Deadline 100s
    # 1 record in 10 seconds -> 0.1 rec/sec
    # 100 expected, 99 remaining -> 990s remaining.
    # ETA = 1000s -> BREACHED
    obs = SLACalculator.calculate(
        config=default_config,
        run_id="run_1",
        start_time=0.0,
        current_time=10.0,
        expected_records=100,
        processed_records=1,
        stage_status="RUNNING"
    )
    assert obs.status == "BREACHED"
    assert obs.estimated_completion_time == 1000.0

def test_sla_calculator_zero_throughput(default_config):
    obs = SLACalculator.calculate(
        config=default_config,
        run_id="run_1",
        start_time=0.0,
        current_time=10.0,
        expected_records=100,
        processed_records=0,
        stage_status="RUNNING"
    )
    assert obs.status == "UNKNOWN"
    assert obs.throughput == 0.0

def test_sla_calculator_missing_info(default_config):
    obs = SLACalculator.calculate(
        config=default_config,
        run_id="run_1",
        start_time=0.0,
        current_time=10.0,
        expected_records=None,
        processed_records=10,
        stage_status="RUNNING"
    )
    assert obs.status == "UNKNOWN"

def test_sla_calculator_completed(default_config):
    obs = SLACalculator.calculate(
        config=default_config,
        run_id="run_1",
        start_time=0.0,
        current_time=50.0,
        expected_records=100,
        processed_records=100,
        stage_status="COMPLETED"
    )
    assert obs.status == "ON_TRACK"
    assert obs.remaining_records == 0
    assert obs.estimated_remaining_seconds == 0.0

def test_sla_calculator_failed(default_config):
    obs = SLACalculator.calculate(
        config=default_config,
        run_id="run_1",
        start_time=0.0,
        current_time=50.0,
        expected_records=100,
        processed_records=10,
        stage_status="FAILED"
    )
    assert obs.status == "UNKNOWN"
