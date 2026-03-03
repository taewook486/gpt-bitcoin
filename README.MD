# 비트코인 GPT 인공지능 AI 업비트 자동매매 시스템 만들기
- GPT API를 활용하여 투자를 자동화 합니다. by 유튜버 조코딩

## 관련 링크
- [수업 자료](https://jocoding.net/bitcoin)
- [1편 - 라이브 풀버전 링크(멤버십 전용)](https://youtube.com/live/-7IVgjUw79s?feature=share)
- [2편 - 라이브 풀버전 링크(멤버십 전용)](https://youtube.com/live/GhZenus5rww?feature=share)
- [3편 - 라이브 풀버전 링크(멤버십 전용)](https://youtube.com/live/ORo8QAn-g74?feature=share)
- [4편 - 라이브 풀버전 링크(멤버십 전용)](https://youtube.com/live/mUTGW4MhL-8?feature=share)

- [(재촬영 편집본) GPT에게 맡기는 AI 비트코인 투자 자동화](https://www.youtube.com/playlist?list=PLU9-uwewPMe0LLUQrBm9vfS62Jkju_rpU)

## 전략 소개
### 1.autotrade.py, instruction.md
- 데이터: 일(30일), 시간(24시간) OHLCV, Moving Averages, RSI, Stochastic Oscillator, MACD, Bollinger Bands, Orderbook Data
- 전략: 1시간에 한번 판단하여 전량 매수/매도 or 홀드

### 2.autotrade_v2.py, instruction_v2.md
- 데이터: 일(30일), 시간(24시간) OHLCV, Moving Averages, RSI, Stochastic Oscillator, MACD, Bollinger Bands, Orderbook Data, 최신 뉴스 데이터(SerpApi), 공포/탐욕 지수
- 전략:  8시간에 한번 판단하여 부분 매수/매도 or 홀드, 투자 데이터 기록하고 AI 재귀 개선
- 뉴스 데이터 조회를 위한 [SerpApi](https://serpapi.com/) 가입 및 API KEY 등록 필요

### 3.autotrade_v3.py, instruction_v3.md
- 데이터: 일(30일), 시간(24시간) OHLCV, Moving Averages, RSI, Stochastic Oscillator, MACD, Bollinger Bands, Orderbook Data, 최신 뉴스 데이터(SerpApi), 공포/탐욕 지수, 차트 이미지(Selenium, GPT-4o 활용)
- 전략:  8시간에 한번 판단하여 부분 매수/매도 or 홀드, 투자 데이터 기록하고 AI 재귀 개선
- 뉴스 데이터 조회를 위한 [SerpApi](https://serpapi.com/) 가입 및 API KEY 등록 필요

## .env 파일 생성 및 설정
```
OPENAI_API_KEY="YourKey"
UPBIT_ACCESS_KEY="YourKey"
UPBIT_SECRET_KEY="YourKey"
SERPAPI_API_KEY="YourKey"
```

## 로컬 환경 설정
```
pip install -r requirements.txt
```

## AWS EC2 Ubuntu 서버 설정 방법
### 업비트 API 허용 IP 설정
[업비트 API 홈페이지](https://upbit.com/mypage/open_api_management)

### 기본 세팅
- 한국 기준으로 서버 시간 설정
```
sudo ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime
```
- 패키지 목록 업데이트
```
sudo apt update
```
- 패키지 목록 업그레이드
```
sudo apt upgrade
```
- pip3 설치
```
sudo apt install python3-pip
```
### 레포지토리 가져오기
```
git clone https://github.com/youtube-jocoding/gpt-bitcoin.git
```
### 서버에서 라이브러리 설치
```
pip3 install -r requirements.txt
```
### .env 파일 만들고 API KEY 넣기
```
vim .env
```
### 명령어
- 현재 경로 상세 출력
```
ls -al
```
- 경로 이동
```
cd 경로
```
- vim 에디터로 파일 열기
```
vim autotrade.py
```
- vim 에디터 입력: i
- vim 에디터 저장: ESC + wq!
### 실행하기
- 그냥 실행
```
python3 autotrade.py
```
- 백그라운드 실행
```
nohup python3 -u autotrade.py > output.log 2>&1 &
```
- 로그 보기
```
cat output.log
tail -f output.log
```
- 실행 확인
```
ps ax | grep .py
```
- 종료하기
```
kill -9 PID
ex. kill -9 13586
```
## 모니터링 시스템

이 시스템은 Prometheus, Grafana, AlertManager를 통합한 모니터링 기능을 제공합니다.

### 서비스 구성

- **Prometheus** (포트 9090): 메트릭 수집 및 저장
- **Grafana** (포트 3000): 시각화 대시보드
- **AlertManager** (포트 9093): 알림 라우팅 및 관리

### Docker Compose로 모니터링 서비스 시작

```bash
# 모니터링 서비스 시작
docker-compose --profile monitoring up -d

# 특정 서비스만 시작
docker-compose up -d prometheus
docker-compose up -d grafana
docker-compose up -d alertmanager
```

### 서비스 접속

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (기본 로그인: admin/admin)
- AlertManager: http://localhost:9093

### 모니터링 메트릭

시스템은 다음 메트릭을 제공합니다:

- **거래 관련**: 총 거래 횟수, 성공/실패율, 평균 실행 시간
- **API 관련**: GLM API 호출 횟수, 응답 시간, 에러율
- **시스템 리소스**: CPU 사용량, 메모리 사용량, 디스크 I/O
- **비용 관련**: GLM API 비용 추적, 일일/월간 비용 집계

### 대시보드

Grafana는 다음 대시보드를 제공합니다:

- **Trading Overview**: 거래 활동 및 성과 요약
- **System Performance**: 시스템 리소스 사용 현황
- **API Monitoring**: GLM API 호출 및 비용 추적

## 비용 관리

GLM API 사용 비용을 효율적으로 관리하기 위한 최적화 기능이 포함되어 있습니다.

### 비용 최적화 전략

1. **캐싱 최적화**
   - Redis를 활용한 응답 캐싱
   - 반복 조회 최소화로 API 호출 감소

2. **배치 처리**
   - 여러 요청을 단일 배치로 처리
   - 토큰 사용량 최적화

3. **메트릭 수집**
   - 실시간 비용 추적
   - 예산 알림 설정

### 비용 모니터링

Prometheus/Grafana를 통해 다음 비용 관련 메트릭을 모니터링할 수 있습니다:

- 일일 API 호출 횟수
- 토큰 사용량 (입력/출력)
- 추정 비용 (원화 기준)
- 비용 추세 및 예측

### 예산 설정

`.env` 파일에서 비용 관련 설정을 구성할 수 있습니다:

```bash
# 일일 최대 비용 (KRW)
DAILY_COST_LIMIT=10000

# 비용 알림 임계값 (KRW)
COST_ALERT_THRESHOLD=8000

# 알림 수신 설정
ALERT_EMAIL=your-email@example.com
ALERT_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

## 알림 설정

AlertManager를 통한 다양한 알림 채널을 지원합니다.

### 지원 알림 채널

- **Webhook**: 애플리케이션으로 직접 알림 전송
- **Email**: 이메일 알림 (선택 사항)
- **Slack**: Slack 메시지 (선택 사항)

### 알림 규칙

`monitoring/alerting/rules.yml`에서 알림 규칙을 구성할 수 있습니다:

- **API 비용 알림**: 일일/월간 비용 임계값 초과 시
- **거래 실패 알림**: 연속 실패 횟수 임계값 초과 시
- **시스템 리소스 알림**: CPU/메모리 사용량 임계값 초과 시
- **API 응답 시간 알림**: 응답 시간 지연 시

### 알림 설정

1. `monitoring/alertmanager.yml`에서 알림 수신자 설정
2. Email/Slack Webhook URL 구성
3. 알림 규칙 및 임계값 조정
4. AlertManager 재시작으로 설정 적용

```bash
# AlertManager 재시작
docker-compose restart alertmanager
```

### 알림 테스트

```bash
# 테스트 알림 전송
curl -X POST http://localhost:8000/alerts/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Test alert"}'
```

## 추후 계획
- 빗썸, 바이낸스, 코인베이스, OKX, 바이비트도 가능하면 다루겠음
