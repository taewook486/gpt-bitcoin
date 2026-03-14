# Acceptance Criteria: SPEC-TRADING-010 (Backup and Restore)

## Overview

이 문서는 SPEC-TRADING-010 백업 및 복원 기능의 수락 기준을 Gherkin 형식(Given-When-Then)으로 정의합니다.

---

## Feature 1: Backup Creation

### Scenario 1.1: Create Full Backup

```gherkin
Feature: 백업 생성 (Backup Creation)

  Scenario: 전체 백업 생성
    Given 사용자가 백업 탭에 있음
      And 거래 내역 100건이 있음
      And 프로필이 설정되어 있음
    When "백업 생성" 버튼 클릭
    Then 새 백업 파일이 생성됨
      And 백업 ID가 할당됨
      And 백업 파일에 trades.db가 포함됨
      And 백업 파일에 profiles.db가 포함됨
      And 백업 파일에 config가 포함됨
      And 체크섬이 계산되어 저장됨
```

### Scenario 1.2: Partial Backup

```gherkin
  Scenario: 부분 백업 생성
    Given 사용자가 백업 탭에 있음
    When 데이터 유형을 "거래 내역만"으로 선택
      And "백업 생성" 버튼 클릭
    Then 백업 파일에 trades.db만 포함됨
      And profiles.db는 포함되지 않음
```

### Scenario 1.3: Backup with Notes

```gherkin
  Scenario: 메모와 함께 백업
    Given 사용자가 백업 탭에 있음
    When 메모에 "업데이트 전 백업" 입력
      And "백업 생성" 버튼 클릭
    Then 백업 메타데이터에 메모가 저장됨
      And 백업 목록에 메모가 표시됨
```

---

## Feature 2: Backup Validation

### Scenario 2.1: Checksum Validation

```gherkin
Feature: 백업 검증 (Backup Validation)

  Scenario: 체크섬 검증
    Given 백업 파일이 생성됨
    When 백업 검증 실행
    Then SHA-256 체크섬이 계산됨
      And 체크섬이 메타데이터와 일치함
```

### Scenario 2.2: Detect Corrupted Backup

```gherkin
  Scenario: 손상된 백업 감지
    Given 백업 파일이 손상됨 (내용 변경됨)
    When 백업 검증 실행
    Then 검증이 실패함
      And "백업 파일이 손상되었습니다" 에러 메시지 표시
```

---

## Feature 3: Restore Operation

### Scenario 3.1: Full Restore

```gherkin
Feature: 복원 작업 (Restore Operation)

  Scenario: 전체 복원
    Given 백업 파일이 존재함
      And 현재 데이터와 백업 데이터가 다름
    When 백업 선택 후 "복원" 버튼 클릭
      And 확인 대화상자에서 "확인" 클릭
    Then 복원 전 안전 백업이 생성됨
      And 백업 데이터로 복원됨
      And "복원 완료" 메시지 표시
      And "애플리케이션을 재시작하세요" 안내 표시
```

### Scenario 3.2: Safety Backup Created

```gherkin
  Scenario: 안전 백업 생성
    Given 복원 작업 시작
    When 복원 실행
    Then 복원 전 현재 데이터의 백업이 생성됨
      And 안전 백업 ID가 결과에 포함됨
```

### Scenario 3.3: Restore from Corrupted Backup

```gherkin
  Scenario: 손상된 백업 복원 시도
    Given 손상된 백업 파일이 있음
    When 복원 시도
    Then 복원이 거부됨
      And BackupCorruptedError 발생
      And 현재 데이터는 변경되지 않음
```

### Scenario 3.4: Partial Restore

```gherkin
  Scenario: 부분 복원
    Given 백업 파일이 거래 내역과 프로필을 포함함
    When "거래 내역만" 선택 후 복원
    Then trades.db만 복원됨
      And profiles.db는 변경되지 않음
```

---

## Feature 4: Backup List

### Scenario 4.1: List All Backups

```gherkin
Feature: 백업 목록 (Backup List)

  Scenario: 모든 백업 목록 표시
    Given 5개의 백업이 존재함
    When 백업 탭 열람
    Then 5개의 백업이 목록에 표시됨
      And 최신 백업이 상단에 표시됨
      And 각 백업에 날짜, 크기, 유형이 표시됨
```

### Scenario 4.2: Backup Details

```gherkin
  Scenario: 백업 상세 정보
    Given 백업 목록이 표시됨
    When 특정 백업 행 클릭
    Then 상세 정보가 표시됨:
      | 항목           | 내용                    |
      | 백업 ID        | UUID                    |
      | 생성 일시      | 2026-03-05 03:00:00    |
      | 파일 크기      | 3.8 MB                  |
      | 데이터 유형    | trades, profiles, config|
      | 체크섬         | SHA-256 해시            |
      | 메모           | 사용자가 입력한 메모    |
```

---

## Feature 5: Retention Policy

### Scenario 5.1: Cleanup Old Backups

```gherkin
Feature: 보관 정책 (Retention Policy)

  Scenario: 오래된 백업 정리
    Given 최대 보관 수가 30개로 설정됨
      And 현재 35개의 백업이 있음
    When 새 백업 생성
    Then 가장 오래된 6개 백업이 삭제됨
      And 30개의 백업만 남음
      And 삭제 로그가 기록됨
```

