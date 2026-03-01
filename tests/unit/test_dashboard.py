"""Unit tests for monitoring dashboard data provider."""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.database.models import Base, MetricsModel, ResourceModel
from packages.monitoring.dashboard import (
    Alert,
    CurrentMetrics,
    HistoricalMetrics,
    ResourceHealth,
    TimeRange,
    get_alerts,
    get_current_metrics,
    get_historical_metrics,
    get_resource_health,
)


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def sample_resource(db_session):
    """Create a sample resource in the database."""
    resource_id = str(uuid.uuid4())
    resource = ResourceModel(
        id=resource_id,
        provision_id=str(uuid.uuid4()),
        resource_type="vm",
        external_id="ext-123",
        status="running",
        connection_info_json="{}",
        created_at=datetime.utcnow(),
    )
    db_session.add(resource)
    db_session.commit()
    return resource_id


def test_get_current_metrics_with_existing_metrics(db_session, sample_resource):
    """Test get_current_metrics returns latest metrics for a resource."""
    # Create metrics
    now = datetime.utcnow()
    metric = MetricsModel(
        id=str(uuid.uuid4()),
        resource_id=sample_resource,
        timestamp=now,
        cpu_percent=45.5,
        memory_percent=60.2,
        storage_used_gb=100.0,
        storage_iops=1000.0,
        network_in_mbps=10.5,
        network_out_mbps=8.3,
    )
    db_session.add(metric)
    db_session.commit()

    # Get current metrics
    result = get_current_metrics(sample_resource, db_session)

    # Verify
    assert isinstance(result, CurrentMetrics)
    assert result.resource_id == sample_resource
    assert result.cpu_percent == 45.5
    assert result.memory_percent == 60.2
    assert result.network_mbps == 18.8  # 10.5 + 8.3
    assert result.timestamp == now


def test_get_current_metrics_returns_most_recent(db_session, sample_resource):
    """Test get_current_metrics returns the most recent metric when multiple exist."""
    # Create older metric
    old_time = datetime.utcnow() - timedelta(minutes=5)
    old_metric = MetricsModel(
        id=str(uuid.uuid4()),
        resource_id=sample_resource,
        timestamp=old_time,
        cpu_percent=30.0,
        memory_percent=40.0,
        storage_used_gb=50.0,
        storage_iops=500.0,
        network_in_mbps=5.0,
        network_out_mbps=5.0,
    )
    db_session.add(old_metric)

    # Create newer metric
    new_time = datetime.utcnow()
    new_metric = MetricsModel(
        id=str(uuid.uuid4()),
        resource_id=sample_resource,
        timestamp=new_time,
        cpu_percent=75.0,
        memory_percent=80.0,
        storage_used_gb=150.0,
        storage_iops=2000.0,
        network_in_mbps=20.0,
        network_out_mbps=15.0,
    )
    db_session.add(new_metric)
    db_session.commit()

    # Get current metrics
    result = get_current_metrics(sample_resource, db_session)

    # Verify it returns the newer metric
    assert result.cpu_percent == 75.0
    assert result.memory_percent == 80.0
    assert result.timestamp == new_time


def test_get_current_metrics_no_metrics_raises_error(db_session, sample_resource):
    """Test get_current_metrics raises ValueError when no metrics exist."""
    with pytest.raises(ValueError, match="No metrics found"):
        get_current_metrics(sample_resource, db_session)


def test_get_current_metrics_nonexistent_resource(db_session):
    """Test get_current_metrics with nonexistent resource."""
    fake_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="No metrics found"):
        get_current_metrics(fake_id, db_session)


def test_get_historical_metrics_one_hour(db_session, sample_resource):
    """Test get_historical_metrics retrieves metrics for 1 hour time range."""
    now = datetime.utcnow()

    # Create metrics within 1 hour
    for i in range(3):
        metric = MetricsModel(
            id=str(uuid.uuid4()),
            resource_id=sample_resource,
            timestamp=now - timedelta(minutes=i * 20),
            cpu_percent=50.0 + i,
            memory_percent=60.0 + i,
            storage_used_gb=100.0,
            storage_iops=1000.0,
            network_in_mbps=10.0,
            network_out_mbps=10.0,
        )
        db_session.add(metric)

    # Create metric outside 1 hour (should not be included)
    old_metric = MetricsModel(
        id=str(uuid.uuid4()),
        resource_id=sample_resource,
        timestamp=now - timedelta(hours=2),
        cpu_percent=10.0,
        memory_percent=10.0,
        storage_used_gb=50.0,
        storage_iops=500.0,
        network_in_mbps=5.0,
        network_out_mbps=5.0,
    )
    db_session.add(old_metric)
    db_session.commit()

    # Get historical metrics
    result = get_historical_metrics(sample_resource, TimeRange.ONE_HOUR, db_session)

    # Verify
    assert isinstance(result, HistoricalMetrics)
    assert result.resource_id == sample_resource
    assert result.time_range == TimeRange.ONE_HOUR
    assert len(result.data_points) == 3  # Only metrics within 1 hour


