"""
재시도 핸들러 단위 테스트.

지수 백오프와 프로바이더 전환을 포함한 재시도 로직을 테스트합니다.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, Mock

import pytest

from gpt_bitcoin.infrastructure.exceptions import GLMAPIError, RateLimitError
from gpt_bitcoin.infrastructure.external.retry_handler import (
    ProviderHealthTracker,
    call_with_retry,
)


class TestRetryOnTimeout:
    """타임아웃 시 재시도 테스트."""

    @pytest.mark.asyncio
    async def test_retry_on_timeout_success(self):
        """
        [GIVEN] 타임아웃이 발생하는 API 클라이언트가 있고
        [WHEN] 2번째 시도에서 성공할 때
        [THEN] 성공적인 응답을 반환해야 한다
        """
        # Arrange
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"decision": "hold"}'))]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        # 첫 번째 호출은 타임아웃, 두 번째는 성공
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("Request timeout")
            return mock_response

        mock_client.chat.completions.create = AsyncMock(side_effect=side_effect)

        # Act
        result = await call_with_retry(
            client=mock_client,
            messages=[{"role": "user", "content": "test"}],
            model="glm-5",
            max_retries=3,
            initial_delay=0.1,
        )

        # Assert
        assert result["content"] == '{"decision": "hold"}'
        assert call_count == 2


class TestMaxRetriesExceeded:
    """최대 재시도 초과 테스트."""

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_raises_error(self):
        """
        [GIVEN] 계속 실패하는 API 클라이언트가 있고
        [WHEN] 최대 재시도 횟수를 초과할 때
        [THEN] GLMAPIError를 발생시켜야 한다
        """
        # Arrange
        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=TimeoutError("Persistent timeout")
        )

        # Act & Assert
        with pytest.raises(GLMAPIError) as exc_info:
            await call_with_retry(
                client=mock_client,
                messages=[{"role": "user", "content": "test"}],
                model="glm-5",
                max_retries=3,
                initial_delay=0.1,
            )

        error_message = str(exc_info.value).lower()
        assert (
            "재시도" in error_message or "max_retries" in error_message or "retry" in error_message
        )


class TestRateLimitHandling:
    """Rate Limit 처리 테스트."""

    @pytest.mark.asyncio
    async def test_rate_limit_handling_with_backoff(self):
        """
        [GIVEN] Rate Limit(429)가 발생하는 API 클라이언트가 있고
        [WHEN] exponential backoff로 재시도할 때
        [THEN] backoff 후 성공해야 한다
        """
        # Arrange
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"decision": "buy"}'))]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("Rate limit exceeded", retry_after=1)
            return mock_response

        mock_client.chat.completions.create = AsyncMock(side_effect=side_effect)

        # Act
        start_time = time.time()
        result = await call_with_retry(
            client=mock_client,
            messages=[{"role": "user", "content": "test"}],
            model="glm-5",
            max_retries=3,
            initial_delay=0.1,
        )
        elapsed_time = time.time() - start_time

        # Assert
        assert result["content"] == '{"decision": "buy"}'
        assert call_count == 2
        # Rate Limit은 retry_after 만큼 대기해야 함
        assert elapsed_time >= 1.0


class TestProviderSwitching:
    """프로바이더 전환 테스트."""

    @pytest.mark.asyncio
    async def test_provider_switch_on_consecutive_failures(self):
        """
        [GIVEN] 프로바이더가 연속 3회 실패하고
        [WHEN] 다음 호출을 시도할 때
        [THEN] OpenAI로 전환해야 한다
        """
        # Arrange
        mock_glm_client = Mock()
        mock_openai_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"decision": "sell"}'))]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        # GLM 클라이언트는 항상 실패
        mock_glm_client.chat.completions.create = AsyncMock(side_effect=TimeoutError("GLM timeout"))
        # OpenAI 클라이언트는 성공
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        tracker = ProviderHealthTracker()

        # Act - 3회 연속 실패 기록
        for _ in range(3):
            tracker.record_failure("glm")

        # Assert - OpenAI가 권장됨
        assert tracker.should_use_fallback("glm") is True

    @pytest.mark.asyncio
    async def test_provider_recovery_after_timeout(self):
        """
        [GIVEN] 프로바이더가 실패 상태이고
        [WHEN] 복구 타임아웃(5분)이 지났을 때
        [THEN] 프로바이더가 복구되어야 한다
        """
        # Arrange
        tracker = ProviderHealthTracker(failure_timeout=1)  # 1초로 단축

        # Act - 3회 실패 기록
        for _ in range(3):
            tracker.record_failure("glm")

        assert tracker.should_use_fallback("glm") is True

        # 1초 대기 (복구 타임아웃)
        time.sleep(1.1)

        # Assert - 복구 후 폴백 불필요
        assert tracker.should_use_fallback("glm") is False


class TestExponentialBackoff:
    """지수 백오프 테스트."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """
        [GIVEN] 연속 실패하는 API 클라이언트가 있고
        [WHEN] exponential backoff로 재시도할 때
        [THEN] 지연 시간이 지수적으로 증가해야 한다
        """
        # Arrange
        mock_client = Mock()
        call_times = []

        async def side_effect(*args, **kwargs):
            call_times.append(time.time())
            if len(call_times) < 4:  # 3회 실패
                raise TimeoutError("Timeout")
            # 4번째 시도에서 성공
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content='{"decision": "hold"}'))]
            mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
            return mock_response

        mock_client.chat.completions.create = AsyncMock(side_effect=side_effect)

        # Act
        await call_with_retry(
            client=mock_client,
            messages=[{"role": "user", "content": "test"}],
            model="glm-5",
            max_retries=5,
            initial_delay=0.1,
        )

        # Assert - 지연 시간 검증
        # 1번째 시도: 0초
        # 2번째 시도: 0.1초 (0.1 * 2^0)
        # 3번째 시도: 0.2초 (0.1 * 2^1)
        # 4번째 시도: 0.4초 (0.1 * 2^2)
        assert len(call_times) == 4

        # 첫 번째와 두 번째 사이의 지연
        delay_1_2 = call_times[1] - call_times[0]
        # 두 번째와 세 번째 사이의 지연
        delay_2_3 = call_times[2] - call_times[1]
        # 세 번째와 네 번째 사이의 지연
        delay_3_4 = call_times[3] - call_times[2]

        # 지연 시간이 증가하는지 확인 (약간의 오차 허용)
        assert delay_2_3 > delay_1_2 * 0.8  # 대략 2배 증가
        assert delay_3_4 > delay_2_3 * 0.8  # 대략 2배 증가


class TestSuccessfulCallNoRetry:
    """성공 시 재시도 없음 테스트."""

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """
        [GIVEN] 정상 작동하는 API 클라이언트가 있고
        [WHEN] API 호출을 시도할 때
        [THEN] 재시도 없이 즉시 성공해야 한다
        """
        # Arrange
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"decision": "hold"}'))]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Act
        result = await call_with_retry(
            client=mock_client,
            messages=[{"role": "user", "content": "test"}],
            model="glm-5",
            max_retries=3,
            initial_delay=0.1,
        )

        # Assert
        assert result["content"] == '{"decision": "hold"}'
        mock_client.chat.completions.create.assert_called_once()


class TestRequestContextPreservation:
    """재시도 시 요청 컨텍스트 보존 테스트."""

    @pytest.mark.asyncio
    async def test_retry_preserves_request_context(self):
        """
        [GIVEN] 특정 파라미터가 있는 API 요청이 있고
        [WHEN] 재시도가 발생할 때
        [THEN] 모든 요청 파라미터가 보존되어야 한다
        """
        # Arrange
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"decision": "buy"}'))]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        call_args_list = []

        async def side_effect(*args, **kwargs):
            call_args_list.append((args, kwargs))
            if len(call_args_list) == 1:
                raise TimeoutError("Timeout")
            return mock_response

        mock_client.chat.completions.create = AsyncMock(side_effect=side_effect)

        messages = [
            {"role": "system", "content": "You are a trading assistant"},
            {"role": "user", "content": "Analyze this market"},
        ]

        # Act
        result = await call_with_retry(
            client=mock_client,
            messages=messages,
            model="glm-5",
            max_retries=3,
            initial_delay=0.1,
            temperature=0.7,
        )

        # Assert - 모든 호출이 동일한 파라미터로 수행되었는지 확인
        assert len(call_args_list) == 2

        # 첫 번째 호출의 파라미터
        _, first_kwargs = call_args_list[0]
        assert first_kwargs["model"] == "glm-5"
        assert first_kwargs["messages"] == messages
        assert first_kwargs["temperature"] == 0.7

        # 두 번째 호출의 파라미터 (동일해야 함)
        _, second_kwargs = call_args_list[1]
        assert second_kwargs["model"] == "glm-5"
        assert second_kwargs["messages"] == messages
        assert second_kwargs["temperature"] == 0.7


class TestConnectionErrorHandling:
    """연결 에러 처리 테스트."""

    @pytest.mark.asyncio
    async def test_connection_error_retry(self):
        """
        [GIVEN] 연결 에러가 발생하는 API 클라이언트가 있고
        [WHEN] 재시도할 때
        [THEN] 연결 에러 후 성공해야 한다
        """
        # Arrange
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"decision": "hold"}'))]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Connection refused")
            return mock_response

        mock_client.chat.completions.create = AsyncMock(side_effect=side_effect)

        # Act
        result = await call_with_retry(
            client=mock_client,
            messages=[{"role": "user", "content": "test"}],
            model="glm-5",
            max_retries=3,
            initial_delay=0.1,
        )

        # Assert
        assert result["content"] == '{"decision": "hold"}'
        assert call_count == 2


class TestSyncClientHandling:
    """동기 클라이언트 처리 테스트."""

    @pytest.mark.asyncio
    async def test_sync_client_handling(self):
        """
        [GIVEN] 동기 API 클라이언트가 있고
        [WHEN] 비동기 함수에서 호출할 때
        [THEN] 스레드 풀에서 실행되어야 한다
        """
        # Arrange
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"decision": "buy"}'))]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        # 동기 mock (비동기 아님)
        mock_client.chat.completions.create = Mock(return_value=mock_response)

        # Act
        result = await call_with_retry(
            client=mock_client,
            messages=[{"role": "user", "content": "test"}],
            model="glm-5",
            max_retries=3,
            initial_delay=0.1,
        )

        # Assert
        assert result["content"] == '{"decision": "buy"}'
        mock_client.chat.completions.create.assert_called_once()


class TestProviderHealthTrackerEdgeCases:
    """프로바이더 건강 추적기 edge case 테스트."""

    def test_get_failure_count_for_unknown_provider(self):
        """
        [GIVEN] 실패 기록이 없는 프로바이더가 있고
        [WHEN] 실패 횟수를 조회할 때
        [THEN] 0을 반환해야 한다
        """
        # Arrange
        tracker = ProviderHealthTracker()

        # Act
        count = tracker.get_failure_count("unknown_provider")

        # Assert
        assert count == 0

    def test_multiple_providers_independent_tracking(self):
        """
        [GIVEN] 여러 프로바이더가 있고
        [WHEN] 각 프로바이더가 독립적으로 실패할 때
        [THEN] 각 프로바이더의 실패 카운트가 독립적이어야 한다
        """
        # Arrange
        tracker = ProviderHealthTracker()

        # Act - GLM 2회 실패
        for _ in range(2):
            tracker.record_failure("glm")

        # OpenAI 1회 실패
        tracker.record_failure("openai")

        # Assert
        assert tracker.get_failure_count("glm") == 2
        assert tracker.get_failure_count("openai") == 1
        assert tracker.should_use_fallback("glm") is False  # 임계값 미달
        assert tracker.should_use_fallback("openai") is False

    def test_success_resets_failure_count(self):
        """
        [GIVEN] 실패 카운트가 있는 프로바이더가 있고
        [WHEN] 성공할 때
        [THEN] 실패 카운트가 리셋되어야 한다
        """
        # Arrange
        tracker = ProviderHealthTracker()

        # 2회 실패 기록
        for _ in range(2):
            tracker.record_failure("glm")

        assert tracker.get_failure_count("glm") == 2

        # Act - 성공 기록
        tracker.record_success("glm")

        # Assert - 카운터 리셋
        assert tracker.get_failure_count("glm") == 0
        assert tracker.should_use_fallback("glm") is False

    def test_timeout_reset_after_recovery(self):
        """
        [GIVEN] 실패 상태의 프로바이더가 있고
        [WHEN] 복구 타임아웃이 경과했을 때
        [THEN] 실패 카운터가 리셋되어야 한다
        """
        # Arrange
        tracker = ProviderHealthTracker(failure_timeout=0.1)  # 100ms

        # 3회 실패 (임계값 도달)
        for _ in range(3):
            tracker.record_failure("glm")

        assert tracker.should_use_fallback("glm") is True

        # Act - 타임아웃 대기
        time.sleep(0.15)

        # should_use_fallback이 내부적으로 리셋을 수행
        result = tracker.should_use_fallback("glm")

        # Assert - 리셋 후 False 반환
        assert result is False
        assert tracker.get_failure_count("glm") == 0
