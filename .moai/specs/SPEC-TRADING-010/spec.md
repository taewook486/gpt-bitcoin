# SPEC-TRADING-010: Backup and Restore

## Metadata

- **SPEC ID**: SPEC-TRADING-010
- **Title**: Backup and Restore (백업 및 복원)
- **Created**: 2026-03-05
- **Status**: Completed
- **Priority**: Medium
- **Depends On**: SPEC-TRADING-002 (TradeHistoryService), SPEC-TRADING-006 (UserProfileService)
- **Lifecycle Level**: spec-first

---

## Problem Analysis

### Current State

SPEC-TRADING-002(TradeHistoryService)와 SPEC-TRADING-006(UserProfileService)에서 사용자 데이터를 SQLite에 저장합니다. 그러나 백업 및 복원 기능이 없어 다음과 같은 문제가 발생합니다:

1. **데이터 손실 위험**: 하드웨어 장애, 파일 손상 시 복구 불가
2. **이관 불가**: 새 시스템으로 데이터 이동 수단 없음
3. **버전 관리 부재**: 특정 시점으로 복원할 수 없음
4. **수동 백업 부담**: 사용자가 직접 DB 파일을 복사해야 함

### Root Cause Analysis (Five Whys)

1. **Why?** 데이터 백업 및 복원 메커니즘이 구현되지 않음
2. **Why?** 초기 구현에서 데이터 저장에 집중, 보호 계층 제외
3. **Why?** 백업이 인프라 문제로 간주되어 애플리케이션 레벨에서 제외
4. **Why?** 사용자 데이터 보호 책임이 명확히 정의되지 않음
5. **Root Cause**: 백업 및 복원 기능이 독립적인 서비스로 설계 필요

### Desired State

사용자가 거래 내역, 프로필, 설정을 백업하고, 필요 시 특정 시점으로 복원할 수 있습니다. 정기 자동 백업도 지원합니다.

---

## Environment

### Technology Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Backup Format | SQLite Dump + JSON | - | 표준 형식, 호환성 |
| Compression | gzip | Built-in | 백업 파일 크기 절감 |
| Scheduling | APScheduler | 3.10+ | 정기 백업 스케줄링 |
| Storage | Local Filesystem | - | 사용자 로컬 저장 |
| Encryption | Optional AES | - | 민감 데이터 보호 (선택) |

### Integration Points

```
SPEC-TRADING-002 (TradeHistoryService)
        ↓ Trade records
SPEC-TRADING-010 (BackupService)
        ↓ Backup archive
    Local Filesystem (.backup/)
        ↑ Restore
SPEC-TRADING-006 (UserProfileService)
        (Profile data)
```

### Constraints

1. **Storage**: 백업 파일 크기 제한 (기본 1GB)
2. **Retention**: 최대 30개 백업 파일 보관 (설정 가능)
3. **Performance**: 백업 생성 10초 이내 (10,000건 기준)
4. **Atomicity**: 백업 중 시스템 사용 가능해야 함

---

## Requirements (EARS Format)

### Ubiquitous Requirements

**REQ-BACKUP-001**: 시스템은 모든 사용자 데이터를 백업할 수 있어야 한다 (The system shall be able to backup all user data).

```
The system shall backup:
- SQLite databases (trades.db, profiles.db)
- Configuration files (config.json, settings.json)
- User preferences
Backup format: Compressed archive (.backup.tar.gz)
```

**REQ-BACKUP-002**: 시스템은 백업 메타데이터를 유지해야 한다 (The system shall maintain backup metadata).

```
The system shall store for each backup:
- Backup ID (UUID)
- Created timestamp
- File size
- Data types included (trades, profiles, config)
- Checksum (SHA-256)
- Version compatibility info
```

### Event-Driven Requirements

**REQ-BACKUP-003**: WHEN 사용자가 백업을 요청하면 THEN 시스템은 전체 백업을 생성해야 한다.

```
WHEN user clicks "백업 생성 (Create Backup)" button
THEN BackupService.create_backup() shall:
    AND export all SQLite databases
    AND export configuration files
    AND compress into single archive
    AND calculate checksum
    AND save to .backup/ directory
    AND return backup metadata
```

