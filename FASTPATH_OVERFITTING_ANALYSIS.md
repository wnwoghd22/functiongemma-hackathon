# Fastpath v1 과적합 분석 (91.0%)

> 기준: `benchmark_runs/benchmark_20260222_084801.md`
> 전략: `strategies/strategy_fastpath_v1.py` + fallback `strategy_final_ensemble_v1.py`

---

## 1. 구조 요약

```
generate_hybrid(messages, tools)
  ├─ _try_fastpath(): 단일 의도 → 모델 스킵, regex만으로 응답 (0ms)
  └─ fallback → strategy_final_ensemble_v1 (3-pass 앙상블)
```

### Fastpath 조건 (L95~118)
1. 키워드로 도구 1개 확정 (`_detect_expected_tools`)
2. `len(expected) != 1`이면 포기
3. `_is_multi_action` 또는 쉼표 있으면 포기
4. `core._extract_args_for_tool`로 regex 추출
5. `_required_valid`로 필수 인자 충족 확인
6. 통과 → **cactus 호출 없이 즉시 리턴** (0.01~0.25ms)

### Fallback: `strategy_final_ensemble_v1`
- Pass 1: `main.generate_hybrid` (원본 정책)
- Pass 2: 정규화된 메시지로 재시도 (quarter past, shoot 등 alias 변환)
- Pass 3: strict on-device recovery (quality_score < 90일 때만)
- 최고 품질 결과 선택 (`_choose_better`)

---

## 2. 91% 점수 분해

```
easy:   F1=1.00  time=0.11ms  time_score=1.00
        level = 0.60×1.0 + 0.15×1.0 + 0.25×1.0 = 1.000  × 0.20 = 0.200

medium: F1=1.00  time=0.03ms  time_score=1.00
        level = 0.60×1.0 + 0.15×1.0 + 0.25×1.0 = 1.000  × 0.30 = 0.300

hard:   F1=0.95  time=2227ms  time_score=0
        level = 0.60×0.95 + 0.15×0 + 0.25×1.0 = 0.820  × 0.50 = 0.410

Total = 0.200 + 0.300 + 0.410 = 0.910 → 91.0%
```

easy+medium의 `time_score=1.0`이 **+5.0p** 기여함.

---

## 3. 과적합 위험 평가

| 항목 | 위험도 | 근거 |
|---|---|---|
| **키워드 매핑 고정** | 🔴 높음 | 7개 도구의 키워드 하드코딩. Hidden eval이 다른 표현 쓰면 `expected=∅` → fastpath 실패 |
| **fallback 시간** | 🟡 중간 | fastpath miss시 ensemble 3-pass → 2~5초, time_score=0으로 복귀 |
| **regex 정확도** | 🔴 높음 | `_extract_args_for_tool`이 비표준 표현 파싱 실패 → `_required_valid=False` → fastpath 포기 |
| **단일 의도 판정** | 🟡 중간 | 키워드 겹침 표현에서 오탐 가능 |
| **fallback 품질** | 🟢 낮음 | ensemble 3-pass는 자체적으로 robust하므로 최악의 경우에도 F1 유지 |

### 키워드 취약 사례

| 공개 벤치 표현 | Hidden eval 가능 표현 | fastpath |
|---|---|---|
| `"Play Bohemian Rhapsody"` | `"Put on some tunes"` | ❌ miss (`play ` 키워드 없음) |
| `"Set alarm for 6 AM"` | `"Wake me at 6 in the morning"` | ✅ hit (`wake me` 매핑 있음) |
| `"What's the weather in SF"` | `"How's it outside in SF"` | ❌ miss → `normalize`로 복구 가능 |
| `"Text Alice saying hi"` | `"Shoot Alice a quick text"` | ❌ miss (`shoot ` 키워드 없음) |
| `"Set timer for 5 minutes"` | `"Countdown for half an hour"` | ✅ hit (`countdown` 매핑 있음) |

---

## 4. 서버 점수 시뮬레이션

| Fastpath hit율 | Easy time | Medium time | 예상 서버 점수 |
|---:|---:|---:|---:|
| 100% (=로컬) | 0.1ms | 0.03ms | **91.0%** |
| 80% | ~128ms | ~200ms | **~89%** |
| 60% | ~256ms | ~410ms | **~86%** |
| 40% | ~384ms | ~615ms | **~83%** |
| 0% (모두 fallback) | ~640ms | ~1025ms | **~80%** |

> hit율이 10% 떨어질 때마다 약 **-1.1p**.

---

## 5. 서버 점수 추정

### 낙관적 시나리오 (hit율 70~80%)
- 서버에서도 easy/medium의 대부분이 표준 표현을 사용
- **~87~89%** 기대

### 보수적 시나리오 (hit율 40~50%)
- Hidden eval이 다양한 표현 사용
- **~83~85%** 기대

### 비관적 시나리오 (hit율 < 30%)
- 대부분 비표준 → fastpath 거의 무의미
- **~81%** (현재 main.py 수준으로 수렴)

---

## 6. 결론 및 권장사항

### 장점
- 시간 보너스 +5p는 **매우 큰 이득** (현재 유일한 time_score 소스)
- fallback이 robust해서 **worst case에도 80% 유지** (안전장치)
- easy/medium 단일 의도 판정 자체는 합리적

### 과적합 요인
- 키워드 테이블이 공개 벤치 표현에 최적화
- fastpath miss시 time_score 급락 (0ms → 2000ms+ 갭)
- regex가 비표준 표현을 못 잡으면 `_required_valid` 실패

### 개선 방향 (과적합 줄이기)
1. **키워드 테이블 확장**: `"put on"`, `"tunes"`, `"jam"` 등 추가
2. **정규화를 fastpath에서도 적용**: 이미 `base._normalize_user_text` 호출 중 ✅
3. **fallback 시간 최적화**: ensemble 3-pass → max_tokens 줄이기, 불필요한 패스 스킵
4. **hard 케이스에도 제한적 fastpath**: multi-action 중 각 sub-request에 fastpath 적용 가능

### 제출 판단 기준
- **제출할 만함**: fallback 안전장치가 있어 81.3% 이하로 떨어지기 어려움
- **핵심 불확실성**: fastpath hit율에 따라 85~91% 범위가 넓음
- **권장**: 키워드 확장 후 paraphrase 테스트 → hit율 70% 이상 확보 후 제출
