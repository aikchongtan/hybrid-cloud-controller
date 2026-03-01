"""Unit tests for metrics collector."""

import threading
import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.database import models
from packages.monitoring import collector


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def sample_resource(db_session):
    """Create a sample resource in the database."""
    resource = models.ResourceModel(
        id=str(uuid.uuid4()),
        provision_id=str(uuid.uuid4()),
        resource_type="vm",
        external_id="test-vm-001",
        status="running",
        connection_info_json="{}",
        created_at=datetime.utcnow(),
    )
    db_session.add(resource)
    db_session.commit()
    return resource


def test_cpu_metrics_dataclass():
    """Test CPUMetrics dataclass creation."""
    metrics = collector.CPUMetrics(
        resource_id="test-id",
        utilization_percent=45.5,
        timestamp=datetime.utcnow(),
    )

    assert metrics.resource_id == "test-id"
    assert metrics.utilization_percent == 45.5
    assert isinstance(metrics.timestamp, datetime)


def test_memory_metrics_dataclass():
    """Test MemoryMetrics dataclass creation."""
    metrics = collector.MemoryMetrics(
        resource_id="test-id",
        used_mb=2048,
        total_mb=4096,
        utilization_percent=50.0,
        timestamp=datetime.utcnow(),
    )

    assert metrics.resource_id == "test-id"
    assert metrics.used_mb == 2048
    assert metrics.total_mb == 4096
    assert metrics.utilization_percent == 50.0


def test_storage_metrics_dataclass():
    """Test StorageMetrics dataclass creation."""
    metrics = collector.StorageMetrics(
        resource_id="test-id",
        used_gb=50,
        total_gb=100,
        utilization_percent=50.0,
        read_iops=1000,
        write_iops=500,
        timestamp=datetime.utcnow(),
    )

    assert metrics.resource_id == "test-id"
    assert metrics.used_gb == 50
    assert metrics.total_gb == 100
    assert metrics.utilization_percent == 50.0
    assert metrics.read_iops == 1000
    assert metrics.write_iops == 500


def test_network_metrics_dataclass():
    """Test NetworkMetrics dataclass creation."""
    metrics = collector.NetworkMetrics(
        resource_id="test-id",
        bytes_sent=1000000,
        bytes_received=2000000,
        throughput_mbps=25.5,
        timestamp=datetime.utcnow(),
    )

    assert metrics.resource_id == "test-id"
    assert metrics.bytes_sent == 1000000
    assert metrics.bytes_received == 2000000
    assert metrics.throughput_mbps == 25.5


def test_generate_mock_cpu_metrics():
    """Test mock CPU metrics generation."""
    metrics = collector._generate_mock_cpu_metrics("test-id")

    assert metrics.resource_id == "test-id"
    assert 10.0 <= metrics.utilization_percent <= 90.0
    assert isinstance(metrics.timestamp, datetime)


def test_generate_mock_memory_metrics():
    """Test mock memory metrics generation."""
    metrics = collector._generate_mock_memory_metrics("test-id")

    assert metrics.resource_id == "test-id"
    assert metrics.total_mb in [1024, 2048, 4096, 8192, 16384]
    assert 20.0 <= metrics.utilization_percent <= 80.0
    assert metrics.used_mb <= metrics.total_mb
    assert isinstance(metrics.timestamp, datetime)


def test_generate_mock_storage_metrics():
    """Test mock storage metrics generation."""
    metrics = collector._generate_mock_storage_metrics("test-id")

    assert metrics.resource_id == "test-id"
    assert metrics.total_gb in [50, 100, 250, 500, 1000]
    assert 30.0 <= metrics.utilization_percent <= 70.0
    assert metrics.used_gb <= metrics.total_gb
    assert 100 <= metrics.read_iops <= 5000
    assert 100 <= metrics.write_iops <= 5000
    assert isinstance(metrics.timestamp, datetime)


def test_generate_mock_network_metrics():
    """Test mock network metrics generation."""
    metrics = collector._generate_mock_network_metrics("test-id")

    assert metrics.resource_id == "test-id"
    assert 1000000 <= metrics.bytes_sent <= 100000000
    assert 1000000 <= metrics.bytes_received <= 100000000
    assert 1.0 <= metrics.throughput_mbps <= 100.0
    assert isinstance(metrics.timestamp, datetime)


def test_collect_cpu_metrics_mock_mode(sample_resource, db_session):
    """Test CPU metrics collection in mock mode."""
    metrics = collector.collect_cpu_metrics(sample_resource.id, db_session)

    assert metrics.resource_id == sample_resource.id
    assert 0.0 <= metrics.utilization_percent <= 100.0
    assert isinstance(metrics.timestamp, datetime)

    # Verify metrics stored in database
    stored_metrics = (
        db_session.query(models.MetricsModel)
        .filter(models.MetricsModel.resource_id == sample_resource.id)
        .first()
    )
    assert stored_metrics is not None
    assert stored_metrics.cpu_percent == metrics.utilization_percent


def test_collect_cpu_metrics_resource_not_found(db_session):
    """Test CPU metrics collection with non-existent resource."""
    with pytest.raises(ValueError, match="Resource .* not found"):
        collector.collect_cpu_metrics("non-existent-id", db_session)


def test_collect_memory_metrics_mock_mode(sample_resource, db_session):
    """Test memory metrics collection in mock mode."""
    metrics = collector.collect_memory_metrics(sample_resource.id, db_session)

    assert metrics.resource_id == sample_resource.id
    assert metrics.used_mb <= metrics.total_mb
    assert 0.0 <= metrics.utilization_percent <= 100.0
    assert isinstance(metrics.timestamp, datetime)

    # Verify metrics stored in database
    stored_metrics = (
        db_session.query(models.MetricsModel)
        .filter(models.MetricsModel.resource_id == sample_resource.id)
        .first()
    )
    assert stored_metrics is not None
    assert stored_metrics.memory_percent == metrics.utilization_percent