### Scenario 5.2: Keep Recent Backups

```gherkin
  Scenario: 최신 백업 유지
    Given 35개의 백업이 있음
    When 정리 실행
    Then 최신 30개 백업이 유지됨
      And 가장 오래된 5개가 삭제됨
```

---

## Feature 6: Automatic Backup

### Scenario 6.1: Scheduled Daily Backup

```gherkin
Feature: 자동 백업 (Automatic Backup)

  Scenario: 매일 정기 백업
    Given 자동 백업이 활성화됨
      And 백업 시간이 03:00으로 설정됨
    When 03:00이 됨
    Then 자동으로 백업이 생성됨
      And 백업 메타데이터에 is_automatic = true 표시
```

### Scenario 6.2: Disabled Auto Backup

```gherkin
  Scenario: 자동 백업 비활성화
    Given 자동 백업이 비활성화됨
    When 03:00이 됨
    Then 자동 백업이 실행되지 않음
```

---

## Feature 7: Error Handling

### Scenario 7.1: Insufficient Disk Space

```gherkin
Feature: 에러 처리 (Error Handling)

  Scenario: 디스크 공간 부족
    Given 남은 디스크 공간이 10MB임
      And 백업 크기가 50MB임
    When 백업 생성 시도
    Then "디스크 공간이 부족합니다" 에러 발생
      And 부분 백업 파일이 삭제됨
```

### Scenario 7.2: Permission Error

```gherkin
  Scenario: 권한 오류
    Given 백업 디렉토리에 쓰기 권한이 없음
    When 백업 생성 시도
    Then "백업 디렉토리에 쓸 수 없습니다" 에러 발생
      And 해결 방법 안내 표시
```

### Scenario 7.3: Restore Rollback on Failure

```gherkin
  Scenario: 복원 실패 시 롤백
    Given 복원 작업 진행 중
    When 복원 중 에러 발생
    Then 이전 상태로 롤백됨
      And 안전 백업에서 복원 가능함
      And 에러 로그가 기록됨
```

---

## Feature 8: Security

### Scenario 8.1: Path Traversal Prevention

```gherkin
Feature: 보안 (Security)

  Scenario: 경로 순회 방지
    Given 악의적인 백업 파일이 있음
      And 아카이브에 "../../../etc/passwd" 경로가 포함됨
    When 복원 시도
    Then 보안 오류로 거부됨
      And "안전하지 않은 경로" 에러 발생
```

### Scenario 8.2: Credential Exclusion

```gherkin
  Scenario: 자격 증명 제외
    Given API 키가 설정되어 있음
    When 백업 생성
    Then 백업에 API 키 값이 포함되지 않음
      And API 키 참조만 포함됨
```

---

## Feature 9: Web UI

### Scenario 9.1: Backup Tab Display

```gherkin
Feature: Web UI

  Scenario: 백업 탭 표시
    Given 사용자가 Web UI에 로그인함
    When "백업 및 복원" 탭 클릭
    Then 백업 탭이 표시됨
      And 현재 상태 카드가 표시됨
      And 백업 목록이 표시됨
      And 백업 생성 버튼이 표시됨
```

### Scenario 9.2: Confirmation Dialog

```gherkin
  Scenario: 복원 확인 대화상자
    Given 사용자가 복원 버튼 클릭
    Then 확인 대화상자가 표시됨
      And "현재 데이터가 덮어씌워집니다" 경고 표시
      And "계속하시겠습니까?" 질문 표시
```

### Scenario 9.3: Progress Display

```gherkin
  Scenario: 진행 상황 표시
    Given 백업 생성 시작
    When 백업 진행 중
    Then 진행 상황이 표시됨
      And 스피너 또는 진행바 표시
      And 완료 시 성공 메시지 표시
```

---

## Quality Gates

### Test Coverage

```gherkin
Feature: 테스트 커버리지

  Scenario: 최소 커버리지 달성
    Given 모든 테스트가 작성됨
    When pytest --cov 실행
    Then 전체 커버리지 >= 85%
      And BackupService 커버리지 >= 90%
      And ArchiveHandler 커버리지 >= 95%
```

### Performance

```gherkin
Feature: 성능 기준

  Scenario: 백업 생성 성능
    Given 10,000건의 거래 내역이 있음
    When 전체 백업 생성
    Then 완료 시간 < 10초
      And 백업 파일 크기 < 50MB
```

### Reliability

```gherkin
Feature: 신뢰성

  Scenario: 복원 신뢰성
    Given 100개의 유효한 백업이 있음
    When 각 백업에서 복원
    Then 복원 성공률 100%
      And 데이터 무결성 유지
```

---

## Definition of Done

- [ ] 모든 Gherkin 시나리오에 대한 테스트 구현
- [ ] 테스트 커버리지 85% 이상 달성
- [ ] Web UI에 백업 탭 추가 완료
- [ ] 백업 생성 기능 작동
- [ ] 복원 기능 작동
- [ ] 안전 백업 기능 작동
- [ ] 체크섬 검증 작동
- [ ] 보관 정책 작동
- [ ] 경로 순회 방지 작동
- [ ] Lint 에러 0개
- [ ] Type checking 에러 0개
- [ ] 문서화 완료 (docstrings)

---

Version: 1.0.0
Last Updated: 2026-03-05
Author: MoAI SPEC Builder
