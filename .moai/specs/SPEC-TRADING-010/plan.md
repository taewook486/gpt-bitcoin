# Implementation Plan: SPEC-TRADING-010 (Backup and Restore)

## Overview

이 문서는 SPEC-TRADING-010 백업 및 복원 기능의 구현 계획을 정의합니다.

---

## Milestones (Priority-Based)

### Phase 1: Core Backup Functionality (Primary Goal)

**Objective**: 기본 백업 생성 및 복원 기능 구현

#### Tasks

1. **Data Models**
   - Priority: Critical
   - Create `BackupMetadata` dataclass
   - Create `BackupConfig` dataclass
   - Create `RestoreResult` dataclass
   - Add validation

2. **ArchiveHandler**
   - Priority: Critical
   - Implement archive creation (tar.gz)
   - Implement archive extraction
   - Add checksum calculation
   - Handle path traversal prevention

3. **BackupService**
   - Priority: High
   - Implement `create_backup()` method
   - Implement `restore_backup()` method
   - Implement `list_backups()` method
   - Implement `validate_backup()` method

4. **BackupRegistry**
   - Priority: High
   - Implement SQLite registry for backup metadata
   - Add CRUD operations
   - Support filtering and sorting

5. **Unit Tests - Core**
   - Priority: High
   - Test backup creation
   - Test restore operation
   - Test checksum validation
   - Test error scenarios

**Deliverables**:
- Working backup creation
- Working restore operation
- Backup registry
- All core tests passing

---

### Phase 2: Safety Features (Secondary Goal)

**Objective**: 안전한 복원을 위한 보호 기능 구현

#### Tasks

1. **Pre-Restore Backup**
   - Priority: High
   - Automatically create backup before restore
   - Store pre-restore backup metadata
   - Provide recovery option if restore fails

2. **Validation**
   - Priority: High
   - Implement checksum validation
   - Detect corrupted archives
   - Validate version compatibility

3. **Atomic Operations**
   - Priority: High
   - Implement all-or-nothing restore
   - Rollback on partial failure
   - Transaction-like behavior

4. **Error Handling**
   - Priority: Medium
   - Handle disk space issues
   - Handle permission errors
   - Provide clear error messages

**Deliverables**:
- Safety backup before restore
- Validation working
- Atomic operations

---

### Phase 3: Web UI Integration (Final Goal)

**Objective**: Web UI에 백업/복원 탭 추가

#### Tasks

1. **Backup Settings Tab**
   - Priority: High
   - Create new tab in Streamlit UI
   - Display backup list
   - Add backup creation controls

2. **Restore UI**
   - Priority: High
   - Add restore selection
   - Show confirmation dialog
   - Display progress

3. **Settings Panel**
   - Priority: Medium
   - Auto backup configuration
   - Retention policy settings
   - Max size configuration

4. **UI Tests**
   - Priority: Medium
   - Test tab rendering
   - Test backup creation flow
   - Test restore flow

**Deliverables**:
- Complete Backup Settings tab
- All UI interactions working
- User-friendly experience

---

### Phase 4: Automatic Backup (Optional)

**Objective**: 정기 자동 백업 기능

#### Tasks

1. **BackupScheduler**
   - Priority: Low
   - Implement APScheduler integration
   - Support daily/weekly schedules
   - Handle application restart

2. **Background Tasks**
   - Priority: Low
   - Run backup in background
   - Notify on completion
   - Handle failures gracefully

**Deliverables**:
- Scheduled automatic backups
- Background execution
- Notification integration

---

## Technical Approach

### Archive Format

```
.backup/
├── backup-20260305-030000-{uuid}.tar.gz
├── backup-20260304-030000-{uuid}.tar.gz
└── registry.db

Archive contents:
├── manifest.json       # Backup metadata
├── trades.db          # Trade history database
├── profiles.db        # User profiles database
├── config/
│   ├── settings.json  # Application settings
│   └── preferences.json
└── checksums.sha256   # File checksums
```

### Archive Handler

