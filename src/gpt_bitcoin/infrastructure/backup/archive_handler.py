"""
아카이브 핸들러 모듈

tar.gz 아카이브 생성, 추출, 메타데이터 관리

REQ-BACKUP-008: tar.gz 아카이브 생성/추출

@MX:NOTE: 파일 시스템 작업 전담
"""

from __future__ import annotations

import json
import tarfile
from pathlib import Path
from typing import Any

from structlog.stdlib import BoundLogger

# =============================================================================
# ArchiveHandler
# =============================================================================


class ArchiveHandler:
    """
    아카이브 핸들러

    tar.gz 아카이브 생성, 추출, 메타데이터 관리

    REQ-BACKUP-008: tar.gz 아카이브 생성/추출
    REQ-BACKUP-003: SHA-256 체크섬 지원

    @MX:NOTE: 모든 경로는 절대 경로여야 합니다
    """

    def __init__(
        self,
        backup_dir: str,
        compress: bool = True,
        logger: BoundLogger | None = None,
    ):
        """
        ArchiveHandler 초기화

        Args:
            backup_dir: 백업 저장 디렉토리
            compress: 압축 여부 (tar.gz vs tar)
            logger: 로거 (선택)
        """
        self._backup_dir = Path(backup_dir)
        self._compress = compress
        self._logger = logger

        # 백업 디렉토리 생성
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    # ========================================================================
    # Public Methods
    # ========================================================================

    def create_archive(
        self,
        backup_id: str,
        files: list[str],
        metadata: dict[str, Any],
    ) -> str:
        """
        아카이브 생성

        REQ-BACKUP-008: tar.gz 아카이브에 파일과 메타데이터 포함

        Args:
            backup_id: 백업 ID
            files: 백업할 파일 경로 목록
            metadata: 백업 메타데이터

        Returns:
            str: 생성된 아카이브 파일 경로

        @MX:ANCHOR: create_archive
            fan_in: 3 (manual backup, auto backup, safety backup)
            @MX:REASON: 중앙 집중식 아카이브 생성
        """
        # 아카이브 파일 경로
        ext = ".tar.gz" if self._compress else ".tar"
        archive_path = self._backup_dir / f"{backup_id}{ext}"

        # 아카이브 생성 모드
        mode = "w:gz" if self._compress else "w"

        try:
            with tarfile.open(archive_path, mode) as tar:
                # 메타데이터 파일 추가 (먼저 추가하여 아카이브 시작부분에 위치)
                metadata_bytes = json.dumps(metadata, indent=2).encode("utf-8")
                import io

                tarinfo = tarfile.TarInfo(name="metadata.json")
                tarinfo.size = len(metadata_bytes)
                tar.addfile(tarinfo, fileobj=io.BytesIO(metadata_bytes))

                # 백업 파일 추가
                for file_path in files:
                    if Path(file_path).exists():
                        # 아카이브 내에서 상대 경로 유지
                        arcname = self._get_archive_name(file_path)
                        tar.add(file_path, arcname=arcname)

                        if self._logger:
                            self._logger.info(
                                "Added file to archive",
                                file=file_path,
                                archive=str(archive_path),
                            )
                    elif self._logger:
                        self._logger.warning(
                            "File not found, skipping",
                            file=file_path,
                        )

            if self._logger:
                self._logger.info(
                    "Archive created successfully",
                    archive=str(archive_path),
                    size=archive_path.stat().st_size,
                )

            return str(archive_path)

        except Exception as e:
            if self._logger:
                self._logger.error(
                    "Failed to create archive",
                    backup_id=backup_id,
                    error=str(e),
                )
            raise

    def extract_archive(
        self,
        archive_path: str,
        extract_dir: str,
    ) -> None:
        """
        아카이브 추출

        REQ-BACKUP-008: 아카이브 내 모든 파일 추출

        Args:
            archive_path: 아카이브 파일 경로
            extract_dir: 추출 대상 디렉토리

        Raises:
            FileNotFoundError: 아카이브 파일이 없을 때

        @MX:ANCHOR: extract_archive
            fan_in: 3 (restore, safety backup, test restore)
            @MX:REASON: 중앙 집중식 아카이브 추출
        """
        if not Path(archive_path).exists():
            raise FileNotFoundError(f"아카이브 파일을 찾을 수 없습니다: {archive_path}")

        # 추출 디렉토리 생성
        Path(extract_dir).mkdir(parents=True, exist_ok=True)

        # 아카이브 모드 결정
        mode = "r:gz" if archive_path.endswith(".gz") else "r"

        try:
            with tarfile.open(archive_path, mode) as tar:
                tar.extractall(path=extract_dir)

            if self._logger:
                self._logger.info(
                    "Archive extracted successfully",
                    archive=archive_path,
                    destination=extract_dir,
                )

        except Exception as e:
            if self._logger:
                self._logger.error(
                    "Failed to extract archive",
                    archive=archive_path,
                    error=str(e),
                )
            raise

    def get_metadata(self, archive_path: str) -> dict[str, Any]:
        """
        아카이브 메타데이터 추출

        REQ-BACKUP-001: 아카이브 내 메타데이터 조회

        Args:
            archive_path: 아카이브 파일 경로

        Returns:
            dict: 메타데이터 딕셔너리

        Raises:
            FileNotFoundError: 아카이브 파일이 없을 때
            KeyError: 메타데이터 파일이 없을 때
        """
        if not Path(archive_path).exists():
            raise FileNotFoundError(f"아카이브 파일을 찾을 수 없습니다: {archive_path}")

        mode = "r:gz" if archive_path.endswith(".gz") else "r"

        with tarfile.open(archive_path, mode) as tar:
            # 메타데이터 파일 추출
            member = tar.extractfile("metadata.json")
            if member is None:
                raise KeyError("메타데이터 파일을 찾을 수 없습니다: metadata.json")

            metadata_bytes = member.read()
            return json.loads(metadata_bytes.decode("utf-8"))

    def get_archive_size(self, archive_path: str) -> int:
        """
        아카이브 파일 크기 조회

        REQ-BACKUP-001: 백업 크기 정보 제공

        Args:
            archive_path: 아카이브 파일 경로

        Returns:
            int: 파일 크기 (bytes)
        """
        if not Path(archive_path).exists():
            raise FileNotFoundError(f"아카이브 파일을 찾을 수 없습니다: {archive_path}")

        return Path(archive_path).stat().st_size

    def delete_archive(self, archive_path: str) -> None:
        """
        아카이브 삭제

        REQ-BACKUP-007: 오래된 백업 정리

        Args:
            archive_path: 삭제할 아카이브 파일 경로
        """
        if Path(archive_path).exists():
            Path(archive_path).unlink()

            if self._logger:
                self._logger.info("Archive deleted", archive=archive_path)

    # ========================================================================
    # Private Methods
    # ========================================================================

    def _get_archive_name(self, file_path: str) -> str:
        """
        아카이브 내 파일 이름 생성

        데이터 파일은 'data/' 접두사, 설정 파일은 'config/' 접두사

        Args:
            file_path: 원본 파일 경로

        Returns:
            str: 아카이브 내 파일 이름
        """
        path = Path(file_path)

        # 데이터 디렉토리 파일
        if "data" in path.parts or path.name.endswith(".db"):
            return f"data/{path.name}"

        # 설정 디렉토리 파일
        if "config" in path.parts or path.suffix in [".json", ".yaml", ".yml"]:
            parts = path.parts
            if "config" in parts:
                config_idx = parts.index("config")
                return "/".join(parts[config_idx:])

        # 기본: 파일 이름만 사용
        return path.name


__all__ = [
    "ArchiveHandler",
]
