# 비트코인 GPT 인공지능 AI 업비트 자동매매 시스템 만들기
- GPT API를 활용하여 투자를 자동화 합니다. by 유튜버 조코딩

## 🆕 신규 기능 (v5.0)
- ✅ **거래 서비스**: TradingService 기반 실거래 실행
- ✅ **보안 강화**: 2FA PIN 인증 및 거래 한도 시스템
- ✅ **거래 내역 기능**: FIFO 기반 손익 계산 및 거래 기록 보관
- ✅ **CLI 통합**: 명령행 인터페이스 실거래 지원
- ✅ **사용자 프로필**: 개인화 설정 및 알림 선호 관리
- ✅ **알림 시스템**: 이메일 및 인앱 알림 지원
- ✅ **테스트넷 환경**: 실제 자금 없이 거래 전략 테스트 가능
- ✅ **API 속도 제한**: Token Bucket 및 Circuit Breaker로 안정적인 API 호출
- ✅ **백업 및 복원**: 전체 데이터 백업/복구 및 자동 백업 스케줄링
- ✅ **포트폴리오 분석**: 실시간 자산 현황, 성과 지표 및 차트 시각화
- ✅ **듀얼 AI 프로바이더**: GLM-5 (1차) + OpenAI (폴백) 자동 전환 시스템

## 🤖 듀얼 AI 프로바이더 시스템
GLM-5와 OpenAI 간의 듀얼 프로바이더 아키텍처로 비용 절감과 안정성을 모두 확보했습니다.

### 특징
- **자동 폴백**: GLM-5 실패 시 OpenAI로 자동 전환
- **프로바이더 상태 추적**: 연속 실패 감지 및 복구 관리
- **지수 백오프 재시도**: 안정적인 API 호출 보장
- **비용 절감**: GLM-5 1차 사용으로 60-70% 비용 절감

### 환경 변수 설정
```bash
# .env 파일에 설정
GLM_API_KEY=your_glm_api_key_here        # 1차 프로바이더
GLM_API_BASE=https://api.z.ai/api/coding/paas/v4/
OPENAI_API_KEY=your_openai_api_key_here  # 폴백 프로바이더
AI_PROVIDER=auto                          # "glm", "openai", "auto"
AI_TIMEOUT=30                             # API 호출 타임아웃 (초)
```

### 사용법
```python
from gpt_bitcoin.infrastructure.external.ai_client_factory import get_ai_client, get_default_model

# 자동 프로바이더 선택으로 클라이언트 생성
client = get_ai_client()

# API 호출
response = client.chat.completions.create(
    model=get_default_model(),
    messages=[{"role": "user", "content": "분석해줘"}]
)
```

## 주요 특징
- 🏗️ **아키텍처**: 도메인 중심 설계 (DDD) + 테스트 주개발 (TDD)
- 🔒 **보안**: 인증된 거래 실행 및 감사 로깅
- 📊 **실시간 추적**: 거래 내역과 수익률 분석
- 🧪 **안전한 테스트**: 테스트넷 환경으로 전략 검증

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

## 🛡️ 보안 기능
### SecurityService (SecurityService)
- PIN 기반 2FA 인증 시스템
- 거래 한도 설정 및 검증
- 고액 거래 추가 확인 절차
- 감사 로깅 시스템 통합

### TradeHistoryService (TradeHistoryService)
- FIFO 기반 손익 계산
- 거래 내역 영구 저장
- 수익률 및 통계 분석
- 거래 이력 관리

### UserProfileService (UserProfileService)
- 사용자 프로필 관리
- 알림 설정 관리
- 이메일 유효성 검증
- SecurityService 연동 (감사 로그)

### NotificationService (NotificationService)
- 이메일 알림 발송
- 인앱 알림 지원
- Rate limiting (스팸 방지)
- 사용자 설정 준수

### CLI Integration (CLI 통합)
- TradingService 연동
- 인터랙티브 승인 프롬프트
- 수동 매수/매도 지원
- 시뮬레이션/실거래 모드

### Testnet Support (MockUpbitClient)
- 실제 자금 없이 거래 테스트
- 가상 잔액 시뮬레이션
- 전략 검증 및 안전한 개발
- 실제 API와 동일한 인터페이스

