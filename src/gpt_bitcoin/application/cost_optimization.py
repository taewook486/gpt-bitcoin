"""
Cost Optimization Strategies.

This module provides cost optimization strategies for GLM API usage,
including intelligent caching, model selection optimization, and
batch request support.

Features:
- Redis-based caching with TTL
- Automatic model selection based on complexity
- Batch request processing
- Cache hit/miss metrics
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Pydantic Models
# =============================================================================


class CacheEntry(BaseModel):
    """Cache entry for API response."""

    query_hash: str = Field(..., description="Hash of the query")
    response: dict[str, Any] = Field(..., description="Cached response")
    model: str = Field(..., description="Model used for the response")
    created_at: float = Field(..., description="Creation timestamp")
    ttl_seconds: int = Field(default=3600, description="Time-to-live in seconds")
    hit_count: int = Field(default=0, description="Number of cache hits")


class BatchRequest(BaseModel):
    """Batch request item."""

    request_id: str = Field(..., description="Unique request ID")
    query: str = Field(..., description="Query text")
    complexity_score: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description="Query complexity score (0-1)",
    )
    priority: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Request priority",
    )


class BatchResult(BaseModel):
    """Result of batch request processing."""

    request_id: str = Field(..., description="Request ID")
    success: bool = Field(..., description="Whether the request succeeded")
    response: dict[str, Any] | None = Field(
        default=None,
        description="Response data if successful",
    )
    error: str | None = Field(default=None, description="Error message if failed")
    model_used: str | None = Field(default=None, description="Model used")
    from_cache: bool = Field(default=False, description="Whether result came from cache")
    cost_krw: float = Field(default=0, description="Cost in KRW")


class ModelSelectionResult(BaseModel):
    """Result of model selection."""

    selected_model: str = Field(..., description="Selected model name")
    estimated_cost_krw: float = Field(..., description="Estimated cost in KRW")
    estimated_tokens: int = Field(..., description="Estimated tokens")
    reasoning: str = Field(..., description="Selection reasoning")


class CacheStats(BaseModel):
    """Cache statistics."""

    total_entries: int = Field(default=0, description="Total cache entries")
    total_hits: int = Field(default=0, description="Total cache hits")
    total_misses: int = Field(default=0, description="Total cache misses")
    hit_rate: float = Field(default=0, ge=0, le=1, description="Cache hit rate")
    estimated_savings_krw: float = Field(
        default=0,
        description="Estimated cost savings in KRW",
    )


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class CostOptimizationConfig:
    """Configuration for cost optimization.

    Attributes:
        cache_ttl_seconds: Cache time-to-live in seconds
        enable_cache: Enable response caching
        redis_url: Redis connection URL (if using Redis)
        max_batch_size: Maximum batch size for batch requests
        complexity_threshold: Threshold for model selection
        glm_4_price_per_1k: GLM-4 price per 1K tokens
        glm_5_price_per_1k: GLM-5 price per 1K tokens
    """

    cache_ttl_seconds: int = 3600  # 1 hour
    enable_cache: bool = True
    redis_url: str | None = None
    max_batch_size: int = 10
    complexity_threshold: float = 0.7
    glm_4_price_per_1k: float = 0.0005
    glm_5_price_per_1k: float = 0.001


# =============================================================================
# In-Memory Cache (Fallback when Redis is not available)
# =============================================================================


class InMemoryCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        """Initialize in-memory cache.

        Args:
            ttl_seconds: Default TTL in seconds
        """
        self._cache: dict[str, CacheEntry] = {}
        self._ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> CacheEntry | None:
        """Get cache entry.

        Args:
            key: Cache key

        Returns:
            Cache entry if found and not expired, None otherwise
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry:
                import time

                if time.time() - entry.created_at > entry.ttl_seconds:
                    del self._cache[key]
                    return None

                entry.hit_count += 1
                return entry

            return None

    async def set(
        self,
        key: str,
        value: dict[str, Any],
        model: str,
        ttl_seconds: int | None = None,
    ) -> None:
        """Set cache entry.

        Args:
            key: Cache key
            value: Value to cache
            model: Model used for the response
            ttl_seconds: Optional TTL override
        """
        async with self._lock:
            import time

            entry = CacheEntry(
                query_hash=key,
                response=value,
                model=model,
                created_at=time.time(),
                ttl_seconds=ttl_seconds or self._ttl_seconds,
            )
            self._cache[key] = entry

    async def delete(self, key: str) -> bool:
        """Delete cache entry.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    async def size(self) -> int:
        """Get number of cache entries.

        Returns:
            Number of cache entries
        """
        return len(self._cache)


# =============================================================================
# Cost Optimizer
# =============================================================================


class CostOptimizer:
    """
    Cost optimization strategies for GLM API usage.

    Provides:
    - Intelligent caching with TTL
    - Automatic model selection based on complexity
    - Batch request processing
    - Cost tracking and optimization

    Example:
        ```python
        optimizer = CostOptimizer(config)

        # Check cache
        if await optimizer.should_use_cache(query_hash):
            response = await optimizer.get_cached_response(query_hash)
        else:
            # Select optimal model
            model = optimizer.select_optimal_model(complexity_score)
            response = await call_glm_api(model, query)
            await optimizer.cache_response(query_hash, response, model)
        ```
    """

    # Model constants
    MODEL_GLM_4 = "glm-4"
    MODEL_GLM_5 = "glm-5"

    def __init__(
        self,
        config: CostOptimizationConfig | None = None,
    ) -> None:
        """Initialize cost optimizer.

        Args:
            config: Optional cost optimization configuration
        """
        self._config = config or CostOptimizationConfig()

        # Initialize cache
        if self._config.enable_cache:
            if self._config.redis_url:
                # Use Redis cache (would require redis-py)
                logger.warning(
                    "Redis URL provided but Redis cache not implemented, using in-memory cache"
                )
                self._cache = InMemoryCache(self._config.cache_ttl_seconds)
            else:
                self._cache = InMemoryCache(self._config.cache_ttl_seconds)
        else:
            self._cache = None

        # Statistics
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info(
            "Cost optimizer initialized",
            cache_enabled=self._config.enable_cache,
            cache_ttl=self._config.cache_ttl_seconds,
        )

    async def should_use_cache(self, query_hash: str) -> bool:
        """
        Check if cached response should be used.

        Args:
            query_hash: Hash of the query

        Returns:
            True if cached response exists and is valid
        """
        if not self._cache:
            return False

        entry = await self._cache.get(query_hash)
        if entry:
            self._cache_hits += 1
            logger.debug(f"Cache hit for query: {query_hash[:8]}")
            return True

        self._cache_misses += 1
        return False

    async def get_cached_response(self, query_hash: str) -> dict[str, Any] | None:
        """
        Get cached response.

        Args:
            query_hash: Hash of the query

        Returns:
            Cached response if available, None otherwise
        """
        if not self._cache:
            return None

        entry = await self._cache.get(query_hash)
        return entry.response if entry else None

    async def cache_response(
        self,
        query_hash: str,
        response: dict[str, Any],
        model: str,
        ttl_seconds: int | None = None,
    ) -> None:
        """
        Cache API response.

        Args:
            query_hash: Hash of the query
            response: Response to cache
            model: Model used for the response
            ttl_seconds: Optional TTL override
        """
        if not self._cache:
            return

        await self._cache.set(
            key=query_hash,
            value=response,
            model=model,
            ttl_seconds=ttl_seconds or self._config.cache_ttl_seconds,
        )

        logger.debug(f"Cached response for query: {query_hash[:8]}")

    def select_optimal_model(
        self,
        complexity_score: float,
        estimated_tokens: int = 1000,
    ) -> ModelSelectionResult:
        """
        Select optimal model based on complexity score.

        GLM-4 is cheaper but less capable.
        GLM-5 is more expensive but more capable.

        Selection strategy:
        - complexity < 0.5: Use GLM-4 (simple queries)
        - complexity >= 0.7: Use GLM-5 (complex queries)
        - 0.5 <= complexity < 0.7: Balance based on estimated tokens

        Args:
            complexity_score: Query complexity score (0-1)
            estimated_tokens: Estimated tokens for the query

        Returns:
            Model selection result with reasoning
        """
        # Simple queries: always use GLM-4
        if complexity_score < 0.5:
            selected_model = self.MODEL_GLM_4
            reasoning = "Low complexity query, using cost-effective GLM-4"

        # Complex queries: always use GLM-5
        elif complexity_score >= self._config.complexity_threshold:
            selected_model = self.MODEL_GLM_5
            reasoning = "High complexity query, using capable GLM-5"

        # Medium complexity: balance based on token count
        else:
            # For smaller token counts, use GLM-4
            if estimated_tokens < 500:
                selected_model = self.MODEL_GLM_4
                reasoning = "Medium complexity with small token count, using cost-effective GLM-4"
            else:
                selected_model = self.MODEL_GLM_5
                reasoning = (
                    "Medium complexity with larger token count, using capable GLM-5 for quality"
                )

        # Calculate estimated cost
        if selected_model == self.MODEL_GLM_4:
            price_per_1k = self._config.glm_4_price_per_1k
        else:
            price_per_1k = self._config.glm_5_price_per_1k

        estimated_cost = (estimated_tokens / 1000) * price_per_1k

        return ModelSelectionResult(
            selected_model=selected_model,
            estimated_cost_krw=estimated_cost,
            estimated_tokens=estimated_tokens,
            reasoning=reasoning,
        )

    async def batch_requests(
        self,
        requests: list[BatchRequest],
        process_fn,
    ) -> list[BatchResult]:
        """
        Process batch requests with caching and optimization.

        Args:
            requests: List of batch requests
            process_fn: Async function to process a single request
                       Signature: async (model: str, query: str) -> dict

        Returns:
            List of batch results
        """
        if len(requests) > self._config.max_batch_size:
            raise ValueError(
                f"Batch size {len(requests)} exceeds maximum {self._config.max_batch_size}"
            )

        results: list[BatchResult] = []

        # Process requests in parallel (up to max_batch_size)
        tasks = []
        for request in requests:
            task = self._process_single_request(request, process_fn)
            tasks.append(task)

        # Gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(
                    BatchResult(
                        request_id=requests[i].request_id,
                        success=False,
                        error=str(result),
                    )
                )
            else:
                final_results.append(result)

        return final_results

    async def _process_single_request(
        self,
        request: BatchRequest,
        process_fn,
    ) -> BatchResult:
        """Process a single request with caching.

        Args:
            request: Batch request to process
            process_fn: Processing function

        Returns:
            Batch result
        """
        # Calculate query hash
        query_hash = self._calculate_query_hash(request.query)

        # Check cache
        if await self.should_use_cache(query_hash):
            cached = await self.get_cached_response(query_hash)
            if cached:
                return BatchResult(
                    request_id=request.request_id,
                    success=True,
                    response=cached,
                    from_cache=True,
                    cost_krw=0,  # No cost for cached response
                )

        # Select optimal model
        selection = self.select_optimal_model(
            complexity_score=request.complexity_score,
            estimated_tokens=len(request.query) // 4,  # Rough estimate
        )

        try:
            # Process request
            response = await process_fn(selection.selected_model, request.query)

            # Cache response
            await self.cache_response(
                query_hash=query_hash,
                response=response,
                model=selection.selected_model,
            )

            return BatchResult(
                request_id=request.request_id,
                success=True,
                response=response,
                model_used=selection.selected_model,
                from_cache=False,
                cost_krw=selection.estimated_cost_krw,
            )

        except Exception as e:
            logger.error(
                f"Batch request failed: {request.request_id}",
                error=str(e),
            )
            return BatchResult(
                request_id=request.request_id,
                success=False,
                error=str(e),
            )

    @staticmethod
    def _calculate_query_hash(query: str) -> str:
        """Calculate hash for query string.

        Args:
            query: Query string

        Returns:
            SHA256 hash of the query
        """
        return hashlib.sha256(query.encode()).hexdigest()

    def calculate_complexity_score(
        self,
        query: str,
        has_image: bool = False,
        context_length: int = 0,
    ) -> float:
        """
        Calculate complexity score for a query.

        Factors:
        - Query length
        - Presence of image
        - Context length
        - Keyword complexity

        Args:
            query: Query text
            has_image: Whether query includes image
            context_length: Length of context/conversation history

        Returns:
            Complexity score (0-1)
        """
        score = 0.0

        # Query length factor (0-0.3)
        query_len = len(query)
        if query_len > 500:
            score += 0.3
        elif query_len > 200:
            score += 0.2
        elif query_len > 100:
            score += 0.1

        # Image factor (0-0.3)
        if has_image:
            score += 0.3

        # Context length factor (0-0.2)
        if context_length > 1000:
            score += 0.2
        elif context_length > 500:
            score += 0.1

        # Keyword complexity factor (0-0.2)
        complex_keywords = [
            "analyze",
            "compare",
            "evaluate",
            "predict",
            "forecast",
            "optimize",
            "recommend",
        ]
        keyword_count = sum(1 for kw in complex_keywords if kw in query.lower())
        score += min(0.2, keyword_count * 0.05)

        return min(1.0, score)

    async def get_cache_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0

        # Estimate savings (assuming average cost per request)
        avg_cost = 0.01  # 0.01 KRW average
        estimated_savings = self._cache_hits * avg_cost

        cache_size = await self._cache.size() if self._cache else 0

        return CacheStats(
            total_entries=cache_size,
            total_hits=self._cache_hits,
            total_misses=self._cache_misses,
            hit_rate=hit_rate,
            estimated_savings_krw=estimated_savings,
        )

    async def clear_cache(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        if not self._cache:
            return 0

        count = await self._cache.clear()
        logger.info(f"Cleared {count} cache entries")
        return count


# =============================================================================
# Global Instance
# =============================================================================

_cost_optimizer: CostOptimizer | None = None


def get_cost_optimizer(config: CostOptimizationConfig | None = None) -> CostOptimizer:
    """Get or create the global cost optimizer instance.

    Args:
        config: Optional cost optimization configuration

    Returns:
        Global CostOptimizer instance
    """
    global _cost_optimizer
    if _cost_optimizer is None:
        _cost_optimizer = CostOptimizer(config)
    return _cost_optimizer


__all__ = [
    "BatchRequest",
    "BatchResult",
    "CacheEntry",
    "CacheStats",
    "CostOptimizationConfig",
    "CostOptimizer",
    "InMemoryCache",
    "ModelSelectionResult",
    "get_cost_optimizer",
]
