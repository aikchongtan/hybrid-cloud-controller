"""Dashboard data provider for monitoring metrics."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session

from packages.database import models

logger = logging.getLogger(__name__)


class TimeRange(Enum):
    """Time range options for historical metrics."""

    ONE_HOUR = "1h"
    TWENTY_FOUR_HOURS = "24h"
    SEVEN_DAYS = "7d"


@dataclass
class CurrentMetrics:
    """Current metrics snapshot for a resource."""

    resource_id: str
    cpu_percent: float
    memory_percent: float
    storage_percent: float
    network_mbps: float
    timestamp: datetime


@dataclass
class HistoricalMetrics:
    """Historical metrics for a resource over a time range."""

    resource_id: str
    time_range: TimeRange
    data_points: list[dict]  # List of {timestamp, cpu, memory, storage, network}


@dataclass
class Alert:
    """Alert for resource utilization exceeding threshold."""

    resource_id: str
    metric_type: str  # "cpu", "memory", "storage"
    current_value: float
    threshold: float
    severity: str  # "warning", "critical"
    timestamp: datetime


@dataclass
class ResourceHealth:
    """Health status for a resource."""

    resource_id: str
    is_reachable: bool
    last_successful_collection: Optional[datetime]
    status: str  # "healthy", "unreachable", "degraded"


def _calculate_time_window(time_range: TimeRange) -> datetime:
    """
    Calculate the start time for a time window based on time range.

    Args:
        time_range: The time range to calculate window for

    Returns:
        datetime representing the start of the time window
    """
    now = datetime.utcnow()

    if time_range == TimeRange.ONE_HOUR:
        return now - timedelta(hours=1)
    elif time_range == TimeRange.TWENTY_FOUR_HOURS:
        return now - timedelta(hours=24)
    elif time_range == TimeRange.SEVEN_DAYS:
        return now - timedelta(days=7)
    else:
        raise ValueError(f"Unknown time range: {time_range}")


def get_current_metrics(resource_id: str, db_session: Session) -> CurrentMetrics:
    """
    Get the most recent metrics for a resource.

    Args:
        resource_id: The ID of the resource to get metrics for
        db_session: SQLAlchemy database session

    Returns:
        CurrentMetrics object with latest metric values

    Raises:
        ValueError: If resource not found or no metrics available
    """
    # Query most recent metrics for resource
    latest_metric = (
        db_session.query(models.MetricsModel)
        .filter(models.MetricsModel.resource_id == resource_id)
        .order_by(models.MetricsModel.timestamp.desc())
        .first()
    )

    if not latest_metric:
        raise ValueError(f"No metrics found for resource {resource_id}")

    # Calculate network throughput (sum of in and out)
    network_mbps = latest_metric.network_in_mbps + latest_metric.network_out_mbps

    return CurrentMetrics(
        resource_id=resource_id,
        cpu_percent=latest_metric.cpu_percent,
        memory_percent=latest_metric.memory_percent,
        storage_percent=0.0,  # Will be calculated from storage_used_gb if needed
        network_mbps=network_mbps,
        timestamp=latest_metric.timestamp,
    )


def get_historical_metrics(
    resource_id: str, time_range: TimeRange, db_session: Session
) -> HistoricalMetrics:
    """
    Get historical metrics for a resource over a time range.

    Args:
        resource_id: The ID of the resource to get metrics for
        time_range: The time range to retrieve (1h, 24h, 7d)
        db_session: SQLAlchemy database session

    Returns:
        HistoricalMetrics object with data points for the time range

    Raises:
        ValueError: If resource not found
    """
    # Calculate time window
    start_time = _calculate_time_window(time_range)

    # Query metrics within time window
    metrics = (
        db_session.query(models.MetricsModel)
        .filter(
            models.MetricsModel.resource_id == resource_id,
            models.MetricsModel.timestamp >= start_time,
        )
        .order_by(models.MetricsModel.timestamp.asc())
        .all()
    )

    # Convert to data points
    data_points = []
    for metric in metrics:
        data_points.append(
            {
                "timestamp": metric.timestamp.isoformat(),
                "cpu": metric.cpu_percent,
                "memory": metric.memory_percent,
                "storage": metric.storage_used_gb,
                "network": metric.network_in_mbps + metric.network_out_mbps,
            }
        )

    return HistoricalMetrics(
        resource_id=resource_id,
        time_range=time_range,
        data_points=data_points,
    )


def get_alerts(resource_id: str, db_session: Session) -> list[Alert]:
    """
    Get alerts for a resource based on utilization thresholds.

    Generates alerts when CPU, memory, or storage utilization exceeds 80%.

    Args:
        resource_id: The ID of the resource to check for alerts
        db_session: SQLAlchemy database session

    Returns:
        List of Alert objects (empty if no alerts)

    Raises:
        ValueError: If resource not found or no metrics available
    """
    # Get current metrics
    try:
        current = get_current_metrics(resource_id, db_session)
    except ValueError:
        # No metrics available, return empty alerts
        return []

    alerts = []
    threshold = 80.0

    # Check CPU utilization
    if current.cpu_percent > threshold:
        alerts.append(
            Alert(
                resource_id=resource_id,
                metric_type="cpu",
                current_value=current.cpu_percent,
                threshold=threshold,
                severity="warning" if current.cpu_percent < 90 else "critical",
                timestamp=current.timestamp,
            )
        )

    # Check memory utilization
    if current.memory_percent > threshold:
        alerts.append(
            Alert(
                resource_id=resource_id,
                metric_type="memory",
                current_value=current.memory_percent,
                threshold=threshold,
                severity="warning" if current.memory_percent < 90 else "critical",
                timestamp=current.timestamp,
            )
        )

    # Check storage utilization (if storage_percent is available)
    if current.storage_percent > threshold:
        alerts.append(
            Alert(
                resource_id=resource_id,
                metric_type="storage",
                current_value=current.storage_percent,
                threshold=threshold,
                severity="warning" if current.storage_percent < 90 else "critical",
                timestamp=current.timestamp,
            )
        )

    logger.debug(f"Generated {len(alerts)} alerts for resource {resource_id}")
    return alerts


def get_resource_health(resource_id: str, db_session: Session) -> ResourceHealth:
    """
    Get health status for a resource.

    A resource is considered unreachable if no metrics have been collected
    in the last 2 minutes.

    Args:
        resource_id: The ID of the resource to check health for
        db_session: SQLAlchemy database session

    Returns:
        ResourceHealth object with health status

    Raises:
        ValueError: If resource not found in database
    """
    # Verify resource exists
    resource = (
        db_session.query(models.ResourceModel)
        .filter(models.ResourceModel.id == resource_id)
        .first()
    )

    if not resource:
        raise ValueError(f"Resource {resource_id} not found")

    # Query most recent metrics
    latest_metric = (
        db_session.query(models.MetricsModel)
        .filter(models.MetricsModel.resource_id == resource_id)
        .order_by(models.MetricsModel.timestamp.desc())
        .first()
    )

    # Check if metrics are recent (within last 2 minutes)
    now = datetime.utcnow()
    reachability_threshold = timedelta(minutes=2)

    if not latest_metric:
        # No metrics at all
        return ResourceHealth(
            resource_id=resource_id,
            is_reachable=False,
            last_successful_collection=None,
            status="unreachable",
        )

    time_since_last_metric = now - latest_metric.timestamp

    if time_since_last_metric > reachability_threshold:
        # Metrics are stale
        return ResourceHealth(
            resource_id=resource_id,
            is_reachable=False,
            last_successful_collection=latest_metric.timestamp,
            status="unreachable",
        )

    # Metrics are recent, resource is healthy
    return ResourceHealth(
        resource_id=resource_id,
        is_reachable=True,
        last_successful_collection=latest_metric.timestamp,
        status="healthy",
    )
