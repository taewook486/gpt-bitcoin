# GPT Bitcoin 자동매매 시스템 API 문서

이 문서는 GPT Bitcoin 자동매매 시스템의 API 엔드포인트를 설명합니다.

## 기본 정보

- **Base URL**: `http://localhost:8000`
- **API Version**: v1
- **Content-Type**: `application/json`

## 인증

현재 시스템은 인증이 필요하지 않습니다. 모든 엔드포인트는 공개되어 있습니다.

## 엔드포인트

### 건강 상태 확인

현재 애플리케이션의 건강 상태를 확인합니다.

**엔드포인트**: `GET /health`

**설명**: 애플리케이션이 정상적으로 실행 중인지 확인합니다.

**요청 예시**:
```bash
curl http://localhost:8000/health
```

**응답 예시**:
```json
{
  "status": "healthy",
  "service": "gpt-bitcoin-auto-trading",
  "version": "1.0.0",
  "timestamp": "2026-03-03T12:00:00Z"
}
```

**상태 코드**:
- `200 OK`: 애플리케이션이 정상 작동 중

---

### 메트릭 조회

Prometheus 형식의 메트릭을 조회합니다.

**엔드포인트**: `GET /metrics`

**설명**: Prometheus 스크래핑을 위한 메트릭 데이터를 제공합니다.

**요청 예시**:
```bash
curl http://localhost:8000/metrics
```

**응답 예시**:
```
# HELP trading_decisions_total Total number of trading decisions made
# TYPE trading_decisions_total counter
trading_decisions_total{version="v3"} 42.0

# HELP trading_execution_duration_seconds Trading decision execution duration in seconds
# TYPE trading_execution_duration_seconds histogram
trading_execution_duration_seconds_bucket{version="v3",le="0.1"} 5.0
trading_execution_duration_seconds_bucket{version="v3",le="0.5"} 15.0
trading_execution_duration_seconds_bucket{version="v3",le="1.0"} 20.0
trading_execution_duration_seconds_bucket{version="v3",le="+Inf"} 25.0
trading_execution_duration_seconds_sum{version="v3"} 8.5
trading_execution_duration_seconds_count{version="v3"} 25.0

# HELP glm_api_requests_total Total number of GLM API requests
# TYPE glm_api_requests_total counter
glm_api_requests_total{model="glm-4-plus",endpoint="chat.completions"} 156.0

# HELP glm_api_tokens_total Total number of tokens used
# TYPE glm_api_tokens_total counter
glm_api_tokens_total{model="glm-4-plus",type="prompt"} 45000.0
glm_api_tokens_total{model="glm-4-plus",type="completion"} 12000.0

# HELP system_cost_estimated_krw Estimated system cost in KRW
# TYPE system_cost_estimated_krw gauge
system_cost_estimated_krw{version="v3"} 8500.0
```

**상태 코드**:
- `200 OK`: 메트릭 데이터 반환 성공

---

### 알림 웹훅

AlertManager로부터 알림을 수신합니다.

**엔드포인트**: `POST /alerts/webhook`

**설명**: Prometheus AlertManager로부터 발생한 알림을 수신하고 처리합니다.

**요청 헤더**:
```
Content-Type: application/json
X-Alert-Priority: critical (optional)
X-Alert-Type: cost (optional)
X-Alert-Component: trading (optional)
```

**요청 본문 예시**:
```json
{
  "receiver": "critical-alerts",
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "HighAPICost",
        "severity": "critical",
        "component": "glm-api"
      },
      "annotations": {
        "summary": "GLM API daily cost exceeded threshold",
        "description": "Current cost: 9500 KRW, Threshold: 8000 KRW"
      },
      "startsAt": "2026-03-03T12:00:00Z",
      "endsAt": "0001-01-01T00:00:00Z",
      "generatorURL": "http://prometheus:9090/...",
      "fingerprint": "abc123def456"
    }
  ],
  "groupLabels": {
    "alertname": "HighAPICost",
    "severity": "critical"
  },
  "commonLabels": {
    "alertname": "HighAPICost",
    "severity": "critical"
  },
  "commonAnnotations": {
    "summary": "GLM API daily cost exceeded threshold"
  },
  "externalURL": "http://localhost:9093",
  "version": "4",
  "groupKey": "{}:{alertname=\"HighAPICost\"}",
  "truncatedAlerts": 0
}
```

