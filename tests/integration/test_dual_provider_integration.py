"""
듀얼 프로바이더 통합 테스트.

이 모듈은 GLM-5와 OpenAI 간의 듀얼 프로바이더 통합 시나리오를 테스트합니다.
End-to-end 테스트로 실제 API 호출 없이 mock을 사용합니다.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from gpt_bitcoin.infrastructure.external.ai_client_factory import (
    get_ai_client,
    get_default_model,
)
from gpt_bitcoin.infrastructure.external.retry_handler import (
    ProviderHealthTracker,
    call_with_retry,
)


class TestDualProviderE2E:
    """End-to-end 듀얼 프로바이더 시나리오 테스트."""

    @patch("gpt_bitcoin.infrastructure.external.ai_client_factory.os.environ.get")
    @patch("gpt_bitcoin.infrastructure.external.ai_client_factory.ZhipuAI")
    def test_e2e_glm_success_flow(self, mock_zhipuai: Mock, mock_environ_get: Mock):
        """
        GLM-5 성공 플로우 End-to-End 테스트.

        GIVEN: GLM_API_KEY가 설정됨
        WHEN: 클라이언트 생성 및 API 호출
        THEN: GLM-5가 정상적으로 응답
        """

        # Arrange
        def mock_env_glm(key: str, default: str | None = None) -> str | None:
            env_map = {
                "GLM_API_KEY": "test-glm-api-key",
                "AI_PROVIDER": "auto",
                "AI_TIMEOUT": "30",
            }
            return env_map.get(key, default)

        mock_environ_get.side_effect = mock_env_glm

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"decision": "hold", "reason": "Test"}'
        mock_client.chat.completions.create.return_value = mock_response
        mock_zhipuai.return_value = mock_client

        # Act
        client = get_ai_client()
        response = client.chat.completions.create(
            model=get_default_model(),
            messages=[{"role": "user", "content": "Test"}],
        )

        # Assert
        assert response.choices[0].message.content == '{"decision": "hold", "reason": "Test"}'
        mock_zhipuai.assert_called_once()

    @patch("gpt_bitcoin.infrastructure.external.ai_client_factory.os.environ.get")
    @patch("gpt_bitcoin.infrastructure.external.ai_client_factory.OpenAI")
    @patch("gpt_bitcoin.infrastructure.external.ai_client_factory.ZhipuAI")
    def test_e2e_glm_failure_openai_fallback(
        self,
        mock_zhipuai: Mock,
        mock_openai: Mock,
        mock_environ_get: Mock,
    ):
        """
        GLM-5 실패 시 OpenAI 폴백 End-to-End 테스트.

        GIVEN: GLM_API_KEY와 OPENAI_API_KEY가 모두 설정됨
        WHEN: GLM-5 초기화 실패
        THEN: OpenAI로 자동 폴백
        """

        # Arrange
        def mock_env_both(key: str, default: str | None = None) -> str | None:
            env_map = {
                "GLM_API_KEY": "invalid-glm-key",
                "OPENAI_API_KEY": "test-openai-api-key",
                "AI_PROVIDER": "auto",
                "AI_TIMEOUT": "30",
            }
            return env_map.get(key, default)

        mock_environ_get.side_effect = mock_env_both
        mock_zhipuai.side_effect = Exception("GLM authentication failed")

        mock_openai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '{"decision": "hold", "reason": "OpenAI fallback"}'
        mock_openai_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_openai_client

        # Act
        client = get_ai_client()
        response = client.chat.completions.create(
            model=get_default_model(),
            messages=[{"role": "user", "content": "Test"}],
        )

        # Assert
        assert "OpenAI fallback" in response.choices[0].message.content
        mock_openai.assert_called_once()


class TestProviderSwitching:
    """프로바이더 전환 시나리오 테스트."""

    def test_provider_switching_after_consecutive_failures(self):
        """
        연속 실패 후 프로바이더 전환 테스트.

        GIVEN: ProviderHealthTracker가 초기화됨
        WHEN: GLM 프로바이더가 3회 연속 실패
        THEN: should_use_fallback()이 True 반환
        """
        # Arrange
        tracker = ProviderHealthTracker(
            failure_threshold=3,
            failure_timeout=300,
        )

        # Act
        tracker.record_failure("glm")
        assert not tracker.should_use_fallback("glm")

        tracker.record_failure("glm")
        assert not tracker.should_use_fallback("glm")

        tracker.record_failure("glm")
        # 3회 실패 후 폴백 사용 권장
        assert tracker.should_use_fallback("glm")

    def test_provider_recovery_after_timeout(self):
        """
        타임아웃 후 프로바이더 복구 테스트.

        GIVEN: GLM 프로바이더가 실패 상태
        WHEN: 복구 타임아웃(300초) 경과
        THEN: should_use_fallback()가 False 반환
        """
        # Arrange
        tracker = ProviderHealthTracker(
            failure_threshold=3,
            failure_timeout=300,
        )

        # 3회 실패 기록
        for _ in range(3):
            tracker.record_failure("glm")

        assert tracker.should_use_fallback("glm")

        # 복구 타임아웃 시뮬레이션 (last_failure_time 조작)
        import time

        tracker.last_failure_time["glm"] = time.time() - 400  # 400초 전

        # Assert - 복구됨
        assert not tracker.should_use_fallback("glm")


class TestRetryIntegration:
    """재시도 통합 테스트."""

    @pytest.mark.asyncio
    @patch("gpt_bitcoin.infrastructure.external.retry_handler.asyncio.sleep")
    async def test_retry_with_exponential_backoff(self, mock_sleep: AsyncMock):
        """
        지수 백오프 재시도 통합 테스트.

        GIVEN: API 호출이 처음 두 번 실패하고 세 번째에 성공
        WHEN: call_with_retry() 호출
        THEN: 지수 백오프로 재시도 후 성공
        """
        # Arrange
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"decision": "buy"}'

        # AsyncMock for async client
        mock_create = AsyncMock()
        mock_create.side_effect = [
            TimeoutError("Timeout"),
            TimeoutError("Timeout"),
            mock_response,
        ]
        mock_client.chat.completions.create = mock_create

        tracker = ProviderHealthTracker()

        # Act
        response = await call_with_retry(
            client=mock_client,
            messages=[{"role": "user", "content": "Test"}],
            model="glm-5",
            max_retries=5,
            initial_delay=1.0,
            tracker=tracker,
        )

        # Assert - 응답이 dict 형태로 반환됨
        assert isinstance(response, dict)
        assert mock_create.call_count == 3
        # 지수 백오프 확인: 1초, 2초
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    @patch("gpt_bitcoin.infrastructure.external.retry_handler.asyncio.sleep")
    async def test_max_retries_exceeded_integration(self, mock_sleep: AsyncMock):
        """
        최대 재시도 초과 통합 테스트.

        GIVEN: API 호출이 계속 실패
        WHEN: call_with_retry() 호출
        THEN: 최대 재시도 후 GLMAPIError 발생
        """
        # Arrange
        from gpt_bitcoin.infrastructure.exceptions import GLMAPIError

        mock_client = MagicMock()
        mock_create = AsyncMock()
        mock_create.side_effect = TimeoutError("Timeout")
        mock_client.chat.completions.create = mock_create

        tracker = ProviderHealthTracker()

        # Act & Assert
        with pytest.raises(GLMAPIError, match="API 호출 실패"):
            await call_with_retry(
                client=mock_client,
                messages=[{"role": "user", "content": "Test"}],
                model="glm-5",
                max_retries=3,
                initial_delay=1.0,
                tracker=tracker,
            )


class TestModelSelection:
    """모델 선택 통합 테스트."""

    @patch("gpt_bitcoin.infrastructure.external.ai_client_factory.os.environ.get")
    def test_glm_model_selection(self, mock_environ_get: Mock):
        """
        GLM 프로바이더 선택 시 모델 테스트.

        GIVEN: AI_PROVIDER가 "glm"으로 설정
        WHEN: get_default_model() 호출
        THEN: GLM-5 모델명 반환
        """

        # Arrange
        def mock_env_glm_provider(key: str, default: str | None = None) -> str | None:
            env_map = {
                "GLM_API_KEY": "test-glm-api-key",
                "AI_PROVIDER": "glm",
                "AI_TIMEOUT": "30",
            }
            return env_map.get(key, default)

        mock_environ_get.side_effect = mock_env_glm_provider

        # Act
        model = get_default_model()

        # Assert
        assert model == "glm-5"

    @patch("gpt_bitcoin.infrastructure.external.ai_client_factory.os.environ.get")
    def test_openai_model_selection(self, mock_environ_get: Mock):
        """
        OpenAI 프로바이더 선택 시 모델 테스트.

        GIVEN: AI_PROVIDER가 "openai"으로 설정
        WHEN: get_default_model() 호출
        THEN: GPT-4 모델명 반환
        """

        # Arrange
        def mock_env_openai_provider(key: str, default: str | None = None) -> str | None:
            env_map = {
                "OPENAI_API_KEY": "test-openai-api-key",
                "AI_PROVIDER": "openai",
                "AI_TIMEOUT": "30",
            }
            return env_map.get(key, default)

        mock_environ_get.side_effect = mock_env_openai_provider

        # Act
        model = get_default_model()

        # Assert
        assert model == "gpt-4-turbo"


class TestHealthCheckIntegration:
    """헬스 체크 통합 테스트."""

    def test_health_tracker_multiple_providers(self):
        """
        다중 프로바이더 헬스 추적 테스트.

        GIVEN: ProviderHealthTracker가 초기화됨
        WHEN: 여러 프로바이더의 실패/성공 기록
        THEN: 각 프로바이더가 독립적으로 추적됨
        """
        # Arrange
        tracker = ProviderHealthTracker(
            failure_threshold=2,
            failure_timeout=300,
        )

        # Act - GLM 실패
        tracker.record_failure("glm")
        tracker.record_failure("glm")
        assert tracker.should_use_fallback("glm")

        # Act - OpenAI는 정상
        assert not tracker.should_use_fallback("openai")

        # Act - GLM 성공으로 복구
        tracker.record_success("glm")
        assert not tracker.should_use_fallback("glm")

    def test_health_tracker_failure_count_reset(self):
        """
        성공 시 실패 카운터 리셋 테스트.

        GIVEN: GLM 프로바이더가 2회 실패
        WHEN: 성공 기록
        THEN: 실패 카운터가 0으로 리셋
        """
        # Arrange
        tracker = ProviderHealthTracker()

        tracker.record_failure("glm")
        tracker.record_failure("glm")
        assert tracker.get_failure_count("glm") == 2

        # Act
        tracker.record_success("glm")

        # Assert
        assert tracker.get_failure_count("glm") == 0