```python
# infrastructure/backup/archive_handler.py

import tarfile
import hashlib
import json
from pathlib import Path

class ArchiveHandler:
    """Handle backup archive creation and extraction."""

    def __init__(self, backup_dir: Path):
        self._backup_dir = backup_dir

    async def create_archive(
        self,
        files: dict[str, Path],
        output_path: Path,
    ) -> str:
        """
        Create compressed archive.

        @MX:NOTE: Uses tar.gz for cross-platform compatibility.
        """
        # Create manifest
        manifest = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "files": list(files.keys()),
        }

        with tarfile.open(output_path, "w:gz") as tar:
            # Add manifest
            manifest_bytes = json.dumps(manifest).encode()
            tar.addfile(
                tarfile.TarInfo("manifest.json"),
                io.BytesIO(manifest_bytes),
            )

            # Add files
            for name, path in files.items():
                if path.exists():
                    tar.add(path, arcname=name)

        # Calculate checksum
        return self._calculate_checksum(output_path)

    async def extract_archive(
        self,
        archive_path: Path,
        target_dir: Path,
        expected_checksum: str,
    ) -> bool:
        """
        Extract archive with validation.

        @MX:WARN: Path traversal prevention applied.
        """
        # Validate checksum
        actual_checksum = self._calculate_checksum(archive_path)
        if actual_checksum != expected_checksum:
            raise BackupCorruptedError(
                f"Checksum mismatch: expected {expected_checksum}, "
                f"got {actual_checksum}"
            )

        # Extract with path traversal prevention
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar.getmembers():
                # Prevent path traversal
                if ".." in member.name or member.name.startswith("/"):
                    raise SecurityError(f"Unsafe path in archive: {member.name}")

                tar.extract(member, target_dir)

        return True

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
```

### Backup Service

```python
# domain/backup.py

class BackupService:
    """Backup and restore service."""

    async def create_backup(
        self,
        data_types: list[str] | None = None,
        notes: str | None = None,
        is_automatic: bool = False,
    ) -> BackupMetadata:
        """
        Create a new backup.

        @MX:ANCHOR: Primary backup creation entry point.
        """
        backup_id = str(uuid4())
        timestamp = datetime.now()

        # Collect files to backup
        files = {}
        if data_types is None or "trades" in data_types:
            files["trades.db"] = self._get_trades_db_path()
        if data_types is None or "profiles" in data_types:
            files["profiles.db"] = self._get_profiles_db_path()
        if data_types is None or "config" in data_types:
            files["config/settings.json"] = self._get_config_path()

        # Create archive
        archive_path = self._config.backup_directory / f"backup-{timestamp.strftime('%Y%m%d-%H%M%S')}-{backup_id[:8]}.tar.gz"
        checksum = await self._archive_handler.create_archive(files, archive_path)

        # Create metadata
        metadata = BackupMetadata(
            backup_id=backup_id,
            created_at=timestamp,
            file_path=archive_path,
            file_size_bytes=archive_path.stat().st_size,
            checksum_sha256=checksum,
            version=__version__,
            data_types=data_types or ["trades", "profiles", "config"],
            is_encrypted=self._config.encryption_enabled,
            is_automatic=is_automatic,
            notes=notes,
        )

        # Save to registry
        await self._registry.save(metadata)

        # Cleanup old backups
        await self.cleanup_old_backups()

        return metadata

    async def restore_backup(
        self,
        backup_id: str,
        data_types: list[str] | None = None,
    ) -> RestoreResult:
        """
        Restore from backup.

        @MX:WARN: Creates safety backup before restore.
        """
        # Get backup metadata
        metadata = await self._registry.get(backup_id)
        if not metadata:
            raise BackupNotFoundError(backup_id)

        # Validate backup
        if not await self.validate_backup(backup_id):
            raise BackupCorruptedError(backup_id)

        # Create safety backup
        safety_backup = await self.create_backup(
            data_types=data_types,
            notes="Pre-restore safety backup",
            is_automatic=True,
        )

        try:
            # Extract and restore
            temp_dir = Path(tempfile.mkdtemp())
            await self._archive_handler.extract_archive(
                metadata.file_path,
                temp_dir,
                metadata.checksum_sha256,
            )

            # Restore files
            restored_types = []
            errors = []

            for data_type in (data_types or metadata.data_types):
                try:
                    self._restore_data_type(temp_dir, data_type)
                    restored_types.append(data_type)
                except Exception as e:
                    errors.append(f"{data_type}: {str(e)}")

            return RestoreResult(
                success=len(errors) == 0,
                backup_id=backup_id,
                restored_at=datetime.now(),
                restored_types=restored_types,
                pre_restore_backup_id=safety_backup.backup_id,
                errors=errors,
                warnings=[],
            )

        except Exception as e:
            # Restore from safety backup
            await self._restore_from_safety(safety_backup)
            raise
```

---

## Architecture Design

### Package Structure

```
src/gpt_bitcoin/
├── domain/
│   ├── backup.py              # [NEW] BackupService
│   ├── trade_history.py       # [EXISTING]
│   └── user_profile.py        # [EXISTING]
│
├── infrastructure/
│   └── backup/                # [NEW PACKAGE]
│       ├── __init__.py
│       ├── backup_manager.py  # BackupManager
│       ├── archive_handler.py # Archive operations
│       ├── registry.py        # Backup registry
│       └── scheduler.py       # Auto backup scheduler
│
├── dependencies/
│   └── container.py           # [MODIFY] Register services
│
├── config/
│   └── settings.py            # [MODIFY] Add backup config
│
└── web_ui.py                  # [MODIFY] Add Backup tab
```

