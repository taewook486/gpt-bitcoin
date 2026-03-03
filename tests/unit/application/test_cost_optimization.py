"""
Unit tests for Cost Optimization.

Tests cover:
- Caching strategies
- Model selection optimization
- Batch request processing
- Complexity score calculation
"""
from __future__ import annotations

import pytest

from gpt_bitcoin.application.cost_optimization import (
    CostOptimizer,
    CostOptimizationConfig,
    CacheEntry,
    BatchRequest,
    BatchResult,
    ModelSelectionResult,
    CacheStats,
    InMemoryCache,
)


@pytest.fixture
async def cost_optimizer():
    """Create cost optimizer with default configuration."""
    config = CostOptimizationConfig(
        enable_cache=True,
        cache_ttl_seconds=3600,
        max_batch_size=5,
        complexity_threshold=0.7,
    )
    optimizer = CostOptimizer(config)
    yield optimizer
    await optimizer.clear_cache()


@pytest.fixture
def in_memory_cache():
    """Create in-memory cache."""
    return InMemoryCache(ttl_seconds=3600)


class TestInMemoryCache:
    """Test cases for InMemoryCache."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, in_memory_cache: InMemoryCache) -> None:
        """Test setting and getting cache entries."""
        key = "test-key-123"
        value = {"result": "success", "data": [1, 2, 3]}

        await in_memory_cache.set(key, value, model="glm-4")
        entry = await in_memory_cache.get(key)

        assert entry is not None
        assert entry.response == value
        assert entry.model == "glm-4"
        assert entry.hit_count == 1

    @pytest.mark.asyncio
    async def test_cache_miss(self, in_memory_cache: InMemoryCache) -> None:
        """Test cache miss."""
        entry = await in_memory_cache.get("nonexistent-key")
        assert entry is None

    @pytest.mark.asyncio
    async def test_cache_delete(self, in_memory_cache: InMemoryCache) -> None:
        """Test cache deletion."""
        key = "delete-test"

        await in_memory_cache.set(key, {"data": "test"}, model="glm-4")
        deleted = await in_memory_cache.delete(key)

        assert deleted is True

        entry = await in_memory_cache.get(key)
        assert entry is None

    @pytest.mark.asyncio
    async def test_cache_clear(self, in_memory_cache: InMemoryCache) -> None:
        """Test cache clearing."""
        await in_memory_cache.set("key1", {"a": 1}, model="glm-4")
        await in_memory_cache.set("key2", {"b": 2}, model="glm-5")

        count = await in_memory_cache.clear()
        assert count == 2

        size = await in_memory_cache.size()
        assert size == 0

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self) -> None:
        """Test cache TTL expiration."""
        import time

        cache = InMemoryCache(ttl_seconds=1)  # 1 second TTL

        await cache.set("key", {"data": "test"}, model="glm-4")

        # Should exist immediately
        entry = await cache.get("key")
        assert entry is not None

        # Wait for TTL to expire
        time.sleep(1.5)

        # Should be expired
        entry = await cache.get("key")
        assert entry is None


class TestCostOptimizer:
    """Test cases for CostOptimizer."""

    @pytest.mark.asyncio
    async def test_should_use_cache_miss(
        self,
        cost_optimizer: CostOptimizer,
    ) -> None:
        """Test cache miss detection."""
        query_hash = "abc123def456"

        result = await cost_optimizer.should_use_cache(query_hash)
        assert result is False

    @pytest.mark.asyncio
    async def test_should_use_cache_hit(
        self,
        cost_optimizer: CostOptimizer,
    ) -> None:
        """Test cache hit detection."""
        query_hash = "test-hash-123"
        response = {"decision": "buy", "confidence": 0.9}

        # Cache the response
        await cost_optimizer.cache_response(query_hash, response, "glm-4")

        # Check cache hit
        result = await cost_optimizer.should_use_cache(query_hash)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_cached_response(
        self,
        cost_optimizer: CostOptimizer,
    ) -> None:
        """Test retrieving cached response."""
        query_hash = "cached-query"
        response = {"decision": "sell", "confidence": 0.8}

        await cost_optimizer.cache_response(query_hash, response, "glm-5")

        cached = await cost_optimizer.get_cached_response(query_hash)
        assert cached == response

    @pytest.mark.asyncio
    async def test_cache_disabled(self) -> None:
        """Test optimizer with caching disabled."""
        config = CostOptimizationConfig(enable_cache=False)
        optimizer = CostOptimizer(config)

        query_hash = "test-hash"
        result = await optimizer.should_use_cache(query_hash)
        assert result is False

        await optimizer.cache_response(query_hash, {"data": "test"}, "glm-4")
        cached = await optimizer.get_cached_response(query_hash)
        assert cached is None

    def test_select_optimal_model_low_complexity(
        self,
        cost_optimizer: CostOptimizer,
    ) -> None:
        """Test model selection for low complexity."""
        result = cost_optimizer.select_optimal_model(
            complexity_score=0.3,
            estimated_tokens=500,
        )

        assert result.selected_model == "glm-4"
        assert "cost-effective" in result.reasoning.lower()
        assert result.estimated_cost_krw > 0

    def test_select_optimal_model_high_complexity(
        self,
        cost_optimizer: CostOptimizer,
    ) -> None:
        """Test model selection for high complexity."""
        result = cost_optimizer.select_optimal_model(
            complexity_score=0.8,
            estimated_tokens=1000,
        )

        assert result.selected_model == "glm-5"
        assert "capable" in result.reasoning.lower()
        assert result.estimated_cost_krw > 0

    def test_select_optimal_model_medium_complexity_small_tokens(
        self,
        cost_optimizer: CostOptimizer,
    ) -> None:
        """Test model selection for medium complexity with small tokens."""
        result = cost_optimizer.select_optimal_model(
            complexity_score=0.6,
            estimated_tokens=300,
        )

        assert result.selected_model == "glm-4"

    def test_select_optimal_model_medium_complexity_large_tokens(
        self,
        cost_optimizer: CostOptimizer,
    ) -> None:
        """Test model selection for medium complexity with large tokens."""
        result = cost_optimizer.select_optimal_model(
            complexity_score=0.6,
            estimated_tokens=800,
        )

        assert result.selected_model == "glm-5"

    def test_calculate_complexity_score_simple(
        self,
        cost_optimizer: CostOptimizer,
    ) -> None:
        """Test complexity score for simple query."""
        query = "What is the price of Bitcoin?"

        score = cost_optimizer.calculate_complexity_score(query)

        assert 0 <= score <= 1
        assert score < 0.3  # Simple query should have low score

    def test_calculate_complexity_score_complex(
        self,
        cost_optimizer: CostOptimizer,
    ) -> None:
        """Test complexity score for complex query."""
        query = """
        Please analyze the current market conditions, evaluate the risk factors,
        and provide a comprehensive forecast for Bitcoin price movement over the
        next week. Compare with historical trends and optimize your recommendation.
        """

        score = cost_optimizer.calculate_complexity_score(
            query=query,
            has_image=True,
            context_length=1500,
        )

        assert 0 <= score <= 1
        assert score > 0.5  # Complex query should have high score

    def test_calculate_complexity_score_with_keywords(
        self,
        cost_optimizer: CostOptimizer,
    ) -> None:
        """Test complexity score with complex keywords."""
        query = "Analyze and predict the optimal trading strategy."

        score = cost_optimizer.calculate_complexity_score(query)

        assert score > 0  # Should have some complexity from keywords

    @pytest.mark.asyncio
    async def test_batch_requests_success(
        self,
        cost_optimizer: CostOptimizer,
    ) -> None:
        """Test successful batch request processing."""

        async def mock_process(model: str, query: str) -> dict:
            return {"model": model, "response": f"Processed: {query[:20]}"}

        requests = [
            BatchRequest(request_id="req-1", query="Query 1", complexity_score=0.3),
            BatchRequest(request_id="req-2", query="Query 2", complexity_score=0.8),
        ]

        results = await cost_optimizer.batch_requests(requests, mock_process)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert results[0].model_used == "glm-4"
        assert results[1].model_used == "glm-5"

    @pytest.mark.asyncio
    async def test_batch_requests_with_cache(
        self,
        cost_optimizer: CostOptimizer,
    ) -> None:
        """Test batch request processing with cache hits."""

        async def mock_process(model: str, query: str) -> dict:
            return {"model": model, "data": "new"}

        # Pre-cache one request
        query1 = "Cached query"
        query1_hash = cost_optimizer._calculate_query_hash(query1)
        await cost_optimizer.cache_response(
            query1_hash,
            {"model": "glm-4", "data": "cached"},
            "glm-4",
        )

        requests = [
            BatchRequest(request_id="req-1", query=query1, complexity_score=0.3),
            BatchRequest(request_id="req-2", query="New query", complexity_score=0.5),
        ]

        results = await cost_optimizer.batch_requests(requests, mock_process)

        assert len(results) == 2
        assert results[0].from_cache is True
        assert results[0].cost_krw == 0  # No cost for cached
        assert results[1].from_cache is False
        assert results[1].cost_krw > 0

    @pytest.mark.asyncio
    async def test_batch_requests_error_handling(
        self,
        cost_optimizer: CostOptimizer,
    ) -> None:
        """Test batch request error handling."""

        async def mock_process(model: str, query: str) -> dict:
            if "error" in query.lower():
                raise ValueError("Simulated error")
            return {"success": True}

        requests = [
            BatchRequest(request_id="req-1", query="Normal query", complexity_score=0.3),
            BatchRequest(request_id="req-2", query="Error query", complexity_score=0.5),
        ]

        results = await cost_optimizer.batch_requests(requests, mock_process)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert results[1].error is not None

    @pytest.mark.asyncio
    async def test_batch_requests_size_limit(
        self,
        cost_optimizer: CostOptimizer,
    ) -> None:
        """Test batch request size limit."""

        async def mock_process(model: str, query: str) -> dict:
            return {"success": True}

        # Create more requests than max_batch_size (5)
        requests = [
            BatchRequest(request_id=f"req-{i}", query=f"Query {i}", complexity_score=0.5)
            for i in range(10)
        ]

        with pytest.raises(ValueError, match="exceeds maximum"):
            await cost_optimizer.batch_requests(requests, mock_process)

    @pytest.mark.asyncio
    async def test_get_cache_stats(
        self,
        cost_optimizer: CostOptimizer,
    ) -> None:
        """Test cache statistics."""
        # Generate some cache activity
        query_hash = "stats-test"
        await cost_optimizer.cache_response(
            query_hash,
            {"data": "test"},
            "glm-4",
        )

        # Hit
        await cost_optimizer.should_use_cache(query_hash)

        # Miss
        await cost_optimizer.should_use_cache("nonexistent")

        stats = await cost_optimizer.get_cache_stats()

        assert isinstance(stats, CacheStats)
        assert stats.total_entries >= 1
        assert stats.total_hits >= 1
        assert stats.total_misses >= 1
        assert 0 <= stats.hit_rate <= 1


class TestCostOptimizationConfig:
    """Test cases for CostOptimizationConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = CostOptimizationConfig()

        assert config.cache_ttl_seconds == 3600
        assert config.enable_cache is True
        assert config.redis_url is None
        assert config.max_batch_size == 10
        assert config.complexity_threshold == 0.7

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = CostOptimizationConfig(
            cache_ttl_seconds=7200,
            enable_cache=False,
            redis_url="redis://localhost:6379",
            max_batch_size=20,
        )

        assert config.cache_ttl_seconds == 7200
        assert config.enable_cache is False
        assert config.redis_url == "redis://localhost:6379"
        assert config.max_batch_size == 20


