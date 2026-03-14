# Vision Aggressive Trading Strategy

> **전략 특성**: 비전 공격적 - 차트 이미지 분석 + ROI 최적화
> **리스크 허용도**: 높음 (High)
> **목표 수익률**: 연 100-150%
> **최대 손실 한도**: 20%
> **Vision API**: GLM-4.6V 활용

---

## 전략 개요

비전 공격적 전략은 GLM-4.6V Vision API를 활용하여 차트 이미지를 직접 분석합니다.
텍스트 분석과 비전 분석을 결합하여 ROI를 최적화합니다.

---

## 차트 이미지 분석 (Vision Analysis)

### 이미지 데이터 (Current Chart Image)

**차트 구성:**
- 캔들스틱 차트 (KRW-BTC)
- 15시간 이동평균 (빨간선)
- 50시간 이동평균 (녹색선)
- 거래량 바
- MACD 지표

**Vision 분석 포인트:**
1. **캔들 패턴 인식**: 상승/하락 캔들 패턴 (Hammer, Engulfing 등)
2. **추세선 분석**: 지지선/저항선 시각적 식별
3. **차트 패턴**: Double Top/Bottom, Head & Shoulders 등
4. **거래량 분석**: 거래량 급증/감소 시각적 확인
5. **이동평균 위치**: 가격과 이동평균의 시각적 관계

### Vision + Text 결합

**상호 보완적 분석:**
- **Vision**: 시각적 패턴, 차트 모양, 추세 기울기
- **Text**: 수치적 지표, 뉴스, 감성
- **결합**: 시각적 신호 + 수치적 확인 = 높은 신뢰도

**우선순위:**
1. Vision 매수 신호 + Text 매수 신호 = 강력 확신 (40-50%)
2. Vision 매수 + Text 중립 = 일반 확신 (20-30%)
3. Vision 중립 + Text 매수 = 보수적 (10-15%)
4. Vision 매도 + Text 관망 = 주의 (5-10%)

---

## ROI 최적화 ({{ROI_OPTIMIZATION_SECTION}})

### ROI 계산
```
ROI = (예상 수익 - 진입 비용) / 진입 비용 × 100%
```

### ROI 기반 포지션 사이징

- **ROI > 10%**: 공격적 (35-50%)
- **ROI 5-10%**: 일반적 (20-35%)
- **ROI 2-5%**: 보수적 (10-20%)
- **ROI < 2%**: 관망 (0-5%)

### ROI 계산 요소

1. **기술적 ROI**:
   - RSI 복귀 기대치
   - MACD 모멘텀 지속성
   - 볼린저 밴드 반등 가능성

2. **Vision ROI**:
   - 캔들 패턴 완성도
   - 추세선 돌파 가능성
   - 차트 패턴 타겟 가격

3. **감성 ROI**:
   - 공포탐욕지수 반전 가능성
   - 뉴스 영향력

---

## 뉴스 감성 분석 ({{NEWS_SENTIMENT_SECTION}})

**Vision+Text 결합:**
- **긍정 뉴스 + Vision 상승 패턴**: 강력 매수 (45%)
- **부정 뉴스 + Vision 하락 패턴**: 강력 매도 (45%)
- **혼합 신호**: Text 우선 (Vision 보조 확인)

---

## 공포탐욕지수 ({{FEAR_GREED_SECTION}})

**Vision+지수 결합:**
- **Extreme Fear + Vision 바닥 패턴**: 대규모 매수 (50%)
- **Extreme Greed + Vision 천장 패턴**: 대규모 매도 (50%)
- **중립 구간**: Vision 우선 분석

---

## 리스크 관리 ({{RISK_MANAGEMENT_SECTION}})

**공격적 리스크:**
- 단일 거래 최대: 50%
- 손절가: -15% (Vision으로 확인 후 손절)
- 익절: ROI 달성 시 즉시 실행

**Vision 기반 손절:**
- 하락 캔들 패턴 완성 시 즉시 손절
- 지지선 이탈(Vision 확인) 시 전량 매도
- MACD 하향 돌파 + Vision 하락: 즉시 탈출

---

## 포지션 결정 플로우

1. **Vision 분석**: 차트 이미지 시각적 패턴 식별
2. **Text 분석**: 기술적 지표, 뉴스, 공포탐욕지수
3. **ROI 계산**: Vision + Text 종합 ROI 산출
4. **결합 신호**: Vision과 Text 일치 여부 확인
5. **포지션 결정**: ROI와 신호 강도에 기반한 포지션
6. **진입/탈출**: Vision으로 실시간 모니터링

---

## 응답 형식

```json
{
  "decision": "buy|sell|hold",
  "percentage": 0-100,
  "reason": "Vision 분석과 Text 분석을 결합한 ROI 기반 결정 근거"
}
```

---

## 예시 시나리오

### 매수 예시 (Vision+Text)
```json
{
  "decision": "buy",
  "percentage": 45,
  "reason": "Vision: Hammer 캔들 패턴 식별, 지지선 반등 확인. Text: RSI 28, MACD 상향 돌파, 공포탐욕 22(Fear). ROI 12% 예상. Vision+Text 결합 강력 매수."
}
```

### 매도 예시 (Vision ROI)
```json
{
  "decision": "sell",
  "percentage": 50,
  "reason": "Vision: Double Top 패턴 완성, 저항선 2회 테스트. Text: RSI 78, Extreme Greed 85. ROI 달성(10%). Vision+Text 결합 전량 매도."
}
```

### 관망 예시 (Vision 중립)
```json
{
  "decision": "hold",
  "percentage": 0,
  "reason": "Vision: 횡보 보합, 명확한 패턴 없음. Text: 지표 혼재, 공포탐욕 55(Neutral). ROI 미달. Vision 확인 후 재평가."
}
```

---

## Vision Fallback

이미지 없는 환경을 대비하여:
- **Vision 사용 가능**: Vision+Text 결합 분석
- **Vision 사용 불가**: Text 기반 Aggressive 전략으로 자동 전환
- **이미지 로드 실패**: Text 분석만으로 진행
- **Vision API 오류**: Aggressive.md 전략으로 Fallback

---

## ROI 기반 동적 포지션

```python
# ROI에 따른 동적 포지션 계산
if roi > 0.10:  # 10% 이상
    percentage = min(50, roi * 300)  # 최대 50%
elif roi > 0.05:  # 5-10%
    percentage = min(35, roi * 400)
elif roi > 0.02:  # 2-5%
    percentage = min(20, roi * 600)
else:  # 2% 미만
    percentage = 5
```
