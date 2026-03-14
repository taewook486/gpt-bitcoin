# GPT Bitcoin 자동매매 시스템 운영 가이드

이 가이드는 GPT Bitcoin 자동매매 시스템의 배포, 모니터링, 문제 해결 절차를 설명합니다.

## 목차

1. [시스템 개요](#시스템-개요)
2. [배포 절차](#배포-절차)
3. [모니터링 절차](#모니터링-절차)
4. [문제 해결](#문제-해결)
5. [유지보수](#유지보수)

---

## 시스템 개요

### 시스템 아키텍처

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Grafana       │◄─────│  Prometheus     │◄─────│   Application   │
│   (포트 3000)   │      │  (포트 9090)    │      │   (포트 8000)   │
│                 │      │                 │      │                 │
│  - 대시보드     │      │  - 메트릭 수집  │      │  - 자동매매     │
│  - 시각화       │      │  - 알림 규칙    │      │  - API 서버     │
└─────────────────┘      └────────┬────────┘      └────────┬────────┘
                                   │                        │
                          ┌────────┴────────┐               │
                          │  AlertManager   │               │
                          │  (포트 9093)    │               │
                          │                 │               │
                          │  - 알림 라우팅  │               │
                          │  - 알림 관리    │               │
                          └─────────────────┘               │
                                                            │
                                   ┌─────────────────────────┴────────┐
                                   │                                  │
                            ┌──────┴──────┐                  ┌──────┴──────┐
                            │   Redis     │                  │ PostgreSQL  │
                            │ (포트 6379) │                  │ (포트 5432) │
                            │            │                  │             │
                            │  - 캐싱    │                  │  - 데이터  │
                            └────────────┘                  └─────────────┘
```

### 서비스 포트

| 서비스 | 포트 | 설명 |
|--------|------|------|
| Application | 8000 | FastAPI 애플리케이션 |
| Prometheus | 9090 | 메트릭 수집 및 저장 |
| Grafana | 3000 | 시각화 대시보드 |
| AlertManager | 9093 | 알림 라우팅 및 관리 |
| Redis | 6379 | 캐시 (선택 사항) |
| PostgreSQL | 5432 | 데이터베이스 (선택 사항) |

### 서비스 URL

- **애플리케이션**: http://localhost:8000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (기본 로그인: admin/admin)
- **AlertManager**: http://localhost:9093

---

## 배포 절차

### 1. Docker 이미지 빌드

로컬 환경에서 Docker 이미지를 빌드합니다.

```bash
# 프로젝트 디렉토리로 이동
cd /path/to/gpt-bitcoin

# Docker 이미지 빌드
docker-compose build

# 또는 Docker 직접 사용
docker build -t gpt-bitcoin:latest .
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 필요한 환경 변수를 설정합니다.

```bash
# .env 파일 생성
cat > .env << EOF
# OpenAI API 설정
OPENAI_API_KEY=your_openai_api_key_here

# Upbit API 설정
UPBIT_ACCESS_KEY=your_upbit_access_key_here
UPBIT_SECRET_KEY=your_upbit_secret_key_here

# SerpApi 설정 (선택 사항)
SERPAPI_API_KEY=your_serpapi_api_key_here

# 로깅 설정
LOG_LEVEL=INFO
LOG_FORMAT=json

# Grafana 설정
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_secure_password_here

# 비용 관리 설정
DAILY_COST_LIMIT=10000
COST_ALERT_THRESHOLD=8000
EOF
```

**중요**: `.env` 파일을 절대로 버전 관리 시스템에 커밋하지 마세요.

### 3. 서비스 시작

#### 기본 서비스 시작

```bash
# 메인 애플리케이션만 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f app
```

#### 모니터링 서비스 시작

```bash
# 모니터링 스택과 함께 시작
docker-compose --profile monitoring up -d

# 특정 모니터링 서비스만 시작
docker-compose up -d prometheus
docker-compose up -d grafana
docker-compose up -d alertmanager
```

#### 전체 서비스 시작

```bash
# 모든 서비스 시작 (애플리케이션 + 모니터링 + 캐시 + 데이터베이스)
docker-compose --profile monitoring --profile cache --profile database up -d

# 서비스 상태 확인
docker-compose ps
```

### 4. 서비스 상태 확인

```bash
# 모든 서비스 상태 확인
docker-compose ps

# 특정 서비스 로그 확인
docker-compose logs -f app
docker-compose logs -f prometheus
docker-compose logs -f grafana
docker-compose logs -f alertmanager

# 서비스 건강 상태 확인
curl http://localhost:8000/health
curl http://localhost:9090/-/healthy
curl http://localhost:3000/api/health
curl http://localhost:9093/-/healthy
```

### 5. 초기 설정

#### Grafana 설정

1. Grafana에 접속: http://localhost:3000
2. 기본 로그인: `admin` / `admin`
3. 비밀번호 변경 프롬프트에서 새 비밀번호 설정
4. Prometheus 데이터 소스가 자동으로 구성되어 있는지 확인

#### AlertManager 설정

1. AlertManager에 접속: http://localhost:9093
2. 알림 규칙이 올바르게 로드되었는지 확인
3. 알림 수신자 설정 검증

### 6. 프로덕션 배포

프로덕션 환경에서는 다음 사항을 고려하세요:

```bash
# 프로덕션 프로필로 시작
docker-compose --profile production up -d

# 로그를 파일로 저장
docker-compose logs -f app > /var/log/gpt-bitcoin/app.log 2>&1 &

# 로그 로테이션 설정
logrotate /etc/logrotate.d/gpt-bitcoin
```

---

## 모니터링 절차

### 1. Grafana 대시보드 접속

1. 브라우저에서 http://localhost:3000 접속
2. 로그인 (admin / 설정한 비밀번호)
3. 왼쪽 메뉴에서 **Dashboards** 선택
4. 사용 가능한 대시보드 확인:
   - **Trading Overview**: 거래 활동 및 성과
   - **System Performance**: 시스템 리소스 사용 현황
   - **API Monitoring**: GLM API 호출 및 비용

### 2. 주요 메트릭 확인

#### 거래 메트릭

- **총 거래 횟수**: `trading_decisions_total`
- **거래 성공율**: `trading_success_rate`
- **평균 실행 시간**: `trading_execution_duration_seconds`
- **현재 포지션**: `trading_current_position`

#### API 메트릭

- **API 호출 횟수**: `glm_api_requests_total`
- **토큰 사용량**: `glm_api_tokens_total`
- **응답 시간**: `glm_api_response_time_seconds`
- **에러율**: `glm_api_error_rate`

#### 시스템 메트릭

- **CPU 사용량**: `system_cpu_usage_percent`
- **메모리 사용량**: `system_memory_usage_bytes`
- **디스크 사용량**: `system_disk_usage_bytes`
- **네트워크 트래픽**: `system_network_traffic_bytes`

#### 비용 메트릭

- **추정 비용**: `system_cost_estimated_krw`
- **일일 비용**: `system_cost_daily_krw`
- **월간 비용**: `system_cost_monthly_krw`

### 3. Prometheus 쿼리 예시

Prometheus UI (http://localhost:9090)에서 다음 쿼리를 실행할 수 있습니다:

```promql
# 지난 1시간 동안의 거래 횟수
rate(trading_decisions_total[1h])

# 지난 5분간의 API 호출률
rate(glm_api_requests_total[5m])

# 현재 CPU 사용량
system_cpu_usage_percent

# 일일 비용 추이
system_cost_daily_krw
```

### 4. 알림 테스트

```bash
# 테스트 알림 전송
curl -X POST http://localhost:8000/alerts/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "receiver": "test",
    "status": "firing",
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "TestAlert",
        "severity": "info",
        "component": "test"
      },
      "annotations": {
        "summary": "테스트 알림",
        "description": "이것은 테스트 알림입니다"
      },
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

### 5. 알림 설정

#### Email 알림 설정

`monitoring/alertmanager.yml`에서 Email 설정을 활성화하세요:

```yaml
global:
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alertmanager@gpt-bitcoin.example.com'
  smtp_auth_username: 'alertmanager@example.com'
  smtp_auth_password: 'password'

receivers:
  - name: 'critical-alerts'
    email_configs:
      - to: 'admin@example.com'
        send_resolved: true
        headers:
          Subject: '[CRITICAL] GPT Bitcoin Alert'
```

#### Slack 알림 설정

Slack Webhook URL을 설정하세요:

```yaml
global:
  # Set your Slack Webhook URL via environment variable
  slack_api_url: '${SLACK_WEBHOOK_URL}'

receivers:
  - name: 'critical-alerts'
    slack_configs:
      - channel: '#critical-alerts'
        send_resolved: true
        title: 'Critical Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

### 6. 일일 점검 체크리스트

매일 다음 항목을 확인하세요:

- [ ] 애플리케이션 건강 상태 확인
- [ ] 거래 로그 확인
- [ ] API 비용 확인
- [ ] 시스템 리소스 사용량 확인
- [ ] 에러 로그 확인
- [ ] 알림이 정상 작동하는지 확인
- [ ] 백업이 완료되었는지 확인

---

## 문제 해결

### 일반적인 문제

#### 1. 서비스가 시작되지 않음

**증상**:
```bash
docker-compose up
# Error: Port 8000 is already allocated
```

**해결 방법**:
```bash
# 사용 중인 포트 확인
netstat -tulpn | grep 8000

# 충돌하는 서비스 중지
sudo systemctl stop conflicting-service

# 또는 docker-compose 포트 변경
# docker-compose.yml에서 포트 수정
```

#### 2. API 연결 실패

**증상**:
```
ConnectionError: Failed to connect to Upbit API
```

**해결 방법**:
```bash
# API 키 확인
cat .env | grep UPBIT

# 네트워크 연결 확인
ping api.upbit.com

# 방화벽 규칙 확인
sudo ufw status
```

#### 3. 메트릭이 수집되지 않음

**증상**:
Grafana 대시보드에 데이터가 표시되지 않음

**해결 방법**:
```bash
# Prometheus 타겟 상태 확인
curl http://localhost:9090/api/v1/targets

# 애플리케이션 메트릭 엔드포인트 확인
curl http://localhost:8000/metrics

# Prometheus 로그 확인
docker-compose logs prometheus | grep error
```

#### 4. 알림이 수신되지 않음

**증상**:
AlertManager가 알림을 전송하지 않음

**해결 방법**:
```bash
# AlertManager 로그 확인
docker-compose logs alertmanager

# 알림 규칙 확인
curl http://localhost:9093/api/v1/status

# 웹훅 엔드포인트 테스트
curl -X POST http://localhost:8000/alerts/webhook -d '{"test": true}'
```

### 로그 확인

#### 애플리케이션 로그

```bash
# 실시간 로그 확인
docker-compose logs -f app

# 최근 100줄 확인
docker-compose logs --tail=100 app

# 로그 파일 저장
docker-compose logs app > app-logs.txt
```

#### Prometheus 로그

```bash
# Prometheus 로그 확인
docker-compose logs prometheus

# Prometheus 로그 수준 설정
# docker-compose.yml에서 command 수정
command:
  - '--log.level=debug'
```

#### Grafana 로그

```bash
# Grafana 로그 확인
docker-compose logs grafana

# Grafana 로그 파일 경로
docker-compose exec grafana cat /var/log/grafana/grafana.log
```

### 문제 해결 프로세스

#### 1. 문제 진단

```bash
# 1. 서비스 상태 확인
docker-compose ps

# 2. 서비스 로그 확인
docker-compose logs

# 3. 리소스 사용량 확인
docker stats

# 4. 네트워크 연결 확인
docker network inspect gpt-bitcoin-network
```

#### 2. 문제 격리

```bash
# 문제가 되는 서비스만 중지
docker-compose stop prometheus

# 문제가 되는 서비스만 재시작
docker-compose restart prometheus

# 서비스 재구성
docker-compose up -d --force-recreate prometheus
```

#### 3. 롤백 절차

```bash
# 1. 현재 컨테이너 중지
docker-compose down

# 2. 이전 이미지 확인
docker images | grep gpt-bitcoin

# 3. 이전 이미지로 롤백
# docker-compose.yml에서 이미지 태그 변경
image: gpt-bitcoin:v1.0.0

# 4. 서비스 재시작
docker-compose up -d
```

### 긴급 상황 대응

#### 1. 모든 서비스 중지

```bash
# 모든 서비스 즉시 중지
docker-compose down

# 또는 특정 프로필만 중지
docker-compose --profile monitoring down
```

#### 2. 긴급 알림 발송

```bash
# 수동 알림 발송
curl -X POST http://localhost:8000/alerts/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "receiver": "critical-alerts",
    "status": "firing",
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "EmergencyShutdown",
        "severity": "critical"
      },
      "annotations": {
        "summary": "긴급 시스템 중단",
        "description": "시스템을 긴급 중단했습니다"
      },
      "startsAt": "2026-03-03T12:00:00Z",
      "endsAt": "0001-01-01T00:00:00Z",
      "generatorURL": "http://manual",
      "fingerprint": "emergency123"
    }],
    "groupLabels": {},
    "commonLabels": {},
    "commonAnnotations": {},
    "externalURL": "http://manual",
    "version": "4",
    "groupKey": "{}"
  }'
```

#### 3. 백업 및 복구

```bash
# 데이터 볼륨 백업
docker run --rm \
  -v gpt-bitcoin_prometheus-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/prometheus-backup.tar.gz -C /data .

# 복구
docker run --rm \
  -v gpt-bitcoin_prometheus-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/prometheus-backup.tar.gz -C /data
```

---

## 유지보수

### 정기 유지보수 작업

#### 주간 작업

- [ ] 로그 파일 백업
- [ ] 디스크 공간 확인
- [ ] 성능 메트릭 검토
- [ ] 알림 규칙 검토

#### 월간 작업

- [ ] 시스템 업데이트
- [ ] 보안 패치 적용
- [ ] 비용 최적화 검토
- [ ] 백업 테스트
- [ ] 재해 복구 훈련

### 업데이트 절차

#### 1. 시스템 업데이트

```bash
# 1. 최신 코드 가져오기
git pull origin main

# 2. 의존성 업데이트
pip install -r requirements.txt --upgrade

# 3. Docker 이미지 재빌드
docker-compose build

# 4. 서비스 재시작
docker-compose down
docker-compose up -d
```

#### 2. 롤링 업데이트

```bash
# Zero-downtime 업데이트
docker-compose up -d --no-deps --build app

# 또는 docker swarm 사용
docker service update --image gpt-bitcoin:latest gpt-bitcoin_app
```

### 백업 전략

#### 1. 데이터 백업

```bash
# Prometheus 데이터 백업
docker run --rm \
  -v gpt-bitcoin_prometheus-data:/data \
  -v /backup:/backup \
  alpine tar czf /backup/prometheus-$(date +%Y%m%d).tar.gz -C /data .

# Grafana 데이터 백업
docker run --rm \
  -v gpt-bitcoin_grafana-data:/data \
  -v /backup:/backup \
  alpine tar czf /backup/grafana-$(date +%Y%m%d).tar.gz -C /data .

# PostgreSQL 데이터 백업 (사용 시)
docker-compose exec postgres pg_dump -U g_user gpt_bitcoin > /backup/db-$(date +%Y%m%d).sql
```

#### 2. 설정 파일 백업

```bash
# 설정 파일 백업
tar czf config-backup-$(date +%Y%m%d).tar.gz \
  docker-compose.yml \
  monitoring/ \
  .env
```

### 모니터링 대시보드 관리

#### 1. 새 대시보드 추가

1. Grafana UI 접속
2. **Dashboards** → **New Dashboard**
3. **Add new panel**
4. PromQL 쿼리 입력
5. 시각화 유형 선택
6. 저장

#### 2. 대시보드 내보내기/가져오기

```bash
# 대시보드 내보내기
curl -u admin:password \
  http://localhost:3000/api/dashboards/uid/abc123

# 대시보드 가져오기
curl -u admin:password \
  -X POST \
  -H "Content-Type: application/json" \
  -d @dashboard.json \
  http://localhost:3000/api/dashboards/db
```

---

## 부록

### 유용한 명령어

```bash
# 컨테이너 리소스 사용량 확인
docker stats

# 네트워크 트래픽 확인
docker network inspect gpt-bitcoin-network

# 로그 실시간 모니터링
docker-compose logs -f

# 특정 시간대의 로그 확인
docker-compose logs --since 2026-03-03T00:00:00 app

# 서비스 재시작
docker-compose restart app

# 서비스 재구성
docker-compose up -d --force-recreate app
```

### 참고 자료

- [Docker Compose 문서](https://docs.docker.com/compose/)
- [Prometheus 문서](https://prometheus.io/docs/)
- [Grafana 문서](https://grafana.com/docs/)
- [AlertManager 문서](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [FastAPI 문서](https://fastapi.tiangolo.com/)

### 지원 및 문의

이슈가 발생하면 다음 단계를 따르세요:

1. 로그를 확인하세요
2. 이 문서의 문제 해결 섹션을 참조하세요
3. GitHub Issues에 문제를 보고하세요