**REQ-BACKUP-004**: WHEN 사용자가 복원을 요청하면 THEN 시스템은 선택한 백업에서 데이터를 복원해야 한다.

```
WHEN user selects backup and clicks "복원 (Restore)" button
THEN BackupService.restore_backup() shall:
    AND validate backup integrity (checksum)
    AND create pre-restore backup (safety)
    AND extract archive
    AND restore databases
    AND restore configuration
    AND log restore action
    AND prompt user to restart application
```

### State-Driven Requirements

**REQ-BACKUP-005**: IF 백업 파일이 손상되었으면 THEN 시스템은 복원을 거부해야 한다.

```
IF backup checksum validation fails
THEN the system shall:
    AND reject restore operation
    AND return BackupCorruptedError
    AND log error with checksum mismatch details
    AND suggest alternative backup
```

**REQ-BACKUP-006**: IF 백업 보관 한도를 초과하면 THEN 시스템은 오래된 백업을 삭제해야 한다.

```
IF backup_count > max_retention (default 30)
THEN the system shall:
    AND delete oldest backup files
    AND keep newest backups
    AND log deletion action
    AND maintain retention limit
```

### Optional Requirements

**REQ-BACKUP-007**: Where possible, 시스템은 정기 자동 백업을 지원해야 한다.

```
Where possible, the system shall support scheduled automatic backups:
- Daily at configurable time (default 03:00)
- Weekly full backup
- Retention policy (keep last N backups)
- Notification on backup completion/failure
```

**REQ-BACKUP-008**: Where possible, 시스템은 백업 암호화를 지원해야 한다.

```
Where possible, the system shall support backup encryption:
- AES-256 encryption with user password
- Password-protected archive
- Decryption required for restore
```

### Unwanted Behavior Requirements

**REQ-BACKUP-009**: 시스템은 복원 중 데이터를 손실해서는 안 된다 (The system shall not lose data during restore).

```
The system shall NOT:
- Overwrite data without pre-restore backup
- Proceed if disk space insufficient
- Partially restore (all or nothing)

AND shall validate restore success before committing
```

**REQ-BACKUP-010**: 시스템은 백업에 민감한 자격 증명을 포함해서는 안 된다 (The system shall not include sensitive credentials in backups).

```
The system shall NOT include in backups:
- API secret keys (store references only)
- Encrypted passwords (already encrypted)
- PIN codes (never store)

AND shall exclude files matching patterns in .backupignore
```

---

## Specifications

### Data Model

#### BackupMetadata

```python
@dataclass
class BackupMetadata:
    """Metadata for a backup archive."""
    backup_id: str  # UUID
    created_at: datetime
    file_path: Path
    file_size_bytes: int
    checksum_sha256: str
    version: str  # Application version
    data_types: list[Literal["trades", "profiles", "config", "logs"]]
    is_encrypted: bool
    is_automatic: bool
    notes: str | None  # User-provided description

@dataclass
class BackupConfig:
    """Configuration for backup behavior."""
    backup_directory: Path = Path(".backup")
    max_retention_count: int = 30
    max_backup_size_mb: int = 1000
    auto_backup_enabled: bool = False
    auto_backup_time: str = "03:00"  # HH:MM
    auto_backup_frequency: Literal["daily", "weekly"] = "daily"
    encryption_enabled: bool = False
    exclude_patterns: list[str] = field(default_factory=lambda: ["*.log", "*.tmp"])

@dataclass
class RestoreResult:
    """Result of restore operation."""
    success: bool
    backup_id: str
    restored_at: datetime
    restored_types: list[str]
    pre_restore_backup_id: str | None  # Safety backup
    errors: list[str]
    warnings: list[str]
```

### SQLite Schema (Backup Registry)

```sql
CREATE TABLE IF NOT EXISTS backup_registry (
    backup_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    version TEXT NOT NULL,
    data_types TEXT NOT NULL,  -- JSON array
    is_encrypted INTEGER NOT NULL DEFAULT 0,
    is_automatic INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);

CREATE INDEX idx_backup_created ON backup_registry(created_at DESC);
```

