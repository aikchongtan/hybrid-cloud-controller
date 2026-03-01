"""Metrics collector for monitoring provisioned resources."""

import logging
import random
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from packages.database import models

logger = logging.getLogger(__name__)

# Try to import psutil, fall back to mock mode if not available
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available, using mock metrics mode")


@dataclass
class CPUMetrics:
    """CPU utilization metrics for a resource."""

    resource_id: str
    utilization_percent: float
    timestamp: datetime


@dataclass
class MemoryMetrics:
    """Memory utilization metrics for a resource."""

    resource_id: str
    used_mb: int
    total_mb: int
    utilization_percent: float
    timestamp: datetime


@dataclass
class StorageMetrics:
    """Storage utilization and I/O metrics for a resource."""

    resource_id: str
    used_gb: int
    total_gb: int
    utilization_percent: float
    read_iops: int
    write_iops: int
    timestamp: datetime


@dataclass
class NetworkMetrics:
    """Network throughput metrics for a resource."""

    resource_id: str
    bytes_sent: int
    bytes_received: int
    throughput_mbps: float
    timestamp: datetime


def _generate_mock_cpu_metrics(resource_id: str) -> CPUMetrics:
    """Generate realistic mock CPU metrics for development/testing."""
    return CPUMetrics(
        resource_id=resource_id,
        utilization_percent=round(random.uniform(10.0, 90.0), 2),
        timestamp=datetime.utcnow(),
    )


def _generate_mock_memory_metrics(resource_id: str) -> MemoryMetrics:
    """Generate realistic mock memory metrics for development/testing."""
    total_mb = random.choice([1024, 2048, 4096, 8192, 16384])
    utilization_percent = round(random.uniform(20.0, 80.0), 2)
    used_mb = int(total_mb * utilization_percent / 100)

    return MemoryMetrics(
        resource_id=resource_id,
        used_mb=used_mb,
        total_mb=total_mb,
        utilization_percent=utilization_percent,
        timestamp=datetime.utcnow(),
    )


def _generate_mock_storage_metrics(resource_id: str) -> StorageMetrics:
    """Generate realistic mock storage metrics for development/testing."""
    total_gb = random.choice([50, 100, 250, 500, 1000])
    utilization_percent = round(random.uniform(30.0, 70.0), 2)
    used_gb = int(total_gb * utilization_percent / 100)

    return StorageMetrics(
        resource_id=resource_id,
        used_gb=used_gb,
        total_gb=total_gb,
        utilization_percent=utilization_percent,
        read_iops=random.randint(100, 5000),
        write_iops=random.randint(100, 5000),
        timestamp=datetime.utcnow(),
    )


def _generate_mock_network_metrics(resource_id: str) -> NetworkMetrics:
    """Generate realistic mock network metrics for development/testing."""
    bytes_sent = random.randint(1000000, 100000000)  # 1MB to 100MB
    bytes_received = random.randint(1000000, 100000000)
    throughput_mbps = round(random.uniform(1.0, 100.0), 2)

    return NetworkMetrics(
        resource_id=resource_id,
        bytes_sent=bytes_sent,
        bytes_received=bytes_received,
        throughput_mbps=throughput_mbps,
        timestamp=datetime.utcnow(),
    )


def collect_cpu_metrics(resource_id: str, db_session: Session) -> CPUMetrics:
    """
    Collect CPU utilization metrics for a resource.

    Args:
        resource_id: The ID of the resource to collect metrics for
        db_session: SQLAlchemy database session

    Returns:
        CPUMetrics object containing CPU utilization data

    Raises:
        ValueError: If resource not found in database
    """
    # Query resource from database
    resource = (
        db_session.query(models.ResourceModel)
        .filter(models.ResourceModel.id == resource_id)
        .first()
    )

    if not resource:
        raise ValueError(f"Resource {resource_id} not found")

    # Use psutil if available, otherwise generate mock metrics
    if PSUTIL_AVAILABLE:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            metrics = CPUMetrics(
                resource_id=resource_id,
                utilization_percent=cpu_percent,
                timestamp=datetime.utcnow(),
            )
        except Exception as e:
            logger.warning(f"Failed to collect real CPU metrics for {resource_id}: {e}, using mock")
            metrics = _generate_mock_cpu_metrics(resource_id)
    else:
        metrics = _generate_mock_cpu_metrics(resource_id)

    # Store metrics in database
    _store_metrics_in_db(metrics, None, None, None, db_session)

    logger.debug(f"Collected CPU metrics for {resource_id}: {metrics.utilization_percent}%")
    return metrics


