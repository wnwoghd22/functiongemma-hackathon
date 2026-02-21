# On-Device Output Sanitization 전략

## 개요

`generate_hybrid` 내부에서 on-device(FunctionGemma) 출력을 cloud fallback 판정 전에 후처리하여,
사소한 오류로 인한 불필요한 cloud 전환 또는 F1 손실을 방지한다.

**적용 범위**: `main.py`의 `generate_hybrid` 내부 로직 (README 허용 범위 내)
**금지 범위**: `benchmark.py` 채점 로직 변경, 케이스명 하드코딩

## on-device 실패 유형 전수 분석 (30건 실측)

### 유형별 분류

| 유형 | 건수 | sanitization | 설명 |
|------|------|-------------|------|
| A. 대화형 거부 | ~11건 | ✗ 불가 | call 자체가 없음. `"I apologize..."`, `"Could you please..."` |
| B. JSON parse fail | ~3-7건 | △ 일부 | leading zero, 깨진 escape 등 |
| C. argument 값 오류 | ~3건 | ○ 가능 | 음수값, 범위 초과 등 기계적 교정 |
| D. argument hallucination | ~2건 | ✗ 불가 | 모델이 내용을 창작 |
| E. multi-call 미달 | ~3건 | ✗ 불가 | 2개 기대, 1개만 생성 |
| F. 정상 성공 | ~8건 | — | 교정 불요 |

### 유형 B: JSON parse fail 상세

| 케이스 | 깨진 출력 | 수리 가능? |
|--------|----------|-----------|
| `alarm_10am` | `"minute":01` (leading zero) | **○** `re.sub(r':(\s*)0(\d+)', ...)` |
| `weather_paris` | `"location：<escape>Paris<escape>}"` | ✗ 구조적 깨짐 |
| `reminder_meeting` | `"title":}` (빈 값) | ✗ 값 자체가 없음 |
| `timer_music_reminder` | `"title：<escape>..."` | ✗ 전각 콜론 + escape |

**수리 가능: 1건** (leading zero만 기계적 수리 가능)

### 유형 C: argument 값 오류 상세

| 케이스 | expected | got | 교정 방법 |
|--------|----------|-----|----------|
| `timer_5min` | `minutes: 5` | `minutes: -5` | `abs(val)` |
| `timer_and_music` | `minutes: 20` | `minutes: -20` | `abs(val)` |
| `alarm_among_three` | `minute: 15` | `minute: 150` | 범위 교정 불가 (15 vs 150 판별 불능) |

**교정 가능: 2건** (음수 → 절대값)

## 구현할 sanitization

### 1. JSON raw string 수리 (parse fail 전)

```python
import re

def _repair_json(raw_str: str) -> str:
    """Fix common JSON issues from FunctionGemma output."""
    # Leading zero in integers: "minute":01 → "minute":1
    raw_str = re.sub(r':\s*0(\d+)([,}\]])', r':\1\2', raw_str)
    return raw_str
```

**효과**: `alarm_10am` parse fail 복구 → on-device call 생성 가능 (1건)

### 2. argument 값 sanitization (parse 후)

```python
def _sanitize_calls(calls):
    """Fix minor argument errors in on-device output."""
    for call in calls:
        args = call.get("arguments", {})
        for key, val in list(args.items()):
            # String whitespace trim
            if isinstance(val, str):
                args[key] = val.strip()
            # Negative time values → absolute
            if key in ("minutes", "seconds", "duration"):
                if isinstance(val, (int, float)) and not isinstance(val, bool) and val < 0:
                    args[key] = abs(int(val)) if isinstance(val, int) else abs(val)
    return calls
```

**효과**: `timer_5min`, `timer_and_music`의 음수 교정 (2건)

### 3. cloud 시스템 프롬프트 (sanitization은 아니지만 병행)

```python
system_instruction = (
    "Return only function calls. "
    "Copy argument values from the user request literally. "
    "Do not paraphrase or reformat."
)
```

**효과**: cloud fallback 시 argument 정확도 향상 (message, reminder 케이스)

## 기대 효과 시뮬레이션

### sanitization만 적용 (step 1-2)

| 구제 케이스 | 난이도 | F1 변화 | score 기여 |
|------------|--------|---------|-----------|
| `alarm_10am` (parse→성공) | easy | 0→1.0 | +0.60 × 0.1 × 0.20 = +0.012 |
| `timer_5min` (음수→양수) | easy | 0→1.0 | +0.60 × 0.1 × 0.20 = +0.012 |
| `timer_and_music` (음수→양수) | hard | 0→부분 | 불확실 (multi-call이라 1/2만 교정) |

**예상 score 개선: +0.3~0.5%p** (미미함)

### cloud 프롬프트까지 병행 (step 3)

prompt_signal_v1 실측에서 hard F1=1.00 달성 → cloud 정확도 안정화
**예상 score 개선: +1.0~2.0%p** (주요 효과)

### 합산

v2.1 baseline 60.9% → **62~63%** 기대

## 결론

sanitization은 **원칙적으로 올바른 접근이지만 효과는 제한적** (2-3건, +0.5%p).
on-device 실패의 대다수(11건 대화형 거부 + 3건 multi-call 미달)는 270M 모델의 구조적 한계이며,
후처리로 해결할 수 없다.

**score 개선의 주 동력은 cloud 프롬프트 최적화**이며, sanitization은 보조 수단으로 병행한다.