**응답 예시**:
```json
{
  "status": "success",
  "message": "Alerts processed successfully",
  "processed_alerts": 1,
  "deduplicated_alerts": 0,
  "timestamp": "2026-03-03T12:00:00Z"
}
```

**상태 코드**:
- `202 Accepted`: 알림 수신 및 처리 성공
- `400 Bad Request`: 잘못된 요청 형식
- `500 Internal Server Error`: 서버 내부 오류

---

### 알림 건강 상태 확인

알림 핸들러의 건강 상태를 확인합니다.

**엔드포인트**: `GET /alerts/health`

**설명**: 알림 웹훅 핸들러가 정상 작동하는지 확인합니다.

**요청 예시**:
```bash
curl http://localhost:8000/alerts/health
```

**응답 예시**:
```json
{
  "status": "healthy",
  "service": "alert-handlers",
  "timestamp": "2026-03-03T12:00:00Z"
}
```

**상태 코드**:
- `200 OK`: 알림 핸들러 정상 작동

---

### 알림 통계 조회

알림 처리 통계를 조회합니다.

**엔드포인트**: `GET /alerts/stats`

**설명**: 알림 처리 및 중복 제거 통계를 반환합니다.

**요청 예시**:
```bash
curl http://localhost:8000/alerts/stats
```

**응답 예시**:
```json
{
  "deduplication": {
    "backend": "redis",
    "cache_size": 42,
    "dedup_window_seconds": 300
  },
  "timestamp": "2026-03-03T12:00:00Z"
}
```

**상태 코드**:
- `200 OK`: 통계 반환 성공

---

## 데이터 모델

### AlertLabel
알림 라벨 정보입니다.

| 필드 | 타입 | 설명 |
|------|------|------|
| alertname | string | 알림 이름 |
| severity | string | 심각도 (critical, warning, info) |
| component | string | 컴포넌트 이름 |
| cost_type | string \| null | 비용 유형 (선택 사항) |

### AlertAnnotation
알림 추가 정보입니다.

| 필드 | 타입 | 설명 |
|------|------|------|
| summary | string | 알림 요약 |
| description | string \| null | 상세 설명 (선택 사항) |
| value | string \| null | 측정값 (선택 사항) |
| runbook_url | string \| null | 운영 가이드 URL (선택 사항) |

### Alert
개별 알림 정보입니다.

| 필드 | 타입 | 설명 |
|------|------|------|
| status | string | 알림 상태 (firing, resolved) |
| labels | AlertLabel | 알림 라벨 |
| annotations | AlertAnnotation | 알림 주석 |
| startsAt | datetime | 알림 시작 시간 |
| endsAt | datetime | 알림 종료 시간 |
| generatorURL | string | Prometheus 생성기 URL |
| fingerprint | string | 알림 고유 식별자 |
| receiver | string | 수신자 이름 |

### AlertManagerWebhook
AlertManager 웹훅 페이로드입니다.

| 필드 | 타입 | 설명 |
|------|------|------|
| receiver | string | 수신자 이름 |
| status | string | 웹훅 상태 |
| alerts | Alert[] | 알림 배열 |
| groupLabels | object | 그룹 라벨 |
| commonLabels | object | 공통 라벨 |
| commonAnnotations | object | 공통 주석 |
| externalURL | string | AlertManager 외부 URL |
| version | string | API 버전 |
| groupKey | string | 그룹 키 |
| truncatedAlerts | integer | 잘린 알림 수 |

### AlertResponse
알림 처리 응답입니다.

| 필드 | 타입 | 설명 |
|------|------|------|
| status | string | 처리 상태 |
| message | string | 처리 메시지 |
| processed_alerts | integer | 처리된 알림 수 |
| deduplicated_alerts | integer | 중복 제거된 알림 수 |
| timestamp | datetime | 처리 시간 |

---

## 에러 응답

모든 엔드포인트는 다음과 같은 표준 에러 응답 형식을 사용합니다.