def test_get_historical_metrics_twenty_four_hours(db_session, sample_resource):
    """Test get_historical_metrics retrieves metrics for 24 hour time range."""
    now = datetime.utcnow()

    # Create metrics within 24 hours
    for i in range(5):
        metric = MetricsModel(
            id=str(uuid.uuid4()),
            resource_id=sample_resource,
            timestamp=now - timedelta(hours=i * 4),
            cpu_percent=40.0 + i,
            memory_percent=50.0 + i,
            storage_used_gb=100.0,
            storage_iops=1000.0,
            network_in_mbps=10.0,
            network_out_mbps=10.0,
        )
        db_session.add(metric)

    # Create metric outside 24 hours
    old_metric = MetricsModel(
        id=str(uuid.uuid4()),
        resource_id=sample_resource,
        timestamp=now - timedelta(hours=30),
        cpu_percent=10.0,
        memory_percent=10.0,
        storage_used_gb=50.0,
        storage_iops=500.0,
        network_in_mbps=5.0,
        network_out_mbps=5.0,
    )
    db_session.add(old_metric)
    db_session.commit()

    # Get historical metrics
    result = get_historical_metrics(sample_resource, TimeRange.TWENTY_FOUR_HOURS, db_session)

    # Verify
    assert result.time_range == TimeRange.TWENTY_FOUR_HOURS
    assert len(result.data_points) == 5


def test_get_historical_metrics_seven_days(db_session, sample_resource):
    """Test get_historical_metrics retrieves metrics for 7 day time range."""
    now = datetime.utcnow()

    # Create metrics within 7 days
    for i in range(7):
        metric = MetricsModel(
            id=str(uuid.uuid4()),
            resource_id=sample_resource,
            timestamp=now - timedelta(days=i),
            cpu_percent=30.0 + i,
            memory_percent=40.0 + i,
            storage_used_gb=100.0,
            storage_iops=1000.0,
            network_in_mbps=10.0,
            network_out_mbps=10.0,
        )
        db_session.add(metric)

    # Create metric outside 7 days
    old_metric = MetricsModel(
        id=str(uuid.uuid4()),
        resource_id=sample_resource,
        timestamp=now - timedelta(days=10),
        cpu_percent=10.0,
        memory_percent=10.0,
        storage_used_gb=50.0,
        storage_iops=500.0,
        network_in_mbps=5.0,
        network_out_mbps=5.0,
    )
    db_session.add(old_metric)
    db_session.commit()

    # Get historical metrics
    result = get_historical_metrics(sample_resource, TimeRange.SEVEN_DAYS, db_session)

    # Verify
    assert result.time_range == TimeRange.SEVEN_DAYS
    assert len(result.data_points) == 7


def test_get_historical_metrics_sorted_by_timestamp(db_session, sample_resource):
    """Test get_historical_metrics returns data points sorted by timestamp ascending."""
    now = datetime.utcnow()

    # Create metrics in random order
    timestamps = [
        now - timedelta(minutes=30),
        now - timedelta(minutes=10),
        now - timedelta(minutes=50),
        now - timedelta(minutes=20),
    ]

    for ts in timestamps:
        metric = MetricsModel(
            id=str(uuid.uuid4()),
            resource_id=sample_resource,
            timestamp=ts,
            cpu_percent=50.0,
            memory_percent=60.0,
            storage_used_gb=100.0,
            storage_iops=1000.0,
            network_in_mbps=10.0,
            network_out_mbps=10.0,
        )
        db_session.add(metric)
    db_session.commit()

    # Get historical metrics
    result = get_historical_metrics(sample_resource, TimeRange.ONE_HOUR, db_session)

    # Verify sorted ascending
    assert len(result.data_points) == 4
    for i in range(len(result.data_points) - 1):
        ts1 = datetime.fromisoformat(result.data_points[i]["timestamp"])
        ts2 = datetime.fromisoformat(result.data_points[i + 1]["timestamp"])
        assert ts1 < ts2


def test_get_historical_metrics_data_point_structure(db_session, sample_resource):
    """Test get_historical_metrics data points have correct structure."""
    now = datetime.utcnow()
    metric = MetricsModel(
        id=str(uuid.uuid4()),
        resource_id=sample_resource,
        timestamp=now,
        cpu_percent=45.5,
        memory_percent=60.2,
        storage_used_gb=100.5,
        storage_iops=1000.0,
        network_in_mbps=10.5,
        network_out_mbps=8.3,
    )
    db_session.add(metric)
    db_session.commit()

    # Get historical metrics
    result = get_historical_metrics(sample_resource, TimeRange.ONE_HOUR, db_session)

    # Verify data point structure
    assert len(result.data_points) == 1
    point = result.data_points[0]
    assert "timestamp" in point
    assert "cpu" in point
    assert "memory" in point
    assert "storage" in point
    assert "network" in point
    assert point["cpu"] == 45.5
    assert point["memory"] == 60.2
    assert point["storage"] == 100.5
    assert point["network"] == 18.8  # 10.5 + 8.3


def test_get_alerts_with_high_cpu_utilization(db_session, sample_resource):
    """Test get_alerts generates alert when CPU exceeds 80%."""
    now = datetime.utcnow()
    metric = MetricsModel(
        id=str(uuid.uuid4()),
        resource_id=sample_resource,
        timestamp=now,
        cpu_percent=85.0,  # Above 80% threshold
        memory_percent=50.0,
        storage_used_gb=100.0,
        storage_iops=1000.0,
        network_in_mbps=10.0,
        network_out_mbps=10.0,
    )
    db_session.add(metric)
    db_session.commit()

    # Get alerts
    alerts = get_alerts(sample_resource, db_session)

    # Verify CPU alert generated
    assert len(alerts) == 1
    assert alerts[0].metric_type == "cpu"
    assert alerts[0].current_value == 85.0
    assert alerts[0].threshold == 80.0
    assert alerts[0].severity == "warning"


def test_get_alerts_with_high_memory_utilization(db_session, sample_resource):
    """Test get_alerts generates alert when memory exceeds 80%."""
    now = datetime.utcnow()
    metric = MetricsModel(
        id=str(uuid.uuid4()),
        resource_id=sample_resource,
        timestamp=now,
        cpu_percent=50.0,
        memory_percent=92.0,  # Above 80% threshold
        storage_used_gb=100.0,
        storage_iops=1000.0,
        network_in_mbps=10.0,
        network_out_mbps=10.0,
    )
    db_session.add(metric)
    db_session.commit()

    # Get alerts
    alerts = get_alerts(sample_resource, db_session)

    # Verify memory alert generated
    assert len(alerts) == 1
    assert alerts[0].metric_type == "memory"
    assert alerts[0].current_value == 92.0
    assert alerts[0].threshold == 80.0
    assert alerts[0].severity == "critical"  # Above 90%


def test_get_alerts_with_multiple_high_utilization(db_session, sample_resource):
    """Test get_alerts generates multiple alerts when multiple metrics exceed threshold."""
    now = datetime.utcnow()
    metric = MetricsModel(
        id=str(uuid.uuid4()),
        resource_id=sample_resource,
        timestamp=now,
        cpu_percent=85.0,  # Above 80%
        memory_percent=88.0,  # Above 80%
        storage_used_gb=100.0,
        storage_iops=1000.0,
        network_in_mbps=10.0,
        network_out_mbps=10.0,
    )
    db_session.add(metric)
    db_session.commit()

    # Get alerts
    alerts = get_alerts(sample_resource, db_session)

    # Verify both alerts generated
    assert len(alerts) == 2
    metric_types = {alert.metric_type for alert in alerts}
    assert "cpu" in metric_types
    assert "memory" in metric_types


def test_get_alerts_with_normal_utilization(db_session, sample_resource):
    """Test get_alerts returns empty list when utilization is normal."""
    now = datetime.utcnow()
    metric = MetricsModel(
        id=str(uuid.uuid4()),
        resource_id=sample_resource,
        timestamp=now,
        cpu_percent=50.0,  # Below 80%
        memory_percent=60.0,  # Below 80%
        storage_used_gb=100.0,
        storage_iops=1000.0,
        network_in_mbps=10.0,
        network_out_mbps=10.0,
    )
    db_session.add(metric)
    db_session.commit()

    # Get alerts
    alerts = get_alerts(sample_resource, db_session)

    # Verify no alerts
    assert len(alerts) == 0


def test_get_alerts_no_metrics_returns_empty(db_session, sample_resource):
    """Test get_alerts returns empty list when no metrics exist."""
    # Get alerts without creating any metrics
    alerts = get_alerts(sample_resource, db_session)

    # Verify no alerts
    assert len(alerts) == 0