### Component Architecture

```
src/gpt_bitcoin/
├── domain/
│   └── backup.py (NEW)
│       ├── BackupMetadata (dataclass)
│       ├── BackupConfig (dataclass)
│       ├── BackupService
│       └── RestoreValidator
├── infrastructure/
│   └── backup/
│       ├── __init__.py (NEW)
│       ├── backup_manager.py (NEW)
│       ├── archive_handler.py (NEW)
│       └── scheduler.py (NEW)
└── web_ui.py (MODIFY - add Backup tab)
```

### Class Design

#### BackupService

```python
class BackupService:
    """
    Domain service for backup and restore operations.

    Responsibilities:
    - Create full and partial backups
    - Restore from backup archives
    - Manage backup retention
    - Validate backup integrity

    @MX:NOTE: Uses atomic operations - either complete success or no change.
    """

    def __init__(
        self,
        config: BackupConfig,
        trade_history_service: TradeHistoryService,
        user_profile_service: UserProfileService,
    ):
        self._config = config
        self._trade_history = trade_history_service
        self._user_profile = user_profile_service
        self._registry = BackupRegistry(config.backup_directory)

    async def create_backup(
        self,
        data_types: list[str] | None = None,
        notes: str | None = None,
        is_automatic: bool = False,
    ) -> BackupMetadata:
        """
        Create a new backup.

        @MX:ANCHOR: Primary backup creation entry point.
            fan_in: 2+ (Web UI, Scheduler)
            @MX:REASON: Centralizes all backup operations.
        """
        pass

    async def restore_backup(
        self,
        backup_id: str,
        data_types: list[str] | None = None,
    ) -> RestoreResult:
        """
        Restore from a backup.

        @MX:WARN: Destructive operation - overwrites current data.
            Always creates safety backup before restore.
        """
        pass

    async def list_backups(self) -> list[BackupMetadata]:
        """List all available backups."""
        pass

    async def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup file and registry entry."""
        pass

    async def validate_backup(self, backup_id: str) -> bool:
        """Validate backup integrity using checksum."""
        pass

    async def cleanup_old_backups(self) -> int:
        """Remove old backups exceeding retention limit."""
        pass
```

### UI Design (Web UI)

#### Backup Settings Tab Structure

```
+-----------------------------------------------------------------+
| [Backup & Restore]                                               |
+-----------------------------------------------------------------+
| Current Status:                                                  |
| +------------------+ +------------------+ +------------------+    |
| | Total Backups    | | Latest Backup    | | Total Size       |    |
| | 12               | | 2026-03-05 03:00 | | 45.2 MB          |    |
| +------------------+ +------------------+ +------------------+    |
+-----------------------------------------------------------------+
| Backup List:                                                     |
| +--------------------------------------------------------+      |
| | Date       | Size    | Type              | Actions       |      |
| | 03/05 03:00| 3.8 MB  | Full (Auto)       | [Restore] [X] |      |
| | 03/04 15:30| 3.7 MB  | Full (Manual)     | [Restore] [X] |      |
| | 03/03 03:00| 3.6 MB  | Full (Auto)       | [Restore] [X] |      |
| +--------------------------------------------------------+      |
+-----------------------------------------------------------------+
| Create Backup:                                                   |
| [Select: All ▼] [Note: ____________________] [백업 생성]        |
+-----------------------------------------------------------------+
| Settings:                                                        |
| [x] Enable Auto Backup    [Time: 03:00 ▼] [Frequency: Daily ▼]  |
| Retention: [30] backups max   Max Size: [1000] MB               |
+-----------------------------------------------------------------+
| Restore:                                                         |
| Warning: Restore will overwrite current data.                    |
| A safety backup will be created before restore.                  |
| [Select backup to restore from list above]                       |
+-----------------------------------------------------------------+
```

---

## MX Tag Targets

### High Fan-In Functions (>= 3 callers)

