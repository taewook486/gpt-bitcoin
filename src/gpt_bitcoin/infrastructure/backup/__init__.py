"""
백업 인프라 스트럭처 모듈

이 모듈은 다음 기능을 제공합니다:
- ArchiveHandler: tar.gz 아카이브 생성/추출
- BackupManager: 백업 파일 관리 및 정리
- Scheduler: 자동 백업 스케줄링

SPEC-TRADING-010: 백업 및 복구 시스템
REQ-BACKUP-006: 자동 백업 스케줄러 (cron 방식)
REQ-BACKUP-007: 백업 보관 정책 (최대 N개 유지)
REQ-BACKUP-008: 아카이브 핸들러 (tar.gz 생성/추출)
REQ-BACKUP-009: 복구 전 안전 백업 (pre-restore backup)

@MX:NOTE: 인프라 계층 - 파일 I/O 및 아카이빙 담당
"""

from gpt_bitcoin.infrastructure.backup.archive_handler import ArchiveHandler

__all__ = [
    "ArchiveHandler",
]
