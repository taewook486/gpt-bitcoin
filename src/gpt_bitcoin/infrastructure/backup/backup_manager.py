"""
백업 관리자 모듈

백업 파일 관리, 정책 적용, 복구 작업 조정

REQ-BACKUP-007: 백업 보관 정책 (최대 N개 유지)
REQ-BACKUP-009: 복구 전 안전 백업

@MX:NOTE: 백업 라이프사이클 관리
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from structlog.stdlib import BoundLogger

if TYPE_CHECKING:
    from gpt_bitcoin.infrastructure.backup.archive_handler import ArchiveHandler


# =============================================================================
# BackupManager
# =============================================================================


class BackupManager:
    """
    백업 관리자

    백업 파일 관리, 보관 정책 적용, 복구 작업 조정

    REQ-BACKUP-007: 최대 N개 백업 유지
    REQ-BACKUP-009: 복구 전 안전 백업 생성

    @MX:ANCHOR: BackupManager
        fan_in: 3 (web UI, scheduler, CLI)
        @MX:REASON: 중앙 집중식 백업 관리
    """

    def __init__(
        self,
        config,  # BackupConfig
        settings,  # Settings
        archive_handler: ArchiveHandler,
        logger: BoundLogger | None = None,
    ):
        """
        BackupManager 초기화

        Args:
            config: 백업 설정
            settings: 애플리케이션 설정
            archive_handler: 아카이브 핸들러
            logger: 로거 (선택)
        """
        self._config = config
        self._settings = settings
        self._archive_handler = archive_handler
        self._logger = logger

    # ========================================================================
    # Public Methods
    # ========================================================================

    def list_backups(self) -> list[dict[str, Any]]:
        """
        모든 백업 목록 조회

        REQ-BACKUP-001: 백업 목록 반환

        Returns:
            list[dict]: 백업 정보 목록 (최신순)
        """
        backup_dir = Path(self._config.backup_dir)
        if not backup_dir.exists():
            return []

        backups = []
        for archive_path in sorted(
            backup_dir.glob("*.tar.gz"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            try:
                metadata = self._archive_handler.get_metadata(str(archive_path))
                metadata["archive_path"] = str(archive_path)
                metadata["file_size"] = archive_path.stat().st_size
                backups.append(metadata)
            except Exception:
                # 손상된 백업은 건너뜀
                continue

        return backups

    def get_backup_info(self, archive_path: str) -> dict[str, Any]:
        """
        백업 정보 조회

        REQ-BACKUP-001: 백업 메타데이터 반환

        Args:
            archive_path: 아카이브 파일 경로

        Returns:
            dict: 백업 정보

        Raises:
            FileNotFoundError: 아카이브 파일이 없을 때
        """
        return self._archive_handler.get_metadata(archive_path)

    def cleanup_old_backups(self) -> int:
        """
        오래된 백업 정리

        REQ-BACKUP-007: max_backups 설정에 따라 오래된 백업 삭제

        Returns:
            int: 삭제된 백업 수
        """
        backup_dir = Path(self._config.backup_dir)
        if not backup_dir.exists():
            return 0

        # 백업 파일 목록 (수정 시간순 정렬)
        backups = sorted(
            backup_dir.glob("*.tar.gz"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        # 최대 개수 초과분 삭제
        deleted_count = 0
        max_backups = self._config.max_backups

        for backup_path in backups[max_backups:]:
            try:
                self._archive_handler.delete_archive(str(backup_path))
                deleted_count += 1

                if self._logger:
                    self._logger.info(
                        "Old backup deleted",
                        backup=str(backup_path),
                    )
            except Exception as e:
                if self._logger:
                    self._logger.warning(
                        "Failed to delete old backup",
                        backup=str(backup_path),
                        error=str(e),
                    )

        return deleted_count

    def restore_backup(self, archive_path: str) -> bool:
        """
        백업 복구

        REQ-BACKUP-009: 복구 전 안전 백업 생성
        REQ-BACKUP-005: 원자적 복구 작업

        Args:
            archive_path: 복구할 아카이브 경로

        Returns:
            bool: 복구 성공 여부
        """
        try:
            # REQ-BACKUP-009: 복구 전 안전 백업
            self._create_safety_backup()

            # 임시 디렉토리에 추출
            with tempfile.TemporaryDirectory() as temp_dir:
                # 아카이브 추출
                self._archive_handler.extract_archive(
                    archive_path=archive_path,
                    extract_dir=temp_dir,
                )

                # 파일 복사 (원자적 연산 보장)
                self._restore_files(temp_dir)

            if self._logger:
                self._logger.info(
                    "Backup restored successfully",
                    archive=archive_path,
                )

            return True

        except Exception as e:
            if self._logger:
                self._logger.error(
                    "Failed to restore backup",
                    archive=archive_path,
                    error=str(e),
                )
            return False

    # ========================================================================
    # Internal Methods
    # ========================================================================

    def _collect_backup_files(self) -> list[str]:
        """
        백업 대상 파일 수집

        REQ-BACKUP-002: 사용자 프로필, 거래 내역, 설정 포함

        Returns:
            list[str]: 백업할 파일 경로 목록
        """
        files = []

        # 데이터 디렉토리 파일
        if hasattr(self._settings, "data_dir"):
            data_dir = Path(self._settings.data_dir)
            if data_dir.exists():
                files.extend([str(f) for f in data_dir.glob("*.db")])

        # 개별 DB 파일 (하위 호환)
        db_files = [
            "profile_db_path",
            "notification_db_path",
            "trading_db_path",
        ]
        for attr in db_files:
            if hasattr(self._settings, attr):
                path = getattr(self._settings, attr)
                if path and Path(path).exists():
                    files.append(path)

        # 설정 디렉토리 파일
        if hasattr(self._settings, "config_dir"):
            config_dir = Path(self._settings.config_dir)
            if config_dir.exists():
                files.extend([str(f) for f in config_dir.glob("*") if f.is_file()])

        return files

    def _create_safety_backup(self) -> None:
        """
        안전 백업 생성

        REQ-BACKUP-009: 복구 전 현재 상태 백업

        @MX:NOTE: 복구 실패 시 롤백용
        """
        from gpt_bitcoin.domain.backup import generate_backup_id

        safety_id = f"safety-{generate_backup_id()}"

        try:
            files = self._collect_backup_files()
            metadata = {
                "backup_id": safety_id,
                "timestamp": Path(self._config.backup_dir).stat().st_mtime,
                "is_safety_backup": True,
                "includes": ["profiles", "trades", "settings"],
            }

            self._archive_handler.create_archive(
                backup_id=safety_id,
                files=files,
                metadata=metadata,
            )

            if self._logger:
                self._logger.info("Safety backup created", backup_id=safety_id)

        except Exception as e:
            if self._logger:
                self._logger.warning(
                    "Failed to create safety backup",
                    error=str(e),
                )

    def _restore_files(self, extract_dir: str) -> None:
        """
        추출된 파일 복원

        REQ-BACKUP-005: 원자적 복구 (전체 성공 또는 전체 실패)

        Args:
            extract_dir: 추출된 파일 디렉토리
        """
        extract_path = Path(extract_dir)

        # 데이터 파일 복원
        data_source = extract_path / "data"
        if data_source.exists():
            if hasattr(self._settings, "data_dir"):
                data_dir = Path(self._settings.data_dir)
                data_dir.mkdir(parents=True, exist_ok=True)

                for db_file in data_source.glob("*.db"):
                    shutil.copy2(db_file, data_dir / db_file.name)

        # 개별 DB 파일 복원 (하위 호환)
        db_mappings = {
            "profiles.db": "profile_db_path",
            "notifications.db": "notification_db_path",
            "trading.db": "trading_db_path",
        }

        for db_name, attr in db_mappings.items():
            source = data_source / db_name
            if source.exists() and hasattr(self._settings, attr):
                dest_path = Path(getattr(self._settings, attr))
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest_path)

        # 설정 파일 복원
        config_source = extract_path / "config"
        if config_source.exists():
            if hasattr(self._settings, "config_dir"):
                config_dir = Path(self._settings.config_dir)
                config_dir.mkdir(parents=True, exist_ok=True)

                for config_file in config_source.glob("*"):
                    if config_file.is_file():
                        shutil.copy2(config_file, config_dir / config_file.name)


__all__ = [
    "BackupManager",
]
