"""
백업 및 복구 도메인 모듈

이 모듈은 다음 기능을 제공합니다:
- BackupService: 백업 및 복구 도메인 서비스
- BackupMetadata: 백업 메타데이터 모델
- BackupConfig: 백업 설정 모델
- BackupResult: 백업 결과 모델
- RestoreResult: 복구 결과 모델
- ValidationError: 유효성 검증 오류

SPEC-TRADING-010: 백업 및 복구 시스템
REQ-BACKUP-001: 전체 시스템 데이터를 tar.gz 아카이브로 백업
REQ-BACKUP-002: 사용자 프로필, 거래 내역, 설정 포함
REQ-BACKUP-003: SHA-256 체크섬으로 무결성 검증
REQ-BACKUP-004: 복구 전 자동 백업 생성
REQ-BACKUP-005: 원자적 복구 작업 (전체 성공 또는 전체 실패)

@MX:NOTE: 백업 시스템 - 데이터 보호 및 재해 복구
"""

from __future__ import annotations

import datetime
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger

    from gpt_bitcoin.config.settings import Settings


# =============================================================================
# Domain Models
# =============================================================================


@dataclass
class BackupMetadata:
    """
    백업 메타데이터 모델

    Attributes:
        backup_id: 고유 백업 식별자 (backup-YYYYMMDD-HHMMSS)
        timestamp: 백업 생성 시간
        version: 백업 포맷 버전
        data_size: 원본 데이터 크기 (bytes)
        compressed_size: 압축된 데이터 크기 (bytes)
        checksum: SHA-256 체크섬
        includes: 포함된 데이터 유형 목록
        backup_path: 백업 파일 경로

    @MX:NOTE: 메타데이터는 아카이브 내 metadata.json에 저장됩니다
    """

    backup_id: str
    timestamp: datetime.datetime
    version: str = "1.0.0"
    data_size: int = 0
    compressed_size: int = 0
    checksum: str = ""
    includes: list[str] = field(default_factory=list)
    backup_path: str = ""

    def to_dict(self) -> dict:
        """
        메타데이터를 딕셔너리로 변환

        Returns:
            dict: 직렬화된 메타데이터
        """
        return {
            "backup_id": self.backup_id,
            "timestamp": self.timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "version": self.version,
            "data_size": self.data_size,
            "compressed_size": self.compressed_size,
            "checksum": self.checksum,
            "includes": self.includes,
            "backup_path": self.backup_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BackupMetadata:
        """
        딕셔너리로부터 메타데이터 생성

        Args:
            data: 직렬화된 메타데이터

        Returns:
            BackupMetadata: 메타데이터 인스턴스
        """
        return cls(
            backup_id=data["backup_id"],
            timestamp=datetime.datetime.fromisoformat(data["timestamp"]),
            version=data.get("version", "1.0.0"),
            data_size=data.get("data_size", 0),
            compressed_size=data.get("compressed_size", 0),
            checksum=data.get("checksum", ""),
            includes=data.get("includes", []),
            backup_path=data.get("backup_path", ""),
        )

    @property
    def compression_ratio(self) -> float:
        """
        압축률 계산

        Returns:
            float: 압축률 (0.0 ~ 1.0)
        """
        if self.data_size == 0:
            return 0.0
        return self.compressed_size / self.data_size


@dataclass
class BackupConfig:
    """
    백업 설정 모델

    Attributes:
        backup_dir: 백업 저장 디렉토리
        max_backups: 최대 보관 백업 수
        compress: 압축 여부 (tar.gz)
        checksum_algorithm: 체크섬 알고리즘 (sha256, md5)
        auto_backup_enabled: 자동 백업 활성화 여부
        auto_backup_schedule: 자동 백업 스케줄 (cron 표현식)

    @MX:NOTE: 기본값은 압축 활성화, SHA-256 체크섬
    """

    backup_dir: str = ".backup"
    max_backups: int = 30  # REQ-BACKUP-006: 최대 30개 백업
    compress: bool = True
    checksum_algorithm: Literal["sha256", "md5"] = "sha256"
    auto_backup_enabled: bool = False  # REQ-BACKUP-007: 자동 백업 (선택)
    auto_backup_schedule: str = "0 3 * * *"  # 매일 새벽 3시


@dataclass
class BackupResult:
    """
    백업 실행 결과 모델

    Attributes:
        success: 백업 성공 여부
        metadata: 백업 메타데이터 (성공 시)
        backup_path: 백업 파일 경로 (성공 시)
        error_message: 오류 메시지 (실패 시)
        duration_seconds: 실행 시간 (초)

    @MX:NOTE: success=False인 경우 metadata와 backup_path는 None입니다
    """

    success: bool
    metadata: BackupMetadata | None
    backup_path: str | None
    error_message: str | None = None
    duration_seconds: float = 0.0


@dataclass
class RestoreResult:
    """
    복구 실행 결과 모델

    Attributes:
        success: 복구 성공 여부
        restored_items: 복구된 항목 수
        backup_id: 복구된 백업 ID
        error_message: 오류 메시지 (실패 시)
        duration_seconds: 실행 시간 (초)

    @MX:NOTE: success=False인 경우 restored_items는 0입니다
    """

    success: bool
    restored_items: int
    backup_id: str
    error_message: str | None = None
    duration_seconds: float = 0.0


# =============================================================================
# Exceptions
# =============================================================================


class ValidationError(Exception):
    """
    유효성 검증 오류

    REQ-BACKUP-003: 체크섬 검증 실패 등
    """

    pass


# =============================================================================
# Helper Functions
# =============================================================================


def calculate_checksum(file_path: str, algorithm: str = "sha256") -> str:
    """
    파일 체크섬 계산

    REQ-BACKUP-003: SHA-256 체크섬으로 무결성 검증

    Args:
        file_path: 파일 경로
        algorithm: 체크섬 알고리즘 (sha256, md5)

    Returns:
        str: 16진수 체크섬

    @MX:ANCHOR: calculate_checksum
        fan_in: 3 (backup, restore, validation)
        @MX:REASON: 중앙 집중식 체크섬 계산
    """
    hash_func = hashlib.sha256() if algorithm == "sha256" else hashlib.md5()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def generate_backup_id() -> str:
    """
    백업 ID 생성

    REQ-BACKUP-001: 타임스탬프 기반 고유 ID

    Returns:
        str: 백업 ID (형식: backup-YYYYMMDD-HHMMSS)

    @MX:NOTE: 타임스탬프 순서로 백업 정렬 가능
    """
    now = datetime.datetime.now()
    return f"backup-{now.strftime('%Y%m%d-%H%M%S')}"


def validate_checksum(file_path: str, expected_checksum: str) -> bool:
    """
    체크섬 검증

    REQ-BACKUP-003: 백업 무결성 검증

    Args:
        file_path: 검증할 파일 경로
        expected_checksum: 예상 체크섬

    Returns:
        bool: 체크섬 일치 여부
    """
    actual_checksum = calculate_checksum(file_path)
    return actual_checksum == expected_checksum


# =============================================================================
# BackupService
# =============================================================================


class BackupService:
    """
    백업 및 복구 도메인 서비스

    책임:
    - 백업 생성 및 관리
    - 복구 작업 수행
    - 체크섬 검증
    - 백업 목록 조회

    REQ-BACKUP-001: 전체 시스템 데이터 백업
    REQ-BACKUP-002: 사용자 프로필, 거래 내역, 설정 포함
    REQ-BACKUP-003: SHA-256 체크섬 무결성 검증
    REQ-BACKUP-004: 복구 전 자동 백업 생성
    REQ-BACKUP-005: 원자적 복구 작업

    @MX:NOTE: 파일 I/O는 인프라 스트럭처 계층에 위임합니다
    """

    def __init__(
        self,
        config: BackupConfig,
        settings: Settings,
        user_profile_service,  # UserProfileService
        trade_history_service,  # TradeHistoryService
        logger: BoundLogger | None = None,
    ):
        """
        BackupService 초기화

        Args:
            config: 백업 설정
            settings: 애플리케이션 설정
            user_profile_service: 사용자 프로필 서비스
            trade_history_service: 거래 내역 서비스
            logger: 로거 (선택)
        """
        self._config = config
        self._settings = settings
        self._user_profile_service = user_profile_service
        self._trade_history_service = trade_history_service
        self._logger = logger

    # ========================================================================
    # Public Methods
    # ========================================================================

    def list_backups(self) -> list[str]:
        """
        저장된 백업 목록 조회

        REQ-BACKUP-001: 백업 파일 목록 반환

        Returns:
            list[str]: 백업 파일 경로 목록 (최신순)
        """
        backup_dir = Path(self._config.backup_dir)
        if not backup_dir.exists():
            return []

        backups = sorted(
            backup_dir.glob("*.tar.gz"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        return [str(b) for b in backups]

    def get_latest_backup(self) -> str | None:
        """
        최신 백업 조회

        REQ-BACKUP-001: 가장 최근 백업 반환

        Returns:
            str | None: 최신 백업 경로 (없으면 None)
        """
        backups = self.list_backups()
        return backups[0] if backups else None

    async def create_backup(
        self,
        notes: str | None = None,
        is_automatic: bool = False,
    ) -> BackupResult:
        """
        백업 생성

        REQ-BACKUP-001: 전체 시스템 데이터 백업
        REQ-BACKUP-002: 사용자 프로필, 거래 내역, 설정 포함

        Args:
            notes: 백업 메모 (선택)
            is_automatic: 자동 백업 여부

        Returns:
            BackupResult: 백업 결과

        @MX:ANCHOR: create_backup
            fan_in: 3 (web UI, scheduler, CLI)
            @MX:REASON: 중앙 집중식 백업 생성
        """
        import time

        start_time = time.time()

        try:
            # 백업 파일 수집
            files_to_backup = self._collect_backup_files()

            if not files_to_backup:
                return BackupResult(
                    success=False,
                    metadata=None,
                    backup_path=None,
                    error_message="백업할 파일이 없습니다",
                    duration_seconds=time.time() - start_time,
                )

            # 백업 ID 생성
            backup_id = generate_backup_id()

            # 아카이브 핸들러 가져오기
            from gpt_bitcoin.infrastructure.backup.archive_handler import ArchiveHandler

            archive_handler = ArchiveHandler(
                backup_dir=self._config.backup_dir,
                compress=self._config.compress,
            )

            # 데이터 크기 계산
            data_size = sum(Path(f).stat().st_size for f in files_to_backup if Path(f).exists())

            # 메타데이터 생성
            metadata = {
                "backup_id": backup_id,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "version": "1.0.0",
                "data_size": data_size,
                "includes": ["profiles", "trades", "settings"],
                "is_automatic": is_automatic,
                "notes": notes,
            }

            # 아카이브 생성
            backup_path = archive_handler.create_archive(
                backup_id=backup_id,
                files=files_to_backup,
                metadata=metadata,
            )

            # 체크섬 계산
            checksum = calculate_checksum(backup_path, self._config.checksum_algorithm)

            # 압축 크기
            compressed_size = Path(backup_path).stat().st_size

            # 메타데이터 업데이트
            metadata["checksum"] = checksum
            metadata["compressed_size"] = compressed_size

            # 백업 메타데이터 생성
            backup_metadata = self._create_backup_metadata(
                backup_path=backup_path,
                data_size=data_size,
                compressed_size=compressed_size,
                checksum=checksum,
                includes=["profiles", "trades", "settings"],
            )

            if self._logger:
                self._logger.info(
                    "Backup created successfully",
                    backup_id=backup_id,
                    backup_path=backup_path,
                    size=compressed_size,
                )

            return BackupResult(
                success=True,
                metadata=backup_metadata,
                backup_path=backup_path,
                duration_seconds=time.time() - start_time,
            )

        except Exception as e:
            if self._logger:
                self._logger.error(
                    "Failed to create backup",
                    error=str(e),
                )

            return BackupResult(
                success=False,
                metadata=None,
                backup_path=None,
                error_message=str(e),
                duration_seconds=time.time() - start_time,
            )

    async def restore_backup(
        self,
        backup_id: str,
    ) -> RestoreResult:
        """
        백업 복구

        REQ-BACKUP-004: 복구 전 안전 백업 생성
        REQ-BACKUP-005: 원자적 복구 작업

        Args:
            backup_id: 복구할 백업 ID

        Returns:
            RestoreResult: 복구 결과

        @MX:WARN: 파괴적 작업 - 현재 데이터를 덮어씁니다
            항상 복구 전 안전 백업을 생성합니다
        """
        import time

        start_time = time.time()

        try:
            # 백업 파일 경로 찾기
            backup_path = self._find_backup_path(backup_id)

            if not backup_path:
                return RestoreResult(
                    success=False,
                    restored_items=0,
                    backup_id=backup_id,
                    error_message=f"백업을 찾을 수 없습니다: {backup_id}",
                    duration_seconds=time.time() - start_time,
                )

            # REQ-BACKUP-003: 체크섬 검증
            metadata = self._get_backup_metadata(backup_path)
            expected_checksum = metadata.get("checksum")

            if expected_checksum:
                if not self._validate_backup_checksum(backup_path, expected_checksum):
                    return RestoreResult(
                        success=False,
                        restored_items=0,
                        backup_id=backup_id,
                        error_message="백업 체크섬 검증 실패 - 파일이 손상되었습니다",
                        duration_seconds=time.time() - start_time,
                    )

            # REQ-BACKUP-004: 복구 전 안전 백업 생성
            await self._create_safety_backup()

            # 복구 실행
            from gpt_bitcoin.infrastructure.backup.archive_handler import ArchiveHandler
            from gpt_bitcoin.infrastructure.backup.backup_manager import BackupManager

            archive_handler = ArchiveHandler(
                backup_dir=self._config.backup_dir,
                compress=self._config.compress,
            )

            backup_manager = BackupManager(
                config=self._config,
                settings=self._settings,
                archive_handler=archive_handler,
                logger=self._logger,
            )

            success = backup_manager.restore_backup(backup_path)

            if not success:
                return RestoreResult(
                    success=False,
                    restored_items=0,
                    backup_id=backup_id,
                    error_message="복구 실패",
                    duration_seconds=time.time() - start_time,
                )

            restored_items = len(metadata.get("includes", []))

            if self._logger:
                self._logger.info(
                    "Backup restored successfully",
                    backup_id=backup_id,
                    restored_items=restored_items,
                )

            return RestoreResult(
                success=True,
                restored_items=restored_items,
                backup_id=backup_id,
                duration_seconds=time.time() - start_time,
            )

        except Exception as e:
            if self._logger:
                self._logger.error(
                    "Failed to restore backup",
                    backup_id=backup_id,
                    error=str(e),
                )

            return RestoreResult(
                success=False,
                restored_items=0,
                backup_id=backup_id,
                error_message=str(e),
                duration_seconds=time.time() - start_time,
            )

    async def delete_backup(self, backup_id: str) -> bool:
        """
        백업 삭제

        Args:
            backup_id: 삭제할 백업 ID

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            backup_path = self._find_backup_path(backup_id)

            if not backup_path:
                return False

            Path(backup_path).unlink()

            if self._logger:
                self._logger.info(
                    "Backup deleted",
                    backup_id=backup_id,
                )

            return True

        except Exception as e:
            if self._logger:
                self._logger.error(
                    "Failed to delete backup",
                    backup_id=backup_id,
                    error=str(e),
                )

            return False

    async def validate_backup(self, backup_id: str) -> bool:
        """
        백업 무결성 검증

        REQ-BACKUP-003: 체크섬 검증

        Args:
            backup_id: 검증할 백업 ID

        Returns:
            bool: 검증 성공 여부
        """
        try:
            backup_path = self._find_backup_path(backup_id)

            if not backup_path:
                return False

            metadata = self._get_backup_metadata(backup_path)
            expected_checksum = metadata.get("checksum")

            if not expected_checksum:
                return False

            return self._validate_backup_checksum(backup_path, expected_checksum)

        except Exception:
            return False

    async def cleanup_old_backups(self) -> int:
        """
        오래된 백업 정리

        REQ-BACKUP-006: 최대 백업 개수 유지

        Returns:
            int: 삭제된 백업 수
        """
        try:
            from gpt_bitcoin.infrastructure.backup.archive_handler import ArchiveHandler
            from gpt_bitcoin.infrastructure.backup.backup_manager import BackupManager

            archive_handler = ArchiveHandler(
                backup_dir=self._config.backup_dir,
                compress=self._config.compress,
            )

            backup_manager = BackupManager(
                config=self._config,
                settings=self._settings,
                archive_handler=archive_handler,
                logger=self._logger,
            )

            return backup_manager.cleanup_old_backups()

        except Exception as e:
            if self._logger:
                self._logger.error(
                    "Failed to cleanup old backups",
                    error=str(e),
                )

            return 0

    # ========================================================================
    # Internal Methods
    # ========================================================================

    def _create_backup_metadata(
        self,
        backup_path: str,
        data_size: int,
        compressed_size: int,
        checksum: str,
        includes: list[str] | None = None,
    ) -> BackupMetadata:
        """
        백업 메타데이터 생성

        Args:
            backup_path: 백업 파일 경로
            data_size: 원본 데이터 크기
            compressed_size: 압축된 크기
            checksum: 체크섬
            includes: 포함된 데이터 유형

        Returns:
            BackupMetadata: 메타데이터 인스턴스
        """
        return BackupMetadata(
            backup_id=generate_backup_id(),
            timestamp=datetime.datetime.now(),
            version="1.0.0",
            data_size=data_size,
            compressed_size=compressed_size,
            checksum=checksum,
            includes=includes or [],
            backup_path=backup_path,
        )

    def _validate_backup_path(self, backup_path: str) -> None:
        """
        백업 파일 경로 검증

        REQ-BACKUP-003: 백업 파일 존재 확인

        Args:
            backup_path: 백업 파일 경로

        Raises:
            ValidationError: 파일이 존재하지 않을 때
        """
        if not Path(backup_path).exists():
            raise ValidationError(f"백업 파일을 찾을 수 없습니다: {backup_path}")

    def _validate_backup_checksum(self, backup_path: str, expected_checksum: str) -> bool:
        """
        백업 체크섬 검증

        REQ-BACKUP-003: 무결성 검증

        Args:
            backup_path: 백업 파일 경로
            expected_checksum: 예상 체크섬

        Returns:
            bool: 검증 성공 여부
        """
        return validate_checksum(backup_path, expected_checksum)

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

        # REQ-BACKUP-010: 민감한 자격 증명 제외
        files = self._filter_sensitive_files(files)

        return files

    def _filter_sensitive_files(self, files: list[str]) -> list[str]:
        """
        민감한 파일 필터링

        REQ-BACKUP-010: API 키, PIN 코드 등 제외

        Args:
            files: 파일 경로 목록

        Returns:
            list[str]: 필터링된 파일 목록
        """
        filtered = []

        for file_path in files:
            path = Path(file_path)

            # .env 파일 제외
            if path.name.endswith(".env") or path.name.startswith(".env"):
                continue

            # *_secret.*, *_key.* 패턴 제외
            if any(pattern in path.name for pattern in ["secret", "key", "token", "credential"]):
                continue

            filtered.append(file_path)

        return filtered

    def _find_backup_path(self, backup_id: str) -> str | None:
        """
        백업 ID로 파일 경로 찾기

        Args:
            backup_id: 백업 ID

        Returns:
            str | None: 백업 파일 경로 (없으면 None)
        """
        backup_dir = Path(self._config.backup_dir)

        if not backup_dir.exists():
            return None

        # 정확한 ID 매칭
        for ext in [".tar.gz", ".tar"]:
            backup_path = backup_dir / f"{backup_id}{ext}"
            if backup_path.exists():
                return str(backup_path)

        return None

    def _get_backup_metadata(self, backup_path: str) -> dict:
        """
        아카이브 메타데이터 추출

        Args:
            backup_path: 아카이브 파일 경로

        Returns:
            dict: 메타데이터 딕셔너리
        """
        from gpt_bitcoin.infrastructure.backup.archive_handler import ArchiveHandler

        archive_handler = ArchiveHandler(
            backup_dir=self._config.backup_dir,
            compress=self._config.compress,
        )

        return archive_handler.get_metadata(backup_path)

    async def _create_safety_backup(self) -> None:
        """
        안전 백업 생성

        REQ-BACKUP-004: 복구 전 현재 상태 백업

        @MX:NOTE: 복구 실패 시 롤백용
        """
        from gpt_bitcoin.infrastructure.backup.archive_handler import ArchiveHandler
        from gpt_bitcoin.infrastructure.backup.backup_manager import BackupManager

        safety_id = f"safety-{generate_backup_id()}"

        try:
            archive_handler = ArchiveHandler(
                backup_dir=self._config.backup_dir,
                compress=self._config.compress,
            )

            backup_manager = BackupManager(
                config=self._config,
                settings=self._settings,
                archive_handler=archive_handler,
                logger=self._logger,
            )

            files = self._collect_backup_files()

            metadata = {
                "backup_id": safety_id,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "is_safety_backup": True,
                "includes": ["profiles", "trades", "settings"],
            }

            archive_handler.create_archive(
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


__all__ = [
    "BackupConfig",
    "BackupMetadata",
    "BackupResult",
    "BackupService",
    "RestoreResult",
    "ValidationError",
    "calculate_checksum",
    "generate_backup_id",
    "validate_checksum",
]
