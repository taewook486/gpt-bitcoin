"""Alert webhook handlers for AlertManager integration.

This module provides FastAPI endpoints for receiving alerts from Prometheus AlertManager
and processing them with deduplication, logging, and optional forwarding.
"""

import hashlib
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

logger = structlog.get_logger()

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertLabel(BaseModel):
    """Alert labels from Prometheus."""

    alertname: str
    severity: str
    component: str
    cost_type: str | None = None


class AlertAnnotation(BaseModel):
    """Alert annotations from Prometheus."""

    summary: str
    description: str | None = None
    value: str | None = None
    runbook_url: str | None = None


class Alert(BaseModel):
    """Individual alert from AlertManager."""

    status: str
    labels: AlertLabel
    annotations: AlertAnnotation
    starts_at: datetime = Field(alias="startsAt")
    ends_at: datetime = Field(alias="endsAt")
    generator_url: str = Field(alias="generatorURL")
    fingerprint: str
    receiver: str

    class Config:
        populate_by_name = True


class AlertManagerWebhook(BaseModel):
    """Webhook payload from AlertManager."""

    receiver: str
    status: str
    alerts: list[Alert]
    group_labels: dict[str, str] = Field(alias="groupLabels", default_factory=dict)
    common_labels: dict[str, str] = Field(alias="commonLabels", default_factory=dict)
    common_annotations: dict[str, str] = Field(alias="commonAnnotations", default_factory=dict)
    external_url: str = Field(alias="externalURL")
    version: str
    group_key: str = Field(alias="groupKey")
    truncated_alerts: int = Field(alias="truncatedAlerts", default=0)

    class Config:
        populate_by_name = True


class AlertResponse(BaseModel):
    """Response for alert webhook."""

    status: str
    message: str
    processed_alerts: int
    deduplicated_alerts: int
    timestamp: datetime


class AlertDeduplicator:
    """Redis-based alert deduplication (optional)."""

    def __init__(self, redis_client: Any = None):
        """Initialize deduplicator with optional Redis client.

        Args:
            redis_client: Optional Redis client for distributed deduplication
        """
        self.redis_client = redis_client
        self.local_cache: dict[str, datetime] = {}
        self.dedup_window_seconds = 300  # 5 minutes

    def _get_dedup_key(self, alert: Alert) -> str:
        """Generate deduplication key for an alert.

        Args:
            alert: Alert to generate key for

        Returns:
            SHA256 hash of alert fingerprint and status
        """
        key_data = f"{alert.fingerprint}:{alert.status}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def is_duplicate(self, alert: Alert) -> bool:
        """Check if alert is a duplicate within the deduplication window.

        Args:
            alert: Alert to check

        Returns:
            True if alert is a duplicate, False otherwise
        """
        dedup_key = self._get_dedup_key(alert)
        now = datetime.now(UTC)

        if self.redis_client:
            # Use Redis for distributed deduplication
            try:
                # Support both sync and async Redis clients
                import asyncio

                try:
                    # Check if we're in an async context
                    loop = asyncio.get_running_loop()
                    # If we are, we can't use sync Redis operations
                    # Fall back to local cache
                    raise RuntimeError("Cannot use sync Redis client in async context")
                except RuntimeError:
                    # No running loop, use sync operations
                    existing = self.redis_client.get(f"alert:{dedup_key}")
                    if existing:
                        return True
                    self.redis_client.setex(
                        f"alert:{dedup_key}",
                        self.dedup_window_seconds,
                        now.isoformat(),
                    )
                    return False
            except Exception as e:
                logger.warning(
                    "redis_dedup_failed",
                    error=str(e),
                    fallback="local_cache",
                )
                # Fall back to local cache

        # Use local cache for deduplication
        if dedup_key in self.local_cache:
            cached_time = self.local_cache[dedup_key]
            age = (now - cached_time).total_seconds()
            if age < self.dedup_window_seconds:
                return True

        self.local_cache[dedup_key] = now
        return False

    def cleanup_cache(self) -> None:
        """Clean up expired entries from local cache."""
        if not self.redis_client:
            now = datetime.now(UTC)
            expired_keys = [
                key
                for key, timestamp in self.local_cache.items()
                if (now - timestamp).total_seconds() > self.dedup_window_seconds
            ]
            for key in expired_keys:
                del self.local_cache[key]
            if expired_keys:
                logger.debug(
                    "cache_cleanup",
                    removed_count=len(expired_keys),
                    remaining_count=len(self.local_cache),
                )


# Global deduplicator instance
_deduplicator: AlertDeduplicator | None = None