def test_collect_memory_metrics_resource_not_found(db_session):
    """Test memory metrics collection with non-existent resource."""
    with pytest.raises(ValueError, match="Resource .* not found"):
        collector.collect_memory_metrics("non-existent-id", db_session)


def test_collect_storage_metrics_mock_mode(sample_resource, db_session):
    """Test storage metrics collection in mock mode."""
    metrics = collector.collect_storage_metrics(sample_resource.id, db_session)

    assert metrics.resource_id == sample_resource.id
    assert metrics.used_gb <= metrics.total_gb
    assert 0.0 <= metrics.utilization_percent <= 100.0
    assert metrics.read_iops > 0
    assert metrics.write_iops > 0
    assert isinstance(metrics.timestamp, datetime)

    # Verify metrics stored in database
    stored_metrics = (
        db_session.query(models.MetricsModel)
        .filter(models.MetricsModel.resource_id == sample_resource.id)
        .first()
    )
    assert stored_metrics is not None
    assert stored_metrics.storage_used_gb == float(metrics.used_gb)


def test_collect_storage_metrics_resource_not_found(db_session):
    """Test storage metrics collection with non-existent resource."""
    with pytest.raises(ValueError, match="Resource .* not found"):
        collector.collect_storage_metrics("non-existent-id", db_session)


def test_collect_network_metrics_mock_mode(sample_resource, db_session):
    """Test network metrics collection in mock mode."""
    metrics = collector.collect_network_metrics(sample_resource.id, db_session)

    assert metrics.resource_id == sample_resource.id
    assert metrics.bytes_sent > 0
    assert metrics.bytes_received > 0
    assert metrics.throughput_mbps > 0.0
    assert isinstance(metrics.timestamp, datetime)

    # Verify metrics stored in database
    stored_metrics = (
        db_session.query(models.MetricsModel)
        .filter(models.MetricsModel.resource_id == sample_resource.id)
        .first()
    )
    assert stored_metrics is not None


def test_collect_network_metrics_resource_not_found(db_session):
    """Test network metrics collection with non-existent resource."""
    with pytest.raises(ValueError, match="Resource .* not found"):
        collector.collect_network_metrics("non-existent-id", db_session)


def test_store_metrics_in_db(sample_resource, db_session):
    """Test storing metrics in database."""
    cpu_metrics = collector.CPUMetrics(
        resource_id=sample_resource.id,
        utilization_percent=45.5,
        timestamp=datetime.utcnow(),
    )

    memory_metrics = collector.MemoryMetrics(
        resource_id=sample_resource.id,
        used_mb=2048,
        total_mb=4096,
        utilization_percent=50.0,
        timestamp=datetime.utcnow(),
    )

    collector._store_metrics_in_db(cpu_metrics, memory_metrics, None, None, db_session)

    # Verify metrics stored
    stored_metrics = (
        db_session.query(models.MetricsModel)
        .filter(models.MetricsModel.resource_id == sample_resource.id)
        .first()
    )

    assert stored_metrics is not None
    assert stored_metrics.cpu_percent == 45.5
    assert stored_metrics.memory_percent == 50.0


def test_collect_all_metrics(sample_resource, db_session):
    """Test collecting all metric types for a resource."""
    collector._collect_all_metrics(sample_resource.id, db_session)

    # Verify all metrics were collected and stored
    metrics_count = (
        db_session.query(models.MetricsModel)
        .filter(models.MetricsModel.resource_id == sample_resource.id)
        .count()
    )

    # Should have 4 metrics records (one for each type)
    assert metrics_count == 4


def test_collect_all_metrics_handles_errors(db_session):
    """Test that _collect_all_metrics handles errors gracefully."""
    # Should not raise exception for non-existent resource
    collector._collect_all_metrics("non-existent-id", db_session)


def test_start_collection_creates_thread(sample_resource, db_session):
    """Test that start_collection creates and starts a thread."""
    resource_ids = [sample_resource.id]

    # Start collection
    thread = collector.start_collection(resource_ids, db_session, interval_seconds=30)

    assert isinstance(thread, threading.Thread)
    assert thread.is_alive()
    assert hasattr(thread, "stop_event")

    # Stop the collection immediately
    thread.stop_event.set()
    thread.join(timeout=2)


def test_start_collection_multiple_resources_creates_thread(db_session):
    """Test starting collection for multiple resources creates thread."""
    # Create multiple resources
    resources = []
    for i in range(3):
        resource = models.ResourceModel(
            id=str(uuid.uuid4()),
            provision_id=str(uuid.uuid4()),
            resource_type="vm",
            external_id=f"test-vm-{i:03d}",
            status="running",
            connection_info_json="{}",
            created_at=datetime.utcnow(),
        )
        db_session.add(resource)
        resources.append(resource)
    db_session.commit()

    resource_ids = [r.id for r in resources]

    # Start collection
    thread = collector.start_collection(resource_ids, db_session, interval_seconds=30)

    assert thread.is_alive()
    assert isinstance(thread, threading.Thread)

    # Stop collection immediately
    thread.stop_event.set()
    thread.join(timeout=2)


def test_start_collection_with_custom_interval(sample_resource, db_session):
    """Test that start_collection accepts custom interval."""
    resource_ids = [sample_resource.id]

    # Start collection with custom interval
    thread = collector.start_collection(resource_ids, db_session, interval_seconds=60)

    assert thread.is_alive()

    # Stop collection
    thread.stop_event.set()
    thread.join(timeout=2)
