"""
백업 스케줄러 모듈

자동 백업 스케줄링 (cron 방식)

REQ-BACKUP-006: 자동 백업 스케줄러

@MX:NOTE: cron 표현식으로 유연한 스케줄링
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from structlog.stdlib import BoundLogger

if TYPE_CHECKING:
    from gpt_bitcoin.infrastructure.backup.backup_manager import BackupManager


# =============================================================================
# BackupScheduler
# =============================================================================


class BackupScheduler:
    """
    백업 스케줄러

    cron 표현식을 사용한 자동 백업 스케줄링

    REQ-BACKUP-006: cron 방식 자동 백업

    예시 cron 표현식:
        - "0 2 * * *" : 매일 새벽 2시
        - "0 */6 * * *" : 6시간마다
        - "0 0 * * 0" : 매주 일요일 자정

    @MX:NOTE: 실제 스케줄 실행은 외부 스케줄러(cron, Celery 등)에 의해 트리거됩니다
    """

    def __init__(
        self,
        config,  # BackupConfig
        backup_manager: BackupManager,
        logger: BoundLogger | None = None,
    ):
        """
        BackupScheduler 초기화

        Args:
            config: 백업 설정 (auto_backup_schedule 포함)
            backup_manager: 백업 관리자
            logger: 로거 (선택)
        """
        self._config = config
        self._backup_manager = backup_manager
        self._logger = logger

        # cron 표현식 파싱
        self._schedule = self._parse_schedule(config.auto_backup_schedule)

    # ========================================================================
    # Public Methods
    # ========================================================================

    def is_enabled(self) -> bool:
        """
        스케줄러 활성화 여부

        Returns:
            bool: 활성화 여부
        """
        return getattr(self._config, "auto_backup_enabled", False)

    def should_run_now(self) -> bool:
        """
        현재 시점에 백업을 실행해야 할지 확인

        cron 표현식과 현재 시간을 비교

        Returns:
            bool: 실행 여부
        """
        if not self.is_enabled():
            return False

        # 현재 시간의 cron 해시 계산
        import datetime

        now = datetime.datetime.now()

        # 분 단위 정확도로 체크
        current_key = f"{now.hour}:{now.min}"

        # 스케줄에 정의된 시간과 일치하는지 확인
        return self._schedule.get(current_key, False)

    def execute_scheduled_backup(self) -> bool:
        """
        예약된 백업 실행

        Returns:
            bool: 실행 성공 여부
        """
        if not self.should_run_now():
            return False

        try:
            # 백업 실행
            files = self._backup_manager._collect_backup_files()

            from gpt_bitcoin.domain.backup import generate_backup_id

            backup_id = generate_backup_id()

            metadata = {
                "backup_id": backup_id,
                "timestamp": datetime.datetime.now().isoformat(),
                "is_scheduled": True,
                "includes": ["profiles", "trades", "settings"],
            }

            self._backup_manager._archive_handler.create_archive(
                backup_id=backup_id,
                files=files,
                metadata=metadata,
            )

            # 오래된 백업 정리
            self._backup_manager.cleanup_old_backups()

            if self._logger:
                self._logger.info(
                    "Scheduled backup completed",
                    backup_id=backup_id,
                )

            return True

        except Exception as e:
            if self._logger:
                self._logger.error(
                    "Scheduled backup failed",
                    error=str(e),
                )
            return False

    # ========================================================================
    # Private Methods
    # ========================================================================

    def _parse_schedule(self, cron_expression: str) -> dict[str, bool]:
        """
        cron 표현식 파싱

        Args:
            cron_expression: cron 표현식 (분 시 일 월 요일)

        Returns:
            dict: 시간 키와 실행 여부 매핑
        """
        # 간단한 구현: 매일 특정 시간 실행
        # 예: "0 2 * * *" -> {"2:0": True}

        parts = cron_expression.split()
        if len(parts) != 5:
            return {}

        minute = parts[0]
        hour = parts[1]

        try:
            key = f"{hour}:{minute}"
            return {key: True}
        except (ValueError, IndexError):
            return {}


__all__ = [
    "BackupScheduler",
]
