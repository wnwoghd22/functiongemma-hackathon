# 과적합(Overfitting) 분석 — strategy_targeted_v1.py

> 로컬 벤치 82.2% (74.4% → +7.8p) 달성. 서버 전이 가능성을 검토.

## 로컬 vs 서버 갭 기존 데이터
| 지표 | 로컬 (053740) | 서버 제출 | 갭 |
|---|---:|---:|---:|
| 총점 | 74.4% | 70.6% | **-3.8p** |
| F1 | 0.86 | 0.7933 | -0.067 |
| 평균 시간 | 1385ms | 3757ms | ×2.71 |

서버 시간이 2.7배 느려지므로 Time Score가 크게 하락함. F1도 약간 하락 (서버 벤치 케이스 차이).

---

## 변경사항별 과적합 위험도

### ✅ 안전 (일반화 가능)

| 변경 | 위험도 | 근거 |
|---|---|---|
| `H:MM AM/PM` 분 추출 우선순위 | 🟢 낮음 | 시간 포맷 파싱은 보편적 NLP 패턴 |
| `set_timer.minutes` dict 평탄화 | 🟢 낮음 | 모델 hallucination 방어, 입력 무관 |
| `abs(int)` 정수 정규화 | 🟢 낮음 | 음수 시간은 항상 틀림 |
| JSON repair | 🟢 낮음 | 구조적 출력 오류 교정 |
| `search_contacts.query` 타입 보호 | 🟢 낮음 | string 강제는 schema 준수 |

### ⚠️ 주의 필요

| 변경 | 위험도 | 근거 |
|---|---|---|
| `remind` 키워드 → `create_reminder` 부스트 | 🟡 중간 | cactus 실패 시 fallback에서만 사용되므로 직접적 위험은 낮음. 다만 `"remind me to play music"` 같은 경우 오선택 가능 |
| `,\s+` 메시지 구분자 추가 | 🟡 중간 | multi-action split 후에는 sub-request에 쉼표가 거의 없어 실질 위험 낮음. 메시지 본문에 쉼표 포함 시 잘림 가능 |

### 🔴 높은 위험

| 변경 | 위험도 | 근거 |
|---|---|---|
| **ALWAYS re-extract** (규칙 기반 arg 항상 덮어쓰기) | 🔴 높음 | 아래 상세 분석 참조 |

---

## 🔴 핵심 위험: ALWAYS re-extract

### 변경 내용
```python
# 이전 (main.py): 빈 args일 때만 재추출
if not args and name:
    args = _extract_args_for_tool(name, user_text, {})

# 수정 (targeted_v1): 항상 재추출
args = _extract_args_for_tool(name, user_text, args)
```

### 로컬에서 효과가 큰 이유
- 로컬 벤치 30개 케이스는 모두 정형화된 영어 문장
- regex 패턴이 30개 케이스를 거의 100% 커버
- 모델이 `minute: 0`으로 잘못 추출한 것을 regex가 교정 → +7.8p

### 서버에서 역효과 시나리오
```
서버 벤치 예상 입력: "Wake me at quarter past eight"
→ regex: _extract_time_hours_minutes() 실패 (패턴 없음)
→ return {"hour": 0, "minute": 0}  ← 모델이 준 정확한 값을 덮어씀!
```

또는:
```
서버 벤치 예상 입력: "Play the latest Taylor Swift album"
→ regex: _extract_song() → "latest Taylor Swift album"
→ 서버 기대값이 "Taylor Swift" 또는 다른 포맷이면 불일치
```

### 위험 정량 추정
- 로컬-서버 F1 갭이 기존 -0.067이었음
- ALWAYS re-extract로 regex 의존도가 높아지면 갭이 **-0.10~-0.15**로 확대 가능
- 82.2% 로컬 → 서버 **68~72%** 예상 (74.4% → 70.6% 비율 적용 시)

---

## 권장 대응

### Option A: 보수적 re-extract (추천)
```python
# 규칙이 모든 필드를 채웠을 때만 overwrite
rule_args = _extract_args_for_tool(name, user_text, {})
if rule_args and all(v for v in rule_args.values()):
    args = rule_args
elif not args:
    args = _extract_args_for_tool(name, user_text, args)
```
- 예상 로컬 점수: ~78-80% (82.2%보다 약간 하락)
- 예상 서버 전이: 더 안정적

### Option B: 현재 로직 유지 + 서버 제출 후 판단
- 82.2% 로컬 → 서버 제출 → 실제 갭 측정
- 갭이 크면 Option A로 전환

### Option C: 도구별 선택적 re-extract
```python
# 규칙이 강한 도구만 항상 re-extract
ALWAYS_REEXTRACT = {"set_alarm", "set_timer", "get_weather"}
if name in ALWAYS_REEXTRACT:
    args = _extract_args_for_tool(name, user_text, args)
elif not args:
    args = _extract_args_for_tool(name, user_text, args)
```
- `set_alarm` 분 추출, `set_timer` 평탄화 등 확실한 개선만 유지
- `send_message`, `play_music` 등은 모델 출력 존중

---

## 결론
- 5개 변경 중 4개는 일반화 안전
- **ALWAYS re-extract**가 유일한 고위험 과적합 지점
- Option C (도구별 선택적)가 가장 좋은 균형점으로 판단됨