### Data Flow

```
+------------------+
| Web UI           |
| (Backup Tab)     |
+--------+---------+
         | Create Backup
         v
+------------------+
| BackupService    |
+--------+---------+
         |
         +-----> Collect files (TradeHistory, UserProfile)
         |
         v
+------------------+
| ArchiveHandler   |
+--------+---------+
         |
         v
+------------------+         +------------------+
| Compressed       |         | BackupRegistry   |
| Archive (.tar.gz)|         | (SQLite)         |
+------------------+         +------------------+
```

---

## Configuration Changes

### Settings Additions

```python
# config/settings.py additions

class Settings(BaseSettings):
    # ... existing settings ...

    # Backup Settings
    backup_directory: str = Field(
        default=".backup",
        description="Directory for backup storage",
    )
    backup_max_retention: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Maximum number of backups to keep",
    )
    backup_max_size_mb: int = Field(
        default=1000,
        ge=10,
        description="Maximum total backup size in MB",
    )
    backup_auto_enabled: bool = Field(
        default=False,
        description="Enable automatic backups",
    )
    backup_auto_time: str = Field(
        default="03:00",
        description="Time for automatic backup (HH:MM)",
    )
    backup_auto_frequency: str = Field(
        default="daily",
        description="Backup frequency (daily, weekly)",
    )
```

### Container Registration

```python
# dependencies/container.py additions

from gpt_bitcoin.domain.backup import BackupService, BackupConfig
from gpt_bitcoin.infrastructure.backup import ArchiveHandler, BackupRegistry

class Container(containers.DeclarativeContainer):
    # ... existing providers ...

    backup_config: providers.Provider[BackupConfig] = providers.Factory(
        BackupConfig,
        backup_directory=Path(settings.provided.backup_directory),
        max_retention_count=settings.provided.backup_max_retention,
        auto_backup_enabled=settings.provided.backup_auto_enabled,
    )

    archive_handler: providers.Provider[ArchiveHandler] = providers.Factory(
        ArchiveHandler,
        backup_dir=backup_config.provided.backup_directory,
    )

    backup_service: providers.Provider[BackupService] = providers.Factory(
        BackupService,
        config=backup_config,
        trade_history_service=trade_history_service,
        user_profile_service=user_profile_service,
    )
```

---

## Testing Strategy

### Test Coverage Goals

| Component | Target Coverage | Priority |
|-----------|-----------------|----------|
| BackupMetadata | 100% | Critical |
| ArchiveHandler | 95% | Critical |
| BackupService | 90% | High |
| Web UI Integration | 70% | Medium |

### Key Test Cases

```python
# tests/unit/domain/test_backup.py

class TestBackupService:
    """Test BackupService."""

    @pytest.mark.asyncio
    async def test_create_backup(self, service, sample_data):
        """Test backup creation."""
        metadata = await service.create_backup()

        assert metadata.backup_id is not None
        assert metadata.file_path.exists()
        assert len(metadata.checksum_sha256) == 64  # SHA-256 hex

    @pytest.mark.asyncio
    async def test_restore_backup(self, service, backup_metadata):
        """Test restore operation."""
        result = await service.restore_backup(backup_metadata.backup_id)

        assert result.success is True
        assert result.pre_restore_backup_id is not None  # Safety backup

    @pytest.mark.asyncio
    async def test_restore_corrupted_backup(self, service, corrupted_backup):
        """Test restore with corrupted backup."""
        with pytest.raises(BackupCorruptedError):
            await service.restore_backup(corrupted_backup.backup_id)

    @pytest.mark.asyncio
    async def test_retention_policy(self, service):
        """Test old backup cleanup."""
        # Create 35 backups
        for _ in range(35):
            await service.create_backup()

        # Check retention
        backups = await service.list_backups()
        assert len(backups) <= 30  # max_retention
```

---

## Dependencies

### New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| APScheduler | >=3.10.0 | Scheduled backups (optional) |

### Built-in Dependencies Used

| Package | Usage |
|---------|-------|
| tarfile | Archive creation |
| hashlib | Checksum calculation |
| gzip | Compression |
| tempfile | Temporary extraction |

---

## Security Considerations

### Path Traversal Prevention

```python
def _validate_archive_path(self, member: tarfile.TarInfo) -> bool:
    """Validate archive member path is safe."""
    # Reject absolute paths
    if member.name.startswith("/"):
        return False

    # Reject parent directory references
    if ".." in member.name:
        return False

    # Reject symlinks pointing outside
    if member.issym() or member.islnk():
        if ".." in member.linkname:
            return False

    return True
```

### Credential Exclusion

- API keys stored as references, not values
- .backupignore patterns applied
- Sensitive files explicitly excluded

---

Version: 1.0.0
Last Updated: 2026-03-05
Author: MoAI SPEC Builder