def get_deduplicator() -> AlertDeduplicator:
    """Get or create global deduplicator instance.

    Returns:
        AlertDeduplicator instance
    """
    global _deduplicator
    if _deduplicator is None:
        # Try to initialize with Redis if available
        try:
            import redis.asyncio as aioredis

            redis_url = "redis://localhost:6379/0"
            redis_client = aioredis.from_url(redis_url, decode_responses=True)
            _deduplicator = AlertDeduplicator(redis_client)
            logger.info("deduplicator_initialized", backend="redis")
        except Exception:
            _deduplicator = AlertDeduplicator()
            logger.info("deduplicator_initialized", backend="local_cache")
    return _deduplicator


def process_alert(alert: Alert) -> dict[str, Any]:
    """Process a single alert with logging and forwarding.

    Args:
        alert: Alert to process

    Returns:
        Dictionary with processing results
    """
    result: dict[str, Any] = {
        "fingerprint": alert.fingerprint,
        "status": alert.status,
        "alertname": alert.labels.alertname,
        "severity": alert.labels.severity,
        "component": alert.labels.component,
        "processed": False,
        "forwarded": False,
    }

    try:
        # Log alert with structured logging
        log_method = (
            logger.error
            if alert.labels.severity == "critical"
            else logger.warning
            if alert.labels.severity == "warning"
            else logger.info
        )

        log_method(
            "alert_received",
            alertname=alert.labels.alertname,
            severity=alert.labels.severity,
            component=alert.labels.component,
            status=alert.status,
            summary=alert.annotations.summary,
            description=alert.annotations.description,
            value=alert.annotations.value,
            fingerprint=alert.fingerprint,
            starts_at=alert.starts_at.isoformat(),
            ends_at=alert.ends_at.isoformat(),
        )

        # Optional: Forward to external services
        # This would be implemented based on requirements
        # For example, Slack, Discord, PagerDuty, etc.
        # forward_to_slack(alert)
        # forward_to_discord(alert)

        result["processed"] = True
        result["message"] = "Alert processed successfully"

    except Exception as e:
        logger.error(
            "alert_processing_failed",
            fingerprint=alert.fingerprint,
            error=str(e),
        )
        result["message"] = f"Failed to process alert: {e}"

    return result


@router.post(
    "/webhook",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive alerts from AlertManager",
    description="Webhook endpoint for Prometheus AlertManager to send alerts",
)
async def receive_alerts(
    request: Request,
    webhook: AlertManagerWebhook,
) -> AlertResponse:
    """Receive and process alerts from Prometheus AlertManager.

    This endpoint receives alert notifications from AlertManager,
    performs deduplication, logs alerts, and optionally forwards them.

    Args:
        request: FastAPI request object
        webhook: AlertManager webhook payload

    Returns:
        AlertResponse with processing results

    Raises:
        HTTPException: If processing fails
    """
    try:
        logger.info(
            "webhook_received",
            receiver=webhook.receiver,
            status=webhook.status,
            alert_count=len(webhook.alerts),
            group_key=webhook.group_key,
        )

        deduplicator = get_deduplicator()
        processed_alerts: list[dict[str, Any]] = []
        deduplicated_count = 0

        for alert in webhook.alerts:
            # Check for duplicate alerts
            if deduplicator.is_duplicate(alert):
                deduplicated_count += 1
                logger.debug(
                    "alert_deduplicated",
                    fingerprint=alert.fingerprint,
                    alertname=alert.labels.alertname,
                )
                continue

            # Process the alert
            result = process_alert(alert)
            processed_alerts.append(result)

        # Periodic cache cleanup
        deduplicator.cleanup_cache()

        logger.info(
            "webhook_processed",
            total_alerts=len(webhook.alerts),
            processed_alerts=len(processed_alerts),
            deduplicated_alerts=deduplicated_count,
        )

        return AlertResponse(
            status="success",
            message=f"Processed {len(processed_alerts)} alerts, deduplicated {deduplicated_count}",
            processed_alerts=len(processed_alerts),
            deduplicated_alerts=deduplicated_count,
            timestamp=datetime.now(UTC),
        )

    except Exception as e:
        logger.error(
            "webhook_processing_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process alerts: {e}",
        ) from e


@router.get(
    "/health",
    summary="Health check for alert handlers",
    description="Returns health status of alert webhook handler",
)
async def health_check() -> dict[str, str]:
    """Health check endpoint for alert handlers.

    Returns:
        Dictionary with health status
    """
    return {
        "status": "healthy",
        "service": "alert-handlers",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get(
    "/stats",
    summary="Alert statistics",
    description="Returns statistics about alert processing",
)
async def get_stats() -> dict[str, Any]:
    """Get alert processing statistics.

    Returns:
        Dictionary with statistics
    """
    deduplicator = get_deduplicator()

    return {
        "deduplication": {
            "backend": "redis" if deduplicator.redis_client else "local_cache",
            "cache_size": len(deduplicator.local_cache),
            "dedup_window_seconds": deduplicator.dedup_window_seconds,
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }
