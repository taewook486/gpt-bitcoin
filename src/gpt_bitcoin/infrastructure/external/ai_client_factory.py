"""
AI 클라이언트 팩토리 모듈.

GLM-5와 OpenAI 간의 듀얼 프로바이더를 지원하는 팩토리 함수를 제공합니다.
환경 변수를 통해 프로바이더를 선택하고 자동 폴백을 지원합니다.

Environment Variables:
    GLM_API_KEY: ZhipuAI GLM API 키 (1차 프로바이더)
    GLM_API_BASE: GLM API 베이스 URL (기본값: https://api.z.ai/api/coding/paas/v4/)
    OPENAI_API_KEY: OpenAI API 키 (폴백 프로바이더)
    AI_PROVIDER: 프로바이더 선택 ("glm", "openai", "auto")
    AI_TIMEOUT: API 호출 타임아웃 (기본값: 30)

Usage:
    >>> from gpt_bitcoin.infrastructure.external.ai_client_factory import get_ai_client
    >>> client = get_ai_client()
    >>> response = client.chat.completions.create(
    ...     model="glm-5",
    ...     messages=[{"role": "user", "content": "Hello"}]
    ... )
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

from openai import OpenAI
from zhipuai import ZhipuAI

from gpt_bitcoin.infrastructure.logging import get_logger

logger = get_logger(__name__)


class AIProvider(str, Enum):
    """
    지원되는 AI 프로바이더 열거형.

    Attributes:
        GLM: ZhipuAI GLM 모델 (1차)
        OPENAI: OpenAI GPT 모델 (폴백)
        AUTO: 환경 변수에 따라 자동 선택
    """

    GLM = "glm"
    OPENAI = "openai"
    AUTO = "auto"


# 기본 설정값
DEFAULT_GLM_BASE_URL = "https://api.z.ai/api/coding/paas/v4/"
DEFAULT_TIMEOUT = 30
DEFAULT_GLM_MODEL = "glm-5"
DEFAULT_OPENAI_MODEL = "gpt-4-turbo"


def get_ai_client(
    provider: AIProvider = AIProvider.AUTO,
    timeout: int | None = None,
) -> Any:
    """
    듀얼 프로바이더를 지원하는 AI 클라이언트 팩토리.

    이 함수는 환경 변수 설정에 따라 적절한 AI 클라이언트를 반환합니다.
    GLM-5를 1차 프로바이더로 사용하며, GLM API 키가 없거나 실패할 경우
    OpenAI로 자동 폴백합니다.

    Args:
        provider: 사용할 프로바이더 (GLM, OPENAI, AUTO).
            기본값은 AUTO로 환경 변수에 따라 자동 선택됩니다.
        timeout: API 호출 타임아웃 (초). 기본값은 환경 변수 또는 30초.

    Returns:
        OpenAI 또는 ZhipuAI 클라이언트 인스턴스.
        두 클라이언트 모두 OpenAI 호환 인터페이스를 제공합니다.

    Raises:
        ValueError: GLM_API_KEY와 OPENAI_API_KEY가 모두 설정되지 않은 경우.

    Environment:
        GLM_API_KEY: GLM API 키 (필수, 1차 프로바이더)
        GLM_API_BASE: GLM API 베이스 URL (선택)
        OPENAI_API_KEY: OpenAI API 키 (폴백용)
        AI_PROVIDER: 강제 프로바이더 선택 ("glm", "openai", "auto")
        AI_TIMEOUT: 타임아웃 설정 (초)

    Examples:
        >>> # 기본 사용 (자동 선택)
        >>> client = get_ai_client()
        >>> response = client.chat.completions.create(
        ...     model="glm-5",
        ...     messages=[{"role": "user", "content": "분석해줘"}]
        ... )

        >>> # 특정 프로바이더 강제 선택
        >>> client = get_ai_client(provider=AIProvider.GLM)

        >>> # 타임아웃 설정
        >>> client = get_ai_client(timeout=60)
    """
    # 타임아웃 설정
    actual_timeout = timeout or int(os.environ.get("AI_TIMEOUT", DEFAULT_TIMEOUT))

    # 환경 변수에서 프로바이더 설정 확인
    env_provider = os.environ.get("AI_PROVIDER", "auto").lower()

    # 프로바이더 결정 (AUTO인 경우 환경 변수 사용)
    actual_provider = provider if provider != AIProvider.AUTO else AIProvider(env_provider)

    # API 키 확인
    glm_api_key = os.environ.get("GLM_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    logger.debug(
        "AI 클라이언트 초기화 시작",
        extra={
            "requested_provider": provider.value,
            "env_provider": env_provider,
            "actual_provider": actual_provider.value,
            "has_glm_key": glm_api_key is not None,
            "has_openai_key": openai_api_key is not None,
            "timeout": actual_timeout,
        },
    )

    # GLM 프로바이더 시도 (1차)
    if actual_provider in (AIProvider.GLM, AIProvider.AUTO):
        if glm_api_key:
            try:
                glm_base_url = os.environ.get("GLM_API_BASE", DEFAULT_GLM_BASE_URL)

                client = ZhipuAI(
                    api_key=glm_api_key,
                    base_url=glm_base_url,
                )

                logger.info(
                    "GLM 클라이언트 초기화 성공",
                    extra={
                        "provider": "glm",
                        "base_url": glm_base_url,
                        "model": DEFAULT_GLM_MODEL,
                    },
                )

                return client

            except Exception as e:
                logger.warning(
                    f"GLM 클라이언트 초기화 실패: {e}",
                    extra={"error": str(e)},
                )

                # AUTO 모드에서만 폴백, GLM 모드에서는 예외 발생
                if actual_provider == AIProvider.GLM:
                    raise ValueError(f"GLM 클라이언트 초기화 실패: {e}") from e

                logger.info("OpenAI로 폴백 시도")

    # OpenAI 프로바이더 시도 (폴백)
    if actual_provider in (AIProvider.OPENAI, AIProvider.AUTO):
        if openai_api_key:
            try:
                client = OpenAI(
                    api_key=openai_api_key,
                    timeout=actual_timeout,
                )

                logger.info(
                    "OpenAI 클라이언트 초기화 성공",
                    extra={
                        "provider": "openai",
                        "model": DEFAULT_OPENAI_MODEL,
                        "timeout": actual_timeout,
                    },
                )

                return client

            except Exception as e:
                logger.error(
                    f"OpenAI 클라이언트 초기화 실패: {e}",
                    extra={"error": str(e)},
                )

                if actual_provider == AIProvider.OPENAI:
                    raise ValueError(f"OpenAI 클라이언트 초기화 실패: {e}") from e

    # 사용 가능한 API 키가 없음
    error_message = (
        "API 키가 설정되지 않았습니다. GLM_API_KEY 또는 OPENAI_API_KEY 환경 변수를 설정하세요."
    )
    logger.error(error_message)
    raise ValueError(error_message)


def get_default_model(provider: AIProvider = AIProvider.AUTO) -> str:
    """
    프로바이더에 따른 기본 모델명 반환.

    Args:
        provider: AI 프로바이더

    Returns:
        기본 모델명 문자열
    """
    actual_provider = (
        provider
        if provider != AIProvider.AUTO
        else AIProvider(os.environ.get("AI_PROVIDER", "auto").lower())
    )

    if actual_provider == AIProvider.GLM:
        return DEFAULT_GLM_MODEL
    return DEFAULT_OPENAI_MODEL


def get_provider_info() -> dict[str, Any]:
    """
    현재 프로바이더 설정 정보 반환.

    Returns:
        프로바이더 설정 정보 딕셔너리
    """
    glm_api_key = os.environ.get("GLM_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    env_provider = os.environ.get("AI_PROVIDER", "auto").lower()

    return {
        "glm_available": glm_api_key is not None,
        "openai_available": openai_api_key is not None,
        "env_provider": env_provider,
        "default_glm_model": DEFAULT_GLM_MODEL,
        "default_openai_model": DEFAULT_OPENAI_MODEL,
        "default_timeout": int(os.environ.get("AI_TIMEOUT", DEFAULT_TIMEOUT)),
    }
