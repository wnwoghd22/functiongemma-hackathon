# High-Efficiency Improvements (Main.py 기준)

## 목적
- 오버피팅 없이 `main.py`의 점수 효율을 빠르게 올린다.
- 우선순위: **총점 상승 기여도/리스크 대비 효과**.

## 현재 전제
- `cloud fallback latch`(1회 실패 후 전체 cloud 비활성화)는 제거됨.
- sanitization은 경량(문자열 공백 trim + JSON leading zero 복구)으로 제한됨.
- 점수식: `0.60*F1 + 0.15*time + 0.25*on-device`.

---

## 우선순위 1: Cloud Function-Call 강제

### 아이디어
- Cloud 호출 시 `tool_config.function_calling_config.mode="ANY"`를 적용해 텍스트 응답/빈 응답 가능성을 줄인다.

### 기대 효과
- cloud fallback 케이스의 F1 안정화.
- medium/hard의 `0.0` 급락 케이스 감소.

### 구현 위치
- `_generate_cloud()` 내부 `types.GenerateContentConfig(...)` 구성 시 `tool_config` 추가.

### 리스크
- 낮음. API 파라미터 변경이며 오버피팅 요소 없음.

---

## 우선순위 2: 난이도 기반 Cloud 모델 분기

### 아이디어
- 단순 케이스 fallback: `gemini-2.5-flash-lite`
- 멀티 액션/고복잡도 fallback: `gemini-2.5-flash` 우선

### 판단 신호(범용)
- `_is_multi_action_request(messages)` 참
- `len(tools) >= 4`
- `prefill_tokens` 높음(예: 300+)

### 기대 효과
- hard(가중치 50%)에서 F1 개선.
- 전체 점수에 직접적 영향.

### 리스크
- 중간. hard에서 시간 증가 가능, 하지만 hard F1 이득이 더 클 가능성 큼.

---

## 우선순위 3: On-device 유지 전 의미 검증 게이트

### 아이디어
- 구조가 맞아도 값이 틀린 케이스를 cloud로 보내는 얕은 semantic gate 추가.
- 하드코딩이 아니라 **범용 규칙**만 사용.

### 후보 규칙
1. `set_alarm`에서 사용자 입력에 `:00`, `10 AM` 등 분 정보가 명시됐는데 예측 minute가 불일치하면 fallback.
2. 단일 의도(single intent)인데 tool name 불일치 시 fallback.
3. multi-action인데 call 수 부족 시 fallback(이미 있음, 유지 강화).

### 기대 효과
- on-device의 “그럴듯한 오답(고신뢰 오답)” 축소.
- 쉬운/중간 난이도 F1 손실 방지.

### 리스크
- 중간. 규칙이 과하면 cloud 비율 증가.

---

## 우선순위 4: Multi-action Cloud Under-call 1회 재시도

### 아이디어
- cloud 결과가 multi-action인데 call 1개만 반환되면 1회만 재시도.
- 재시도 모델은 상위 모델(`flash`) 우선.

### 기대 효과
- hard 복합 툴 시나리오에서 `0.5~0.67`를 `1.0`으로 끌어올릴 가능성.

### 리스크
- 중간. 지연 증가, 하지만 hard 가중치가 높아 채산성 있음.

---

## 추천 적용 순서 (빠른 사이클)
1. 우선순위 1 (Cloud function-call 강제)
2. 우선순위 2 (난이도 기반 모델 분기)
3. 벤치 1회
4. 우선순위 4 (under-call 재시도) 추가
5. 벤치 1회
6. 마지막으로 우선순위 3에서 가장 보수적인 규칙 1~2개만 추가

---

## 목표치 가이드
- 단기: `60%` 안정 재돌파
- 중기: `62~65%` 구간 진입
- 조건: hard 구간 F1 하락 없이 medium 오답 케이스를 줄일 것

