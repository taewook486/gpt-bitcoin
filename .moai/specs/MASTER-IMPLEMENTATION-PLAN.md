# GPT Bitcoin Trading System - 마스터 구현 계획

**문서 버전:** 1.0.0
**생성 일자:** 2026-03-14
**프로젝트 상태:** 현대화 진행 중 (60% 완료)

---

## 1. 요약 (Executive Summary)

### 프로젝트 개요

GPT Bitcoin 자동 거래 시스템의 전체 SPEC 항목에 대한 우선순위 기반 구현 계획입니다.

### 현재 상태

| 지표 | 수치 |
|------|------|
| **총 SPEC 수** | 12개 |
| **완료됨** | 0개 (0%) |
| **진행 중** | 1개 (SPEC-MODERNIZE-001, 60% 완료) |
| **미시작** | 11개 (92%) |

### 주요 발견사항

1. **비용 절감 기회**: OpenAI API → GLM-5 마이그레이션으로 **60-70% 비용 절감** 가능
2. **안정성 개선**: API Rate Limiting 구현으로 거래 안정성 확보
3. **데이터 보호**: Backup/Restore 시스템으로 자산 보호
4. **인프라 완성**: SPEC-MODERNIZE-001 Phases 6-8 완료로 현대적 아키텍처 확립

---

## 2. 우선순위 그룹별 분류

### P1 (Critical) - 즉시 구현 권장

| SPEC ID | 제목 | 근거 | 예상 노력 |
|---------|------|------|-----------|
| **SPEC-UPDATE-AI-001** | GLM-5 AI 모델 마이그레이션 | OpenAI → GLM-5 전환으로 **60-70% 비용 절감** | M (중간) |
| **SPEC-TRADING-009** | API Rate Limiting | Upbit API 안정성 확보, 거래 실패 방지 | S (작음) |

### P2 (High) - P1 완료 후 구현

| SPEC ID | 제목 | 근거 | 예상 노력 |
|---------|------|------|-----------|
| **SPEC-MODERNIZE-001** | 시스템 현대화 (Phases 6-8) | 인프라 완성, 모니터링 및 백업 시스템 | L (큼) |
| **SPEC-TRADING-010** | 백업 및 복구 | 데이터 보호, 재해 복구 capability | M (중간) |
| **SPEC-TRADING-008** | 포트폴리오 분석 대시보드 | 사용자 경험 개선, 투자 분석 | L (큼) |

### P3 (Medium) - 리소스 허용 시 구현

| SPEC ID | 제목 | 근거 | 예상 노력 |
|---------|------|------|-----------|
| **SPEC-TRADING-007** | 알림 시스템 | 거래 알림, 가격 경고 | M (중간) |
| **SPEC-TRADING-001** | Upbit 실거래 | 핵심 거래 기능 | XL (매우 큼) |
| **SPEC-TRADING-002** | 거래 내역 | 데이터 추적 및 분석 | M (중간) |
| **SPEC-TRADING-003** | CLI 통합 | 명령줄 인터페이스 | S (작음) |
| **SPEC-TRADING-004** | 보안/2FA 시스템 | 보안 강화 | M (중간) |
| **SPEC-TRADING-005** | 테스트넷 모드 | 안전한 테스트 환경 | M (중간) |
| **SPEC-TRADING-006** | 사용자 프로필 관리 | 사용자 관리 | S (작음) |
| **SPEC-REFACTOR-PYTHON-001** | Python 코드 리팩토링 | 코드 품질 개선 | L (큼) |

---

## 3. 구현 타임라인 권장사항

### Q1 2026 (1-3월): 비용 절감 및 안정성

**목표:** 운영 비용 절감 및 API 안정성 확보

| 작업 | SPEC | 기간 | 담당 에이전트 |
|------|------|------|---------------|
| GLM-5 마이그레이션 | SPEC-UPDATE-AI-001 | 2주 | expert-backend |
| API Rate Limiting | SPEC-TRADING-009 | 1주 | expert-backend |

**예상 효과:**
- 월 운영비 60-70% 절감
- API 호출 실패율 90% 감소

### Q2 2026 (4-6월): 인프라 완성

**목표:** 현대적 인프라 완성 및 데이터 보호

| 작업 | SPEC | 기간 | 담당 에이전트 |
|------|------|------|---------------|
| 시스템 현대화 완료 | SPEC-MODERNIZE-001 (Phases 6-8) | 4주 | expert-backend, expert-devops |
| 백업 및 복구 | SPEC-TRADING-010 | 2주 | expert-backend |
| 포트폴리오 대시보드 | SPEC-TRADING-008 | 3주 | expert-frontend, expert-backend |

**예상 효과:**
- 완전한 모니터링 시스템 구축
- 재해 복구 capability 확보
- 사용자 경험 대폭 개선