def test_get_resource_health_healthy(db_session, sample_resource):
    """Test get_resource_health returns healthy status for recent metrics."""
    now = datetime.utcnow()
    metric = MetricsModel(
        id=str(uuid.uuid4()),
        resource_id=sample_resource,
        timestamp=now,  # Recent metric
        cpu_percent=50.0,
        memory_percent=60.0,
        storage_used_gb=100.0,
        storage_iops=1000.0,
        network_in_mbps=10.0,
        network_out_mbps=10.0,
    )
    db_session.add(metric)
    db_session.commit()

    # Get resource health
    health = get_resource_health(sample_resource, db_session)

    # Verify healthy status
    assert isinstance(health, ResourceHealth)
    assert health.resource_id == sample_resource
    assert health.is_reachable is True
    assert health.status == "healthy"
    assert health.last_successful_collection == now


def test_get_resource_health_unreachable_stale_metrics(db_session, sample_resource):
    """Test get_resource_health returns unreachable status for stale metrics."""
    old_time = datetime.utcnow() - timedelta(minutes=5)  # Older than 2 minutes
    metric = MetricsModel(
        id=str(uuid.uuid4()),
        resource_id=sample_resource,
        timestamp=old_time,
        cpu_percent=50.0,
        memory_percent=60.0,
        storage_used_gb=100.0,
        storage_iops=1000.0,
        network_in_mbps=10.0,
        network_out_mbps=10.0,
    )
    db_session.add(metric)
    db_session.commit()

    # Get resource health
    health = get_resource_health(sample_resource, db_session)

    # Verify unreachable status
    assert health.is_reachable is False
    assert health.status == "unreachable"
    assert health.last_successful_collection == old_time


def test_get_resource_health_unreachable_no_metrics(db_session, sample_resource):
    """Test get_resource_health returns unreachable status when no metrics exist."""
    # Get resource health without creating any metrics
    health = get_resource_health(sample_resource, db_session)

    # Verify unreachable status
    assert health.is_reachable is False
    assert health.status == "unreachable"
    assert health.last_successful_collection is None


def test_get_resource_health_nonexistent_resource(db_session):
    """Test get_resource_health raises ValueError for nonexistent resource."""
    fake_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="Resource .* not found"):
        get_resource_health(fake_id, db_session)


def test_time_range_enum():
    """Test TimeRange enum has correct values."""
    assert TimeRange.ONE_HOUR.value == "1h"
    assert TimeRange.TWENTY_FOUR_HOURS.value == "24h"
    assert TimeRange.SEVEN_DAYS.value == "7d"


def test_current_metrics_dataclass():
    """Test CurrentMetrics dataclass can be instantiated."""
    now = datetime.utcnow()
    metrics = CurrentMetrics(
        resource_id="test-id",
        cpu_percent=50.0,
        memory_percent=60.0,
        storage_percent=70.0,
        network_mbps=20.0,
        timestamp=now,
    )

    assert metrics.resource_id == "test-id"
    assert metrics.cpu_percent == 50.0
    assert metrics.memory_percent == 60.0
    assert metrics.storage_percent == 70.0
    assert metrics.network_mbps == 20.0
    assert metrics.timestamp == now


def test_historical_metrics_dataclass():
    """Test HistoricalMetrics dataclass can be instantiated."""
    data_points = [
        {"timestamp": "2024-01-01T00:00:00", "cpu": 50.0, "memory": 60.0},
        {"timestamp": "2024-01-01T00:01:00", "cpu": 55.0, "memory": 65.0},
    ]

    metrics = HistoricalMetrics(
        resource_id="test-id",
        time_range=TimeRange.ONE_HOUR,
        data_points=data_points,
    )

    assert metrics.resource_id == "test-id"
    assert metrics.time_range == TimeRange.ONE_HOUR
    assert len(metrics.data_points) == 2


def test_alert_dataclass():
    """Test Alert dataclass can be instantiated."""
    now = datetime.utcnow()
    alert = Alert(
        resource_id="test-id",
        metric_type="cpu",
        current_value=85.0,
        threshold=80.0,
        severity="warning",
        timestamp=now,
    )

    assert alert.resource_id == "test-id"
    assert alert.metric_type == "cpu"
    assert alert.current_value == 85.0
    assert alert.threshold == 80.0
    assert alert.severity == "warning"
    assert alert.timestamp == now


def test_resource_health_dataclass():
    """Test ResourceHealth dataclass can be instantiated."""
    now = datetime.utcnow()
    health = ResourceHealth(
        resource_id="test-id",
        is_reachable=True,
        last_successful_collection=now,
        status="healthy",
    )

    assert health.resource_id == "test-id"
    assert health.is_reachable is True
    assert health.last_successful_collection == now
    assert health.status == "healthy"