class TestPydanticModels:
    """Test cases for Pydantic models."""

    def test_cache_entry(self) -> None:
        """Test CacheEntry model."""
        import time

        entry = CacheEntry(
            query_hash="abc123",
            response={"data": "test"},
            model="glm-4",
            created_at=time.time(),
        )

        assert entry.query_hash == "abc123"
        assert entry.ttl_seconds == 3600
        assert entry.hit_count == 0

    def test_batch_request(self) -> None:
        """Test BatchRequest model."""
        request = BatchRequest(
            request_id="req-123",
            query="Test query",
            complexity_score=0.75,
            priority="high",
        )

        assert request.request_id == "req-123"
        assert request.complexity_score == 0.75
        assert request.priority == "high"

    def test_batch_result(self) -> None:
        """Test BatchResult model."""
        result = BatchResult(
            request_id="req-123",
            success=True,
            response={"decision": "buy"},
            model_used="glm-5",
            from_cache=False,
            cost_krw=0.05,
        )

        assert result.success is True
        assert result.from_cache is False
        assert result.cost_krw == 0.05

    def test_model_selection_result(self) -> None:
        """Test ModelSelectionResult model."""
        result = ModelSelectionResult(
            selected_model="glm-4",
            estimated_cost_krw=0.01,
            estimated_tokens=1000,
            reasoning="Low complexity query",
        )

        assert result.selected_model == "glm-4"
        assert result.estimated_tokens == 1000

    def test_cache_stats(self) -> None:
        """Test CacheStats model."""
        stats = CacheStats(
            total_entries=100,
            total_hits=75,
            total_misses=25,
            hit_rate=0.75,
            estimated_savings_krw=50.0,
        )

        assert stats.hit_rate == 0.75
        assert stats.estimated_savings_krw == 50.0
