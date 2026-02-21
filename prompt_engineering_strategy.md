# 프롬프트 엔지니어링 전략 (Prompt Engineering Strategy)

이전의 최적화 시도들(`improvement_summary.md`, `routing_signal_guide.md`)에서 제안된 라우팅 시그널이나 복잡한 Fallback 로직들은 모두 가치가 있습니다. 하지만 **로컬 모델(FunctionGemma)이 아예 Function Call을 뱉어내지 않는 현상(Empty Call)** 이 압도적인 빈도로 발생하고 있기 때문에, 이를 먼저 해결하지 않으면 어떤 라우팅 규칙을 사용하든 결국 클라우드로 향하게 됩니다.

따라서 최우선 과제는 `main.py` 내부의 `generate_cactus` 함수에서 모델에 주입되는 **시스템 프롬프트(System Prompt)를 강력하게 통제**하여 로컬 F1 점수와 온디바이스 비율(On-device Ratio)을 동시에 끌어올리는 것입니다.

## 1. 현재 프롬프트의 문제점

현재 `main.py`에 작성된 시스템 프롬프트는 다음과 같습니다.
```python
[{"role": "system", "content": "You are a helpful assistant that can use tools."}] + messages
```
- **문제점**: 270M 파라미터 수준의 소형 모델에게 "도움이 되는 어시스턴트(helpful assistant)"라는 페르소나를 부여하면, 툴을 호출하기보다 **사용자에게 되묻거나(clarification) 대화형 응답(conversational response)을 시도**하려는 경향이 강해집니다.
- 그 결과 모델은 내부적으로 툴을 사용하지 않기로 결정하고 빈 리스트(`[]`)를 반환하게 됩니다.

## 2. 프롬프트 개선 방향 (System Prompt Engineering)

소형 모델은 추상적인 지시보다 **기계적이고 단호한(Strict & Robotic) 지시**에 훨씬 더 잘 따릅니다. 사용자와 대화하는 행위를 원천 차단하고 오직 JSON 형태의 도구 호출(Tool Call)만 출력해야 한다는 점을 강제해야 합니다.

### 제안하는 시스템 프롬프트 (예시)
```json
{
    "role": "system",
    "content": "You are a strict, logic-only function routing engine. You MUST output a tool call to fulfill the user's request. NEVER ask for clarification. NEVER output conversational text. Always select the most appropriate tool from the provided list."
}
```

### 적용 포인트
1. **페르소나 변경**: "어시스턴트"가 아니라 "함수 라우팅 엔진"으로 정의.
2. **부정 명령(Negative Constraints)**: 대화형 텍스트 생성 및 되묻기를 절대 하지 말 것(`NEVER`).
3. **강제성(Must)**: 반드시 제공된 도구 중 하나를 선택해 출력할 것.

## 3. Tool Description 최적화 (보조 수단)

만약 강력한 시스템 프롬프트를 적용했음에도 특정 도구를 잘 호출하지 못한다면, `generate_cactus` 내부에서 호춣하기 직전에 `tools` 딕셔너리의 `description` 항목을 조작(Enhancement)하여 모델이 더 쉽게 이해할 수 있도록 형태를 바꿀 수 있습니다.

- 예: `"Get current weather for a location"` -> `"Triggers the weather API. Required context: Location. Use this when the user asks about rain, temperature, or weather."`

## 4. 기대 효과 및 다음 진행 순서

1. **온디바이스 비율 파괴적 상승**: 빈 배열(`[]`)을 리턴하던 케이스들이 억제되면서 로컬 생성 모델이 강제로 툴 구조를 예측하게 됩니다. 이 상태에서 로컬 F1만 높아져도 라우팅(클라우드 Fallback) 횟수가 급감합니다.
2. **벤치마크 테스트 진행**: 프롬프트를 수정한 후 `benchmark.py`를 로컬에서 돌려 Empty Call 에러가 얼마나 줄어들었는지 수치적으로 확인합니다.
3. **사후 정규화(Post-processing) 결합**: 모델이 툴 호출은 성공했으나, 정규화되지 않은 텍스트(예: 대문자 누락, 구두점 에러)를 뱉는다면 이 부분만 가벼운 Python 코드(Regex)로 `main.py` 내에서 교정합니다.
4. **최종 라우팅 지표 적용**: 위의 두 조치로 베이스라인 F1을 최대한 확보한 뒤에, `routing_signal_guide.md`에서 제기된 `cloud_handoff`, `prefill_tokens` 등의 보조 지표를 사용해 "정말로 실패할 수밖에 없는 하드 태스크"만 선별해 클라우드로 보냅니다.

---
**요약**: 복잡한 룰 기반 라우팅 로직을 추가하기 전에, "빈 응답(Empty Call)" 자체를 원천 봉쇄하는 프롬프트 엔지니어링 튜닝을 제일 먼저 실행합니다.