```json
{
  "detail": "Error message description"
}
```

### 공통 에러 코드

| 상태 코드 | 설명 |
|-----------|------|
| 400 | 잘못된 요청 형식 |
| 404 | 리소스를 찾을 수 없음 |
| 422 | 요청 데이터 검증 실패 |
| 500 | 서버 내부 오류 |
| 503 | 서비스를 사용할 수 없음 |

---

## 설정

환경 변수를 통해 API 동작을 구성할 수 있습니다.

### API 서버 설정

```bash
# API 서버 포트 (기본값: 8000)
API_PORT=8000

# API 호스트 (기본값: 0.0.0.0)
API_HOST=0.0.0.0

# 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

### 알림 설정

```bash
# 알림 중복 제거 창 (초)
ALERT_DEDUP_WINDOW=300

# Redis 연결 (선택 사항)
REDIS_URL=redis://localhost:6379/0
```

---

## 사용 예시

### cURL 예시

```bash
# 건강 상태 확인
curl -X GET http://localhost:8000/health

# 메트릭 조회
curl -X GET http://localhost:8000/metrics

# 알림 건강 상태 확인
curl -X GET http://localhost:8000/alerts/health

# 알림 통계 조회
curl -X GET http://localhost:8000/alerts/stats

# 알림 웹훅 테스트
curl -X POST http://localhost:8000/alerts/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "receiver": "test",
    "status": "firing",
    "alerts": [{
      "status": "firing",
      "labels": {"alertname": "TestAlert", "severity": "info"},
      "annotations": {"summary": "Test alert"},
      "startsAt": "2026-03-03T12:00:00Z",
      "endsAt": "0001-01-01T00:00:00Z",
      "generatorURL": "http://test",
      "fingerprint": "test123"
    }],
    "groupLabels": {},
    "commonLabels": {},
    "commonAnnotations": {},
    "externalURL": "http://test",
    "version": "4",
    "groupKey": "{}"
  }'
```

### Python 예시

```python
import requests

# 건강 상태 확인
response = requests.get("http://localhost:8000/health")
print(response.json())

# 메트릭 조회
response = requests.get("http://localhost:8000/metrics")
print(response.text)

# 알림 통계 조회
response = requests.get("http://localhost:8000/alerts/stats")
print(response.json())

# 알림 웹훅 전송
alert_payload = {
    "receiver": "test",
    "status": "firing",
    "alerts": [{
        "status": "firing",
        "labels": {"alertname": "TestAlert", "severity": "info"},
        "annotations": {"summary": "Test alert"},
        "startsAt": "2026-03-03T12:00:00Z",
        "endsAt": "0001-01-01T00:00:00Z",
        "generatorURL": "http://test",
        "fingerprint": "test123"
    }],
    "groupLabels": {},
    "commonLabels": {},
    "commonAnnotations": {},
    "externalURL": "http://test",
    "version": "4",
    "groupKey": "{}"
}

response = requests.post(
    "http://localhost:8000/alerts/webhook",
    json=alert_payload
)
print(response.json())
```

---

## Docker Compose 프로필

Docker Compose를 사용하여 다양한 구성으로 시스템을 실행할 수 있습니다.

### 기본 서비스

```bash
# 메인 애플리케이션만 실행
docker-compose up -d
```

### 모니터링 프로필

```bash
# 모니터링 서비스와 함께 실행
docker-compose --profile monitoring up -d

# 모니터링 서비스만 실행
docker-compose --profile monitoring up -d prometheus grafana alertmanager
```

### 캐시 프로필

```bash
# Redis와 함께 실행
docker-compose --profile cache up -d
```

### 데이터베이스 프로필

```bash
# PostgreSQL과 함께 실행
docker-compose --profile database up -d
```

### 전체 프로필

```bash
# 모든 서비스 실행
docker-compose --profile monitoring --profile cache --profile database up -d
```

---

## 참고 자료

- [Prometheus 문서](https://prometheus.io/docs/)
- [AlertManager 문서](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Grafana 문서](https://grafana.com/docs/)
- [FastAPI 문서](https://fastapi.tiangolo.com/)