### Q3-Q4 2026 (7-12월): 기능 확장

**목표:** 핵심 거래 기능 및 부가 기능 구현

| 작업 | SPEC | 기간 | 담당 에이전트 |
|------|------|------|---------------|
| 알림 시스템 | SPEC-TRADING-007 | 2주 | expert-backend |
| 실거래 기능 | SPEC-TRADING-001 | 6주 | expert-backend, expert-security |
| 거래 내역 | SPEC-TRADING-002 | 2주 | expert-backend |
| CLI 통합 | SPEC-TRADING-003 | 1주 | expert-backend |
| 보안/2FA | SPEC-TRADING-004 | 3주 | expert-security |
| 테스트넷 모드 | SPEC-TRADING-005 | 2주 | expert-backend |
| 사용자 프로필 | SPEC-TRADING-006 | 1주 | expert-backend |
| 코드 리팩토링 | SPEC-REFACTOR-PYTHON-001 | 4주 | expert-refactoring |

---

## 4. 의존성 그래프

```
┌─────────────────────────────────────────────────────────────┐
│                    P1 (독립 실행 가능)                       │
│  ┌──────────────────┐     ┌──────────────────┐              │
│  │ SPEC-UPDATE-     │     │ SPEC-TRADING-    │              │
│  │ AI-001           │     │ 009              │              │
│  │ (GLM-5 마이그레이션)│     │ (Rate Limiting)  │              │
│  └──────────────────┘     └────────┬─────────┘              │
└─────────────────────────────────────┼───────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    P2 (P1 완료 후 시작)                      │
│  ┌──────────────────┐     ┌──────────────────┐              │
│  │ SPEC-MODERNIZE-  │────▶│ SPEC-TRADING-    │              │
│  │ 001 (Phases 6-8) │     │ 010 (Backup)     │              │
│  └──────────────────┘     └──────────────────┘              │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────┐                                       │
│  │ SPEC-TRADING-    │                                       │
│  │ 008 (Dashboard)  │                                       │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    P3 (P2 완료 후 시작)                      │
│  ┌──────────────────┐     ┌──────────────────┐              │
│  │ SPEC-TRADING-    │────▶│ SPEC-TRADING-    │              │
│  │ 001 (실거래)      │     │ 002 (History)    │              │
│  └──────────────────┘     └──────────────────┘              │
│           │                                                 │
│           ├──────────────┬──────────────┬──────────────┐    │
│           ▼              ▼              ▼              ▼    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────┐│
│  │SPEC-007     │ │SPEC-003     │ │SPEC-004     │ │SPEC-005││
│  │(알림)       │ │(CLI)        │ │(보안/2FA)   │ │(테스트넷)││
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────┘│
│                                     │                        │
│                                     ▼                        │
│                            ┌─────────────┐                  │
│                            │SPEC-006     │                  │
│                            │(프로필)     │                  │
│                            └─────────────┘                  │
└─────────────────────────────────────────────────────────────┘

병렬 실행 가능:
- SPEC-TRADING-001 완료 후: 002, 003, 007, 004, 005 병렬 진행 가능
- SPEC-REFACTOR-PYTHON-001: 모든 기능 구현 후 진행 권장
```

### 핵심 의존성 규칙

1. **SPEC-TRADING-009 (Rate Limiting) → SPEC-TRADING-001 (실거래)**
   - 이유: API 안정성이 거래 기능의 전제 조건

2. **SPEC-TRADING-010 (Backup) → 무거운 거래 활동**
   - 이유: 데이터 보호가 대규모 거래 전 필수

3. **SPEC-UPDATE-AI-001 (GLM-5) → 독립 실행**
   - 이유: 다른 기능과 무관하게 즉시 비용 절감 가능

---

## 5. 리소스 및 노력 추정

### 노력 등급 정의

| 등급 | 범위 | 예상 기간 | 파일 수 | 복잡도 |
|------|------|-----------|---------|--------|
| **S (Small)** | 단일 모듈 | 1-2주 | 1-3개 | 낮음 |
| **M (Medium)** | 여러 모듈 | 2-3주 | 4-7개 | 중간 |
| **L (Large)** | 아키텍처 변경 | 3-5주 | 8-15개 | 높음 |
| **XL (Extra Large)** | 핵심 시스템 | 5-8주 | 16개 이상 | 매우 높음 |

### SPEC별 상세 추정

#### P1 Critical

| SPEC | 노력 | 위험도 | 필요 스킬 | 담당 에이전트 |
|------|------|--------|-----------|---------------|
| SPEC-UPDATE-AI-001 | M | 중간 | Python, API 통합, GLM SDK | expert-backend |
| SPEC-TRADING-009 | S | 낮음 | Python, Rate Limiting 패턴 | expert-backend |

#### P2 High