def collect_memory_metrics(resource_id: str, db_session: Session) -> MemoryMetrics:
    """
    Collect memory utilization metrics for a resource.

    Args:
        resource_id: The ID of the resource to collect metrics for
        db_session: SQLAlchemy database session

    Returns:
        MemoryMetrics object containing memory utilization data

    Raises:
        ValueError: If resource not found in database
    """
    # Query resource from database
    resource = (
        db_session.query(models.ResourceModel)
        .filter(models.ResourceModel.id == resource_id)
        .first()
    )

    if not resource:
        raise ValueError(f"Resource {resource_id} not found")

    # Use psutil if available, otherwise generate mock metrics
    if PSUTIL_AVAILABLE:
        try:
            mem = psutil.virtual_memory()
            metrics = MemoryMetrics(
                resource_id=resource_id,
                used_mb=int(mem.used / (1024 * 1024)),
                total_mb=int(mem.total / (1024 * 1024)),
                utilization_percent=mem.percent,
                timestamp=datetime.utcnow(),
            )
        except Exception as e:
            logger.warning(
                f"Failed to collect real memory metrics for {resource_id}: {e}, using mock"
            )
            metrics = _generate_mock_memory_metrics(resource_id)
    else:
        metrics = _generate_mock_memory_metrics(resource_id)

    # Store metrics in database
    _store_metrics_in_db(None, metrics, None, None, db_session)

    logger.debug(f"Collected memory metrics for {resource_id}: {metrics.utilization_percent}%")
    return metrics


def collect_storage_metrics(resource_id: str, db_session: Session) -> StorageMetrics:
    """
    Collect storage utilization and I/O metrics for a resource.

    Args:
        resource_id: The ID of the resource to collect metrics for
        db_session: SQLAlchemy database session

    Returns:
        StorageMetrics object containing storage utilization and I/O data

    Raises:
        ValueError: If resource not found in database
    """
    # Query resource from database
    resource = (
        db_session.query(models.ResourceModel)
        .filter(models.ResourceModel.id == resource_id)
        .first()
    )

    if not resource:
        raise ValueError(f"Resource {resource_id} not found")

    # Use psutil if available, otherwise generate mock metrics
    if PSUTIL_AVAILABLE:
        try:
            disk = psutil.disk_usage("/")
            disk_io = psutil.disk_io_counters()

            metrics = StorageMetrics(
                resource_id=resource_id,
                used_gb=int(disk.used / (1024**3)),
                total_gb=int(disk.total / (1024**3)),
                utilization_percent=disk.percent,
                read_iops=disk_io.read_count if disk_io else 0,
                write_iops=disk_io.write_count if disk_io else 0,
                timestamp=datetime.utcnow(),
            )
        except Exception as e:
            logger.warning(
                f"Failed to collect real storage metrics for {resource_id}: {e}, using mock"
            )
            metrics = _generate_mock_storage_metrics(resource_id)
    else:
        metrics = _generate_mock_storage_metrics(resource_id)

    # Store metrics in database
    _store_metrics_in_db(None, None, metrics, None, db_session)

    logger.debug(f"Collected storage metrics for {resource_id}: {metrics.utilization_percent}%")
    return metrics


def collect_network_metrics(resource_id: str, db_session: Session) -> NetworkMetrics:
    """
    Collect network throughput metrics for a resource.

    Args:
        resource_id: The ID of the resource to collect metrics for
        db_session: SQLAlchemy database session

    Returns:
        NetworkMetrics object containing network throughput data

    Raises:
        ValueError: If resource not found in database
    """
    # Query resource from database
    resource = (
        db_session.query(models.ResourceModel)
        .filter(models.ResourceModel.id == resource_id)
        .first()
    )

    if not resource:
        raise ValueError(f"Resource {resource_id} not found")

    # Use psutil if available, otherwise generate mock metrics
    if PSUTIL_AVAILABLE:
        try:
            net_io = psutil.net_io_counters()
            # Calculate throughput in Mbps (simplified calculation)
            throughput_mbps = round((net_io.bytes_sent + net_io.bytes_recv) / (1024 * 1024), 2)

            metrics = NetworkMetrics(
                resource_id=resource_id,
                bytes_sent=net_io.bytes_sent,
                bytes_received=net_io.bytes_recv,
                throughput_mbps=throughput_mbps,
                timestamp=datetime.utcnow(),
            )
        except Exception as e:
            logger.warning(
                f"Failed to collect real network metrics for {resource_id}: {e}, using mock"
            )
            metrics = _generate_mock_network_metrics(resource_id)
    else:
        metrics = _generate_mock_network_metrics(resource_id)

    # Store metrics in database
    _store_metrics_in_db(None, None, None, metrics, db_session)

    logger.debug(f"Collected network metrics for {resource_id}: {metrics.throughput_mbps} Mbps")
    return metrics


