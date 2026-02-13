# 🪙 Crypto Auto Trading Agent

> **Upbit 기반 암호화폐 자동매매 에이전트 (인프라 / 모의 거래)**  
> RSI + 이동평균 교차(MA Crossover) 복합 전략

---

## 📁 프로젝트 구조

```
crypto_agent/
├── config.py        # API 키, 전략 파라미터, 경로 설정
├── market_data.py   # Upbit 공개 API 시세 데이터 수집
├── strategy.py      # RSI + MA 교차 전략 (신호 생성)
├── portfolio.py     # 포트폴리오 추적, P&L 계산
├── main.py          # 오케스트레이터 (진입점)
├── data/
│   └── portfolio.json   # 포트폴리오 상태 영속 저장
└── logs/
    └── agent_YYYYMMDD.log
```

---

## ⚙️ 설치 및 설정

### 1. 의존성 설치
```bash
pip install requests pandas numpy
```

### 2. API 키 설정 (선택 — 공개 API는 불필요)
실제 주문 시 필요. 환경변수로 주입:
```bash
export UPBIT_ACCESS_KEY="your_access_key"
export UPBIT_SECRET_KEY="your_secret_key"
```

또는 `config.py`에서 직접 수정.

---

## 🚀 실행 방법

### 신호 관찰 (Dry-Run, 기본값)
```bash
python main.py
```

### 모의 거래 (Paper Trading)
```bash
python main.py --paper
```

### 루프 모드 (60초마다 반복)
```bash
python main.py --loop --paper
```

### 각 모듈 단독 테스트
```bash
python market_data.py   # API 연결 및 BTC 데이터 확인
python strategy.py      # 신호 생성 테스트
python portfolio.py     # 포트폴리오 현황
```

---

## 📈 전략 설명: RSI + 이동평균 교차

### 핵심 지표

| 지표 | 설명 | 기본값 |
|------|------|--------|
| **RSI** (Relative Strength Index) | 가격 변동의 과매수/과매도 판단 | 14일 |
| **MA Short** | 단기 이동평균 | 5일 |
| **MA Long** | 장기 이동평균 | 20일 |

### 매수 조건 (BUY)
```
✅ 골든크로스: MA5 > MA20 (단기가 장기를 상향 돌파)
   + RSI < 70 (과매수 아닐 것)
   
   강력 매수:
✅ 골든크로스 + RSI < 30 (과매도 구간 진입 = 더 좋은 진입점)
```

### 매도 조건 (SELL)
```
🔴 데드크로스: MA5 < MA20 (단기가 장기를 하향 돌파)
🔴 RSI > 70    (과매수 구간 — 단독으로도 매도)
🔴 손절: 평균매수가 대비 -5% 이하
🔴 익절: 평균매수가 대비 +15% 이상
```

### 전략 직관적 해석

```
    가격
     │        ┌──────── MA5 (빠른 선)
     │    ↗골든크로스    
     │───────────────── MA20 (느린 선)
     │
     └──────────────────────────▶ 시간
     
     RSI:  0 ────[30 과매도]────[50 중립]────[70 과매수]──── 100
```

- **골든 크로스**: 단기 평균이 장기 평균을 돌파 → 상승 추세 시작 신호
- **데드 크로스**: 단기 평균이 장기 평균 아래로 → 하락 추세 신호
- **RSI**: 크로스 신호의 과매수/과매도 필터 역할 (노이즈 감소)

---

## 💰 리스크 관리

| 항목 | 기본값 |
|------|--------|
| 투자 비율 | 가용자금의 95% |
| 코인당 최대 투자 | 총 자산의 30% |
| 손절 | -5% |
| 익절 | +15% |
| 수수료 | 0.05% (Upbit 기본) |

---

## 🗺️ 로드맵

- [x] Upbit 공개 API 연동 (시세, 캔들)
- [x] RSI + MA 교차 전략
- [x] 모의 포트폴리오 (Paper Trading)
- [x] 손절/익절 자동화
- [ ] Upbit 인증 API (실제 주문)
- [ ] 텔레그램 알림 연동
- [ ] 백테스팅 모듈
- [ ] 다중 전략 (볼린저 밴드, MACD)
- [ ] 웹 대시보드

---

## ⚠️ 주의사항

> 이 코드는 **교육/연구 목적**이며, 실제 투자 손실에 대해 책임지지 않습니다.  
> 암호화폐 투자는 원금 손실 위험이 있습니다.

---

*Inspired by [KIS_AUTO](../KIS_AUTO) & [Creon_Auto](../Creon_Auto) projects*