| SPEC | 노력 | 위험도 | 필요 스킬 | 담당 에이전트 |
|------|------|--------|-----------|---------------|
| SPEC-MODERNIZE-001 | L | 중간 | DDD, TDD, Python, 모니터링 | expert-backend, expert-devops |
| SPEC-TRADING-010 | M | 낮음 | Python, 백업 패턴, 암호화 | expert-backend |
| SPEC-TRADING-008 | L | 중간 | React, TypeScript, FastAPI | expert-frontend, expert-backend |

#### P3 Medium

| SPEC | 노력 | 위험도 | 필요 스킬 | 담당 에이전트 |
|------|------|--------|-----------|---------------|
| SPEC-TRADING-001 | XL | 높음 | Python, Upbit API, 거래 로직 | expert-backend, expert-security |
| SPEC-TRADING-002 | M | 낮음 | Python, Database, 데이터 모델링 | expert-backend |
| SPEC-TRADING-003 | S | 낮음 | Python, CLI 설계 | expert-backend |
| SPEC-TRADING-004 | M | 중간 | Python, 2FA, 보안 패턴 | expert-security |
| SPEC-TRADING-005 | M | 낮음 | Python, 테스트 패턴 | expert-backend |
| SPEC-TRADING-006 | S | 낮음 | Python, 데이터 모델링 | expert-backend |
| SPEC-TRADING-007 | M | 낮음 | Python, 알림 서비스 | expert-backend |
| SPEC-REFACTOR-PYTHON-001 | L | 중간 | Python, 리팩토링 패턴 | expert-refactoring |

### 총 리소스 추정

| 우선순위 | 총 노력 | 예상 기간 | 팀 규모 권장 |
|----------|---------|-----------|--------------|
| P1 | 1.5M | 3주 | 1-2명 |
| P2 | 2.5L | 9주 | 2-3명 |
| P3 | 1XL + 4M + 2S + 1L | 20주 | 2-3명 |
| **전체** | - | **32주 (8개월)** | **2-3명** |

---

## 6. 빠른 성과 (Quick Wins)

### 즉시 실행 가능한 고가치 작업

#### 1순위: SPEC-UPDATE-AI-001 (GLM-5 마이그레이션)

**선택 이유:**
- 독립 실행 가능 (의존성 없음)
- 즉각적인 비용 절감 (60-70%)
- 낮은 위험도
- 빠른 구현 (2주)

**예상 ROI:**
- 월 $100 운영비 → $30-40으로 절감
- 투자 대비 즉각적 수익

#### 2순위: SPEC-TRADING-009 (API Rate Limiting)

**선택 이유:**
- 낮은 복잡도 (S 등급)
- 높은 안정성 개선 효과
- 향후 모든 거래 기능의 기반

**예상 효과:**
- API 호출 실패율 90% 감소
- 거래 신뢰성 확보

---

## 7. 위험 분석 및 완화 전략

### 고위험 항목

#### SPEC-TRADING-001 (실거래) - 위험도: 높음

**위험 요소:**
- 실제 자금 관련
- API 오류로 인한 손실 가능성
- 잘못된 거래 로직의 치명적 결과

**완화 전략:**
1. **SPEC-TRADING-005 (테스트넷) 먼저 구현**
   - 실제 자금 없이 거래 로직 검증
2. **SPEC-TRADING-009 (Rate Limiting) 선행**
   - API 안정성 확보
3. **SPEC-TRADING-010 (Backup) 선행**
   - 데이터 보호 메커니즘 확보
4. **단계적 출시**
   - 소액 거래로 시작
   - 점진적 금액 증가

#### SPEC-MODERNIZE-001 (Phases 6-8) - 위험도: 중간

**위험 요소:**
- 대규모 아키텍처 변경
- 기존 기능 영향 가능성

**완화 전략:**
1. **TDD 적용**
   - 테스트 커버리지 85% 이상 유지
2. **단계적 배포**
   - Phase별 독립 검증
3. **롤백 계획**
   - 각 Phase별 롤백 포인트 설정

---

## 8. 다음 단계 (Next Actions)

### 즉시 시작 권장 작업

#### 추천 1: SPEC-UPDATE-AI-001 (GLM-5 마이그레이션)

```bash
# 실행 명령
/moai:1-plan "GLM-5 AI Model Migration"
# SPEC 승인 후
/moai:2-run SPEC-UPDATE-AI-001
```

**선택 근거:**
- 독립 실행으로 즉시 착수 가능
- 비용 절감 효과 즉각적
- 낮은 위험도

#### 추천 2: SPEC-TRADING-009 (API Rate Limiting)

```bash
# 실행 명령
/moai:1-plan "API Rate Limiting"
# SPEC 승인 후
/moai:2-run SPEC-TRADING-009
```