## ⚙️ 환경 설정
### .env 파일 생성 및 설정
```
# AI 모델 API 키
OPENAI_API_KEY="YourOpenAIKey"
ZHIPUAI_API_KEY="YourZhipuAIKey"

# 업비트 API 키
UPBIT_ACCESS_KEY="YourUpbitAccessKey"
UPBIT_SECRET_KEY="YourUpbitSecretKey"

# 뉴스 데이터 API 키
SERPAPI_API_KEY="YourSerpApiKey"

# 테스트넷 모드 (true: 테스트, false: 실거래)
TESTNET_MODE=false
```

## 📁 프로젝트 구조
```
src/gpt_bitcoin/
├── domain/                # 도메인 모델 (DDD 아키텍처)
│   ├── audit.py          # 감사 로깅 기록
│   ├── security.py       # 보안 서비스 (2FA, 거래 한도)
│   ├── testnet_config.py # 테스트넷 설정
│   ├── trade_history.py  # 거래 내역 관리
│   ├── trading.py        # 거래 서비스 (주요)
│   ├── trading_mode.py   # 거래 모드 설정
│   ├── trading_state.py  # 거래 상태 관리
│   ├── user_profile.py   # 사용자 프로필 관리
│   ├── notification.py   # 알림 시스템
│   ├── backup.py         # 백업 및 복원 서비스
│   └── analytics.py      # 포트폴리오 분석 서비스
├── infrastructure/       # 인프라 계층
│   ├── external/         # 외부 API 연동
│   ├── persistence/      # 데이터 저장소
│   ├── observability/    # 모니터링 및 추적
│   ├── resilience/       # 회복탄력 (Circuit Breaker, Retry)
│   ├── rate_limiting/    # API 속도 제한
│   └── backup/           # 백업 관리자
├── application/          # 애플리케이션 서비스
├── dependencies/         # 의존성 주입 컨테이너
└── config/               # 설정 관리
```

## 로컬 환경 설정
```
pip install -r requirements.txt
```

## 🧪 테스트 및 개발
### 테스트 실행
```bash
# 모든 테스트 실행 (745개 테스트, 100% 통과)
python -m pytest tests/ -v

# 커버리지 확인
python -m pytest tests/ --cov=src/gpt_bitcoin --cov-report=term-missing

# 특정 도메인 테스트
python -m pytest tests/unit/domain/test_trading.py -v
python -m pytest tests/unit/domain/test_user_profile.py -v
python -m pytest tests/unit/domain/test_notification.py -v

# CLI 트레이딩 테스트
python -m pytest tests/unit/test_cli_trading.py -v

# 테스트넷 모드 테스트
TESTNET_MODE=true python -m pytest tests/unit/infrastructure/test_mock_upbit_client.py
```

### 품질 검사
```bash
# 린터 실행
ruff check src/ --ignore E501

# 타입 체커 실행
mypy src/gpt_bitcoin/ --ignore-missing-imports
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

## 🚀 실행 방법
### 실거래 모드
```bash
# 실제 거래 실행
python main.py

# 보안 모드로 실행 (PIN 인증 필요)
python main.py --secure
```

### 테스트 모드
```bash
# 테스트넷에서 실행
TESTNET_MODE=true python main.py

# 테스트 실행
python -m pytest tests/unit/test_trading.py
```

### CLI 트레이딩
```bash
# CLI 인터페이스로 거래
python src/gpt_bitcoin/cli_trading.py --ticker KRW-BTC --amount 10000 --side buy
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
## 📋 SPEC 구현 현황
| SPEC ID | 설명 | 상태 |
|---------|------|------|
| SPEC-TRADING-001 | 거래 서비스 (TradingService) | ✅ 완료 |
| SPEC-TRADING-002 | 거래 내역 관리 (TradeHistory) | ✅ 완료 |
| SPEC-TRADING-003 | CLI 통합 | ✅ 완료 |
| SPEC-TRADING-004 | 보안 강화 (SecurityService) | ✅ 완료 |
| SPEC-TRADING-005 | 테스트넷 환경 (Testnet) | ✅ 완료 |
| SPEC-TRADING-006 | 사용자 프로필 관리 (UserProfile) | ✅ 완료 |
| SPEC-TRADING-007 | 알림 시스템 (Notification) | ✅ 완료 |
| SPEC-TRADING-008 | 포트폴리오 분석 대시보드 | ✅ 완료 |
| SPEC-TRADING-009 | API 속도 제한 (Rate Limiting) | ✅ 완료 |
| SPEC-TRADING-010 | 백업 및 복원 (Backup) | ✅ 완료 |

## 추후 계획
- 빗썸, 바이낸스, 코인베이스, OKX, 바이비트도 가능하면 다루겠음