def _store_metrics_in_db(
    cpu_metrics: Optional[CPUMetrics],
    memory_metrics: Optional[MemoryMetrics],
    storage_metrics: Optional[StorageMetrics],
    network_metrics: Optional[NetworkMetrics],
    db_session: Session,
) -> None:
    """
    Store collected metrics in the database.

    This is a helper function that stores metrics in MetricsModel.
    It handles partial metrics (e.g., only CPU metrics) by using defaults for missing values.
    """
    # Determine resource_id and timestamp from whichever metrics object is provided
    resource_id = None
    timestamp = datetime.utcnow()

    if cpu_metrics:
        resource_id = cpu_metrics.resource_id
        timestamp = cpu_metrics.timestamp
    elif memory_metrics:
        resource_id = memory_metrics.resource_id
        timestamp = memory_metrics.timestamp
    elif storage_metrics:
        resource_id = storage_metrics.resource_id
        timestamp = storage_metrics.timestamp
    elif network_metrics:
        resource_id = network_metrics.resource_id
        timestamp = network_metrics.timestamp

    if not resource_id:
        logger.error("No metrics provided to store")
        return

    # Create metrics record with available data
    metrics_record = models.MetricsModel(
        id=str(uuid.uuid4()),
        resource_id=resource_id,
        timestamp=timestamp,
        cpu_percent=cpu_metrics.utilization_percent if cpu_metrics else 0.0,
        memory_percent=memory_metrics.utilization_percent if memory_metrics else 0.0,
        storage_used_gb=float(storage_metrics.used_gb) if storage_metrics else 0.0,
        storage_iops=float(storage_metrics.read_iops + storage_metrics.write_iops)
        if storage_metrics
        else 0.0,
        network_in_mbps=network_metrics.throughput_mbps / 2 if network_metrics else 0.0,
        network_out_mbps=network_metrics.throughput_mbps / 2 if network_metrics else 0.0,
    )

    db_session.add(metrics_record)
    db_session.commit()


def _collect_all_metrics(resource_id: str, db_session: Session) -> None:
    """
    Collect all metric types for a resource.

    This is a helper function used by start_collection to collect all metrics
    in a single operation.
    """
    try:
        collect_cpu_metrics(resource_id, db_session)
        collect_memory_metrics(resource_id, db_session)
        collect_storage_metrics(resource_id, db_session)
        collect_network_metrics(resource_id, db_session)
    except Exception as e:
        logger.error(f"Error collecting metrics for {resource_id}: {e}")


def start_collection(
    resource_ids: list[str],
    db_session: Session,
    interval_seconds: int = 30,
) -> threading.Thread:
    """
    Start periodic metrics collection for resources.

    Args:
        resource_ids: List of resource IDs to collect metrics for
        db_session: SQLAlchemy database session
        interval_seconds: Collection interval in seconds (default: 30)

    Returns:
        Thread handle for the background collection thread

    Note:
        The returned thread is started and runs as a daemon.
        To stop collection, you can set a stop event or terminate the thread.
    """
    stop_event = threading.Event()

    def collection_loop():
        """Background thread loop for periodic metrics collection."""
        logger.info(
            f"Starting metrics collection for {len(resource_ids)} resources "
            f"at {interval_seconds}s intervals"
        )

        while not stop_event.is_set():
            for resource_id in resource_ids:
                try:
                    _collect_all_metrics(resource_id, db_session)
                except Exception as e:
                    logger.error(
                        f"Failed to collect metrics for {resource_id}: {e}",
                        exc_info=True,
                    )

            # Wait for the interval or until stop event is set
            stop_event.wait(interval_seconds)

        logger.info("Metrics collection stopped")

    # Create and start the collection thread
    collection_thread = threading.Thread(target=collection_loop, daemon=True)
    collection_thread.stop_event = stop_event  # Attach stop event for external control
    collection_thread.start()

    return collection_thread