| Function | Expected Fan-In | MX Tag Type | Location |
|----------|-----------------|-------------|----------|
| `BackupService.create_backup()` | 2+ | @MX:ANCHOR | domain/backup.py |
| `ArchiveHandler.create_archive()` | 2+ | @MX:NOTE | infrastructure/backup/archive_handler.py |

### Danger Zones (Complexity >= 15 or Critical Operations)

| Function | Risk | MX Tag Type | Reason |
|----------|------|-------------|--------|
| `restore_backup()` | Data loss | @MX:WARN | Overwrites current data |
| `cleanup_old_backups()` | Data loss | @MX:NOTE | Deletes backup files |
| Archive extraction | Security | @MX:NOTE | Path traversal risk |

---

## Files to Modify

### New Files

| File Path | Purpose | Lines (Est.) |
|-----------|---------|--------------|
| `src/gpt_bitcoin/domain/backup.py` | BackupService, data models | ~200 |
| `src/gpt_bitcoin/infrastructure/backup/__init__.py` | Package init | ~10 |
| `src/gpt_bitcoin/infrastructure/backup/backup_manager.py` | Backup operations | ~150 |
| `src/gpt_bitcoin/infrastructure/backup/archive_handler.py` | Archive creation/extraction | ~120 |
| `src/gpt_bitcoin/infrastructure/backup/scheduler.py` | Auto backup scheduling | ~80 |
| `tests/unit/domain/test_backup.py` | Unit tests | ~350 |
| `tests/unit/infrastructure/test_backup_manager.py` | Infrastructure tests | ~200 |

### Modified Files

| File Path | Changes | Lines Changed (Est.) |
|-----------|---------|---------------------|
| `src/gpt_bitcoin/web_ui.py` | Add Backup Settings tab | +120 |
| `src/gpt_bitcoin/dependencies/container.py` | Register BackupService | +15 |
| `src/gpt_bitcoin/config/settings.py` | Add backup config | +20 |

---

## Risks and Mitigations

### Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Backup file corruption | Low | High | Checksum validation, multiple backups |
| Restore failure mid-process | Low | High | Atomic operations, safety backup |
| Insufficient disk space | Medium | Medium | Pre-check disk space |
| Accidental restore of wrong backup | Medium | High | Confirmation dialogs, clear labeling |

### Recovery Plan

If restore fails:
1. Safety backup is automatically created before restore
2. System prompts user to use safety backup
3. Manual recovery instructions provided

---

## Traceability Matrix

| Requirement | Component | Test Case |
|-------------|-----------|-----------|
| REQ-BACKUP-001 | BackupService.create_backup() | test_create_full_backup() |
| REQ-BACKUP-002 | BackupMetadata | test_metadata_storage() |
| REQ-BACKUP-003 | BackupService.create_backup() | test_manual_backup() |
| REQ-BACKUP-004 | BackupService.restore_backup() | test_restore_operation() |
| REQ-BACKUP-005 | RestoreValidator | test_corrupted_backup_rejection() |
| REQ-BACKUP-006 | BackupService.cleanup_old_backups() | test_retention_policy() |
| REQ-BACKUP-007 | BackupScheduler | test_scheduled_backup() |
| REQ-BACKUP-008 | ArchiveHandler | test_encrypted_backup() |
| REQ-BACKUP-009 | BackupService.restore_backup() | test_atomic_restore() |
| REQ-BACKUP-010 | ArchiveHandler | test_credential_exclusion() |

---

## Success Criteria

1. **Functional**: All 10 requirements implemented and passing tests
2. **Reliability**: Restore success rate 100% for valid backups
3. **Coverage**: Minimum 85% test coverage
4. **Safety**: Pre-restore backup always created
5. **Performance**: Backup creation 10s for 10,000 records
6. **UI**: Backup/Restore tab functional with all features

---

## Related SPECs

- **SPEC-TRADING-002**: TradeHistoryService (trade data backup)
- **SPEC-TRADING-006**: UserProfileService (profile data backup)
- **SPEC-TRADING-009**: API Rate Limiting (similar retry/safety patterns)

---

Version: 1.0.0
Last Updated: 2026-03-05
Author: MoAI SPEC Builder
