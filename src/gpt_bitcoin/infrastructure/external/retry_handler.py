"""
재시도 핸들러 모듈.

지수 백오프와 프로바이더 전환을 포함한 재시도 로직을 제공합니다.
듀얼 프로바이더 환경에서의 자동 장애 조치를 지원합니다.

Features:
- 지수 백오프(exponential backoff)를 적용한 재시도
- 연속 실패 시 프로바이더 자동 전환
- 프로바이더 건강 상태 추적
- 타임아웃 및 Rate Limit 처리
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from gpt_bitcoin.infrastructure.exceptions import GLMAPIError, RateLimitError
from gpt_bitcoin.infrastructure.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Provider Health Tracker
# =============================================================================


@dataclass
class ProviderHealthTracker:
    """
    프로바이더 건강 상태 추적기.

    연속 실패 횟수를 추적하고, 일정 횟수 이상 실패 시
    폴백 프로바이더 사용을 권장합니다.

    # @MX:NOTE: 연속 실패 기반 프로바이더 전환 로직
    # - 실패 임계값: 3회 (failure_threshold)
    # - 복구 타임아웃: 300초 (failure_timeout)
    # - 복구 후 자동 리셋

    Attributes:
        failure_count: 프로바이더별 연속 실패 횟수
        last_failure_time: 마지막 실패 시간
        failure_threshold: 폴백 전환 임계값 (기본값: 3회)
        failure_timeout: 복구 타임아웃 (초, 기본값: 300초 = 5분)

    Examples:
        >>> tracker = ProviderHealthTracker()
        >>> tracker.record_failure("glm")
        >>> tracker.should_use_fallback("glm")
        False
        >>> for _ in range(3):
        ...     tracker.record_failure("glm")
        >>> tracker.should_use_fallback("glm")
        True
    """

    failure_count: dict[str, int] = field(default_factory=dict)
    last_failure_time: dict[str, float] = field(default_factory=dict)
    failure_threshold: int = 3
    failure_timeout: float = 300.0  # 5 minutes

    def record_failure(self, provider: str) -> None:
        """
        프로바이더 실패를 기록합니다.

        Args:
            provider: 프로바이더 이름 ("glm", "openai")
        """
        self.failure_count[provider] = self.failure_count.get(provider, 0) + 1
        self.last_failure_time[provider] = time.time()

        logger.warning(
            f"프로바이더 실패 기록: {provider}",
            extra={
                "provider": provider,
                "failure_count": self.failure_count[provider],
                "threshold": self.failure_threshold,
            },
        )

    def record_success(self, provider: str) -> None:
        """
        프로바이더 성공을 기록하고 실패 카운터를 리셋합니다.

        Args:
            provider: 프로바이더 이름
        """
        if provider in self.failure_count:
            del self.failure_count[provider]
        if provider in self.last_failure_time:
            del self.last_failure_time[provider]

        logger.info(f"프로바이더 성공, 실패 카운터 리셋: {provider}")

    def should_use_fallback(self, provider: str) -> bool:
        """
        폴백 프로바이더 사용 여부를 반환합니다.

        연속 실패가 임계값을 초과하고 복구 타임아웃이 지나지 않은 경우
        폴백 사용을 권장합니다.

        Args:
            provider: 프로바이더 이름

        Returns:
            폴백 사용 권장 시 True, 아니면 False
        """
        # 실패 기록이 없음
        if provider not in self.failure_count:
            return False

        # 임계값 미달
        if self.failure_count[provider] < self.failure_threshold:
            return False

        # 복구 타임아웃 확인
        last_failure = self.last_failure_time.get(provider, 0)
        if time.time() - last_failure > self.failure_timeout:
            # 타임아웃 경과: 실패 카운터 리셋
            del self.failure_count[provider]
            del self.last_failure_time[provider]
            logger.info(f"프로바이더 복구 타임아웃 경과, 정상 상태로 복귀: {provider}")
            return False

        # 폴백 사용 권장
        logger.warning(
            f"프로바이더 연속 실패 임계값 도달, 폴백 사용 권장: {provider}",
            extra={
                "provider": provider,
                "failure_count": self.failure_count[provider],
                "threshold": self.failure_threshold,
            },
        )
        return True

    def get_failure_count(self, provider: str) -> int:
        """
        프로바이더의 현재 연속 실패 횟수를 반환합니다.

        Args:
            provider: 프로바이더 이름

        Returns:
            연속 실패 횟수
        """
        return self.failure_count.get(provider, 0)


# =============================================================================
# Retry Handler
# =============================================================================


async def call_with_retry(
    client: Any,
    messages: list[dict[str, Any]],
    model: str,
    max_retries: int = 5,
    initial_delay: float = 1.0,
    temperature: float = 0.7,
    tracker: ProviderHealthTracker | None = None,
) -> dict[str, Any]:
    """
    지수 백오프를 적용한 API 호출.

    # @MX:ANCHOR: 듀얼 프로바이더 재시도 진입점
    # - fan_in: GLMClient, OpenAI 클라이언트
    # - 지수 백오프: initial_delay * (2 ** attempt)
    # - 프로바이더 상태 추적: tracker.record_failure/success

    타임아웃, Rate Limit, 네트워크 오류 시 자동으로 재시도합니다.
    지수 백오프(algorithm): delay * (2 ** attempt)를 사용합니다.

    Args:
        client: AI 클라이언트 인스턴스
        messages: 메시지 리스트 (OpenAI 호환 형식)
        model: 모델명
        max_retries: 최대 재시도 횟수 (기본값: 5)
        initial_delay: 초기 지연 시간 (초, 기본값: 1.0)
        temperature: 샘플링 온도 (기본값: 0.7)
        tracker: 프로바이더 건강 상태 추적기 (선택사항)

    Returns:
        dict: API 응답 딕셔너리
            - content (str): 응답 내용
            - usage (dict): 토큰 사용량
            - model (str): 사용된 모델
            - retry_count (int): 재시도 횟수

    Raises:
        GLMAPIError: 모든 재시도 실패 시

    Examples:
        >>> response = await call_with_retry(
        ...     client=glm_client,
        ...     messages=[{"role": "user", "content": "Hello"}],
        ...     model="glm-5",
        ...     max_retries=3,
        ... )
        >>> print(response["content"])

    Retry Logic:
        - TimeoutError: 네트워크 타임아웃
        - RateLimitError: API Rate Limit 초과 (429)
        - ConnectionError: 연결 실패
        - asyncio.TimeoutError: 비동기 타임아웃

    Exponential Backoff:
        - 시도 1: initial_delay * 2^0 = 1.0초
        - 시도 2: initial_delay * 2^1 = 2.0초
        - 시도 3: initial_delay * 2^2 = 4.0초
        - 시도 4: initial_delay * 2^3 = 8.0초
        - 최대 대기: initial_delay * 2^(max_retries-1)
    """
    last_error: TimeoutError | ConnectionError | RateLimitError | None = None
    retry_count = 0

    for attempt in range(max_retries):
        try:
            # API 호출 (동기/비동기 자동 지원)
            if asyncio.iscoroutinefunction(client.chat.completions.create):
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                )
            else:
                response = await _call_api_async(client, messages, model, temperature)

            # 성공 시 추적기 업데이트
            if tracker:
                tracker.record_success(model)

            # 응답 반환
            return {
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                "model": model,
                "retry_count": retry_count,
            }

        except (TimeoutError, ConnectionError) as e:
            last_error = e
            retry_count += 1

            logger.warning(
                f"API 호출 실패 (시도 {attempt + 1}/{max_retries}): {type(e).__name__}",
                extra={
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "error": str(e),
                    "model": model,
                },
            )

            # 실패 추적
            if tracker:
                tracker.record_failure(model)

            # 마지막 시도가 아니면 대기
            if attempt < max_retries - 1:
                # 지수 백오프 계산
                delay = initial_delay * (2**attempt)
                logger.info(f"지수 백오프 대기: {delay:.2f}초")
                await asyncio.sleep(delay)

        except RateLimitError as e:
            last_error = e
            retry_count += 1

            logger.warning(
                f"Rate Limit 초과 (시도 {attempt + 1}/{max_retries})",
                extra={
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "retry_after": getattr(e, "retry_after", None),
                },
            )

            # 실패 추적
            if tracker:
                tracker.record_failure(model)

            # Rate Limit: retry_after 만큼 대기 또는 기본 백오프
            if attempt < max_retries - 1:
                if hasattr(e, "retry_after") and e.retry_after:
                    delay = e.retry_after
                else:
                    delay = initial_delay * (2**attempt)

                logger.info(f"Rate Limit 대기: {delay:.2f}초")
                await asyncio.sleep(delay)

    # 모든 재시도 실패
    error_message = (
        f"API 호출 실패 (최대 {max_retries}회 재시도): {type(last_error).__name__}: {last_error}"
    )
    logger.error(error_message)
    raise GLMAPIError(error_message, model=model) from last_error


async def _call_api_async(
    client: Any,
    messages: list[dict[str, Any]],
    model: str,
    temperature: float,
) -> Any:
    """
    비동기 API 호출 헬퍼 함수.

    Args:
        client: AI 클라이언트
        messages: 메시지 리스트
        model: 모델명
        temperature: 샘플링 온도

    Returns:
        API 응답 객체
    """
    # OpenAI/ZhipuAI 클라이언트는 동기 메서드를 제공
    # asyncio.to_thread()를 사용하여 스레드 풀에서 실행
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        ),
    )
    return response
