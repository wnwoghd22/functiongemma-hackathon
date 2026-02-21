# 80점+ 서버 달성 구현 계획 (v2, Codex 비평 반영)

> 현재 최고 로컬: **80.4%** (strategy_targeted_v2, on-device 100%)
> 현재 서버 실측: **70.6%** (main.py 구버전 제출)
> 서버 갭: 로컬 대비 **-3.8p** (F1 -0.067, 시간 ×2.71)

---

## 점수 공식

```
level_score = 0.60×F1 + 0.15×time_score + 0.25×on_device
time_score  = max(0, 1 - avg_time/500)
난이도 가중치: easy 20%, medium 30%, hard 50%
```

서버 avg time ~3500ms → `time_score ≈ 0`. **F1 (60%)과 on-device (25%)에 집중**.

---

## 실행 순서 (Codex 권장 반영)

### Phase 1: 저위험 구조 수정 (먼저)

#### Step 1. `_is_multi_action` 쉼표 false positive 수정
- **예상 효과**: 단일 의도 케이스 복구 → +1~2p
- **위험도**: 🟢 낮음 (일반화 안전)
- **문제**: `text_lower.count(",") >= 1`이면 multi-action 판정
  - 정중한 표현 `"Set a timer for 5 minutes, please"` 등이 잘못 split
- **수정**: 쉼표 단독 판정 제거. `and`/`then` 등 접속사 마커 필수
- **`main.py`와 `strategy_targeted_v2.py` 모두 적용**

#### Step 2. 도구 이름 only dedup → dedup 제거 또는 (name, args) 기준
- **예상 효과**: 같은 도구의 복수 호출 보존 → +0.5~1p
- **위험도**: 🟢 낮음
- **문제**: `seen.add(name)`이 같은 도구의 다른 인자 호출을 유실
- **수정**: `generate_hybrid` 내 dedup 로직 변경

---

### Phase 2: defensive re-extract 핵심만 이식

#### Step 3. `_ALWAYS_REEXTRACT_TOOLS` + defensive override (신규분만)
- **예상 효과**: 서버 F1 +0.03~0.05 → +2~3p
- **위험도**: 🟡 중간 (범위 제한 필수)
- **이미 main.py에 있는 것**: H:MM 우선 파싱, nested dict 평탄화
- **신규 이식 대상**:
  - `set_alarm`, `set_timer`, `get_weather` → 항상 regex 우선
  - 기타 도구 → regex가 **모든 필드를 채웠을 때만** override
  - cactus가 non-empty args를 줬으면 존중 (과적합 방지)

---

### Phase 3: 정밀 cloud fallback (좁은 조건)

#### Step 4. 3건 실패 패턴만 cloud 시도
- **예상 효과**: F1 +0.03~0.05 → +1~2p
- **위험도**: 🟡 중간 (조건을 매우 좁게)
- **타겟**:
  - `remind` 키워드 + 모델이 `create_reminder` 미선택 + 4개 이상 도구
  - multi-action + alarm+reminder 조합 + 2번째 호출 실패
  - 모델이 도구 자체를 잘못 선택 (빈 호출 또는 무관한 도구)
- **제한**: easy/medium 정상 케이스는 절대 cloud로 보내지 않음

---

### Phase 4: 후순위

#### Step 5. cactus confidence 파싱 (P1.7)
- confidence=1.0 하드코딩 제거, 실제 값 파싱
- 단독 게이트 사용은 변동성이 크므로 보조 시그널로만 활용

#### Step 6. 서버 시간 최적화 (P2)
- `max_tokens` 256→128
- ROI가 작으므로 최후순위

---

## 남은 파일 구조

```
strategies/
├── strategy_targeted_v2.py           ← 최고 on-device (80.4%)
├── strategy_targeted_v2_cloud_combo.py ← v2 + cloud (82.2%)
└── __init__.py
```

## 예상 점수 (보수적)

| 단계 | 로컬 예상 | 서버 예상 |
|---|---:|---:|
| Phase 1 (Step 1+2) | ~81% | **75-77%** |
| + Phase 2 (Step 3) | ~82% | **77-79%** |
| + Phase 3 (Step 4) | ~83% | **78-81%** |
| 전체 (1~6) | ~83% | **78-81%** |

> **참고**: 상한 추정. 서버 변동성 고려 시, Phase 1+2 적용 후 제출 1~2회로 실측하고 Phase 3 판단 권장.