**선택 근거:**
- 향후 모든 거래 기능의 필수 기반
- 빠른 구현 가능 (1주)
- 높은 안정성 개선 효과

### 시작 전 체크리스트

#### 공통 전제조건

- [ ] `.moai/project/product.md` 최신화
- [ ] `.moai/project/tech.md` 기술 스택 확인
- [ ] 개발 환경 설정 완료
- [ ] 테스트 환경 준비

#### SPEC-UPDATE-AI-001 특수 전제조건

- [ ] GLM-5 API 키 확보
- [ ] 기존 OpenAI 사용 패턴 분석
- [ ] 마이그레이션 영향도 평가

#### SPEC-TRADING-009 특수 전제조건

- [ ] Upbit API 제한 사항 문서화
- [ ] 현재 API 호출 패턴 분석
- [ ] Rate Limiting 전략 수립

---

## 9. 성공 지표 (Success Metrics)

### KPI 정의

#### P1 완료 기준

| 지표 | 목표 | 측정 방법 |
|------|------|-----------|
| 비용 절감 | 60% 이상 | 월별 API 비용 비교 |
| API 안정성 | 99.5% 가용성 | API 성공률 모니터링 |
| 테스트 커버리지 | 85% 이상 | pytest-cov 측정 |

#### P2 완료 기준

| 지표 | 목표 | 측정 방법 |
|------|------|-----------|
| 인프라 현대화 | 100% 완료 | Phase별 체크리스트 |
| 백업 신뢰성 | 99.9% 복구 성공 | 정기 복구 테스트 |
| 사용자 만족도 | 4.5/5.0 | 대시보드 사용성 평가 |

#### P3 완료 기준

| 지표 | 목표 | 측정 방법 |
|------|------|-----------|
| 거래 성공률 | 99% 이상 | 거래 실행 로그 |
| 보안 취약점 | 0건 | 정기 보안 스캔 |
| 코드 품질 | A 등급 | 정적 분석 도구 |

---

## 10. 부록

### A. SPEC 상세 목록

| SPEC ID | 제목 | 상태 | 우선순위 | 노력 |
|---------|------|------|----------|------|
| SPEC-MODERNIZE-001 | 시스템 현대화 | 진행 중 (60%) | P2 | L |
| SPEC-UPDATE-AI-001 | GLM-5 마이그레이션 | 미시작 | P1 | M |
| SPEC-TRADING-001 | Upbit 실거래 | 미시작 | P3 | XL |
| SPEC-TRADING-002 | 거래 내역 | 미시작 | P3 | M |
| SPEC-TRADING-003 | CLI 통합 | 미시작 | P3 | S |
| SPEC-TRADING-004 | 보안/2FA 시스템 | 미시작 | P3 | M |
| SPEC-TRADING-005 | 테스트넷 모드 | 미시작 | P3 | M |
| SPEC-TRADING-006 | 사용자 프로필 관리 | 미시작 | P3 | S |
| SPEC-TRADING-007 | 알림 시스템 | 미시작 | P3 | M |
| SPEC-TRADING-008 | 포트폴리오 분석 대시보드 | 미시작 | P2 | L |
| SPEC-TRADING-009 | API Rate Limiting | 미시작 | P1 | S |
| SPEC-TRADING-010 | 백업 및 복구 | 미시작 | P2 | M |
| SPEC-REFACTOR-PYTHON-001 | Python 코드 리팩토링 | 미시작 | P3 | L |

### B. 에이전트 매핑

| 에이전트 | 주요 담당 SPEC | 보조 담당 SPEC |
|----------|----------------|----------------|
| expert-backend | 001, 002, 003, 005, 006, 007, 008, 009, 010, UPDATE-AI-001 | MODERNIZE-001 |
| expert-frontend | 008 | - |
| expert-security | 001, 004 | 010 |
| expert-devops | MODERNIZE-001 | 008, 010 |
| expert-refactoring | REFACTOR-PYTHON-001 | MODERNIZE-001 |

### C. 기술 스택 요구사항

| 카테고리 | 기술 | 버전 |
|----------|------|------|
| 언어 | Python | 3.11+ |
| 웹 프레임워크 | FastAPI | 0.115+ |
| 프론트엔드 | React | 19+ |
| 프론트엔드 프레임워크 | Next.js | 16+ |
| ORM | SQLAlchemy | 2.0+ |
| 데이터 검증 | Pydantic | 2.9+ |
| 테스트 | pytest | 8.0+ |
| AI 모델 | GLM-5 | Latest |
| 거래소 API | Upbit | v1 |

---

**문서 관리:**
- 업데이트 주기: 분기별 또는 주요 SPEC 완료 시
- 책임자: Project Manager
- 검토자: Technical Architect

**변경 이력:**
| 버전 | 일자 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 1.0.0 | 2026-03-14 | 초기 문서 생성 | MoAI System |
