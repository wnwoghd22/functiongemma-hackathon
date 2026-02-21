# FunctionGemma Hackathon: Final Strategy Summary & Conclusion

본 문서는 FunctionGemma 라우팅 최적화 해커톤 과정에서 발견한 문제점들과 이를 극복하기 위해 도입한 최종 하이브리드 전략(Score: 60.5%)의 핵심 요소를 정리한 최종 결론(Walkthrough) 문서입니다.

---

## 1. 초기 분석 파악 및 병목 지점 (The Bottlenecks)

1.  **채점 공식의 함정 (The Cloud Trap)**
    *   벤치마크 점수는 `(0.50 * F1) + (0.25 * Time_Score) + (0.25 * On_Device)` 로 구성됩니다.
    *   Time_Score는 500ms 부근에서 급감하여 클라우드(Gemini, 보통 1200ms) 호출 시 무조건 **0점**이 됩니다.
    *   결과적으로 클라우드를 사용하면 Time과 On-Device 비율 점수를 모두 버리게 되어, F1이 완벽하더라도 **이론 상 최대 60%** 언저리의 점수 벽에 갇히게 됩니다.
2.  **FunctionGemma-270M 모델의 한계점**
    *   **대화형 거부 (Empty Call Refusal)**: 복잡한 프롬프트가 들어오면 툴 콜링을 수행하지 않고 빈 리스트(`[]`)를 반환해 버립니다.
    *   **파라미터 환각 (Parameter Hallucination)**: 툴 구조는 완벽하게 맞췄음에도 숫자값(`minute: 59`)을 미세하게 틀리거나, 넘겨준 문자열 양 끝에 쓸데없는 구두점/공백(`" Alice. "`)을 붙이는 패턴이 자주 반복되어 전체 F1 점수를 망가뜨렸습니다.

---

## 2. 해결 과정 및 기각된 전략들

*   **하드코딩된 규칙 기반 라우팅 (v1)**: 특정 툴(`send_message`)이나 조건문을 정규식으로 직접 하드코딩하려 했으나, 이는 주최 측의 'Hidden Test Cases'에서 심각한 오버피팅을 유발할 위험성이 커 기각되었습니다.
*   **단순 하향 Confidence Threshold 조정**: 로컬 모델의 `confidence_threshold`를 일괄적으로 낮추면 모델이 빈 배열을 뱉는 횟수만 늘어나 F1과 전체 점수가 동반 하락했습니다.
*   **숫자 값(Integer) 직접 수정**: 모델이 틀린 숫자를 뱉어냈을 때 정규식으로 1단위 숫자(`:01 -> 1`) 정도를 살짝 고치는 건 안전하지만, 그 이상으로 값을 임의 보정(예: `59` -> `00`)하는 시도는 너무 위험하고 파괴적이어서 기각되었습니다.

---

## 3. 최종 도출된 하이브리드 전략 (The Non-Overfitting Solution)

위의 한계점들을 조합하여, **오버피팅(하드코딩 꼼수) 0%** 의 견고한 전략을 `main.py`에 구축했습니다. 다음 세 가지 핵심 요소가 결합되었습니다.

### A. 강력한 시스템 프롬프트 주입 (Strict Prompting)
```python
_LOCAL_SYSTEM_PROMPT = (
    "You are a strict function-calling router. "
    "Output only function calls, never conversational text."
)
```
"친절한 어시스턴트"가 아닌 "엄격한 라우터" 페르소나를 강제 주입하여, 로컬 모델이 대화체로 회피하며 빈 리스트(`[]`)를 뱉는 빈도를 획기적으로 낮췄습니다. (이론적 On-device 기회 창출 극대화)

### B. 다중 지표 기반 Risk Score (Merged Multi-Signals)
단일 `confidence` 수치에만 의존하던 기존의 불안정한 라우팅을 버리고, `cactus_complete`가 던져주는 내부 메타데이터를 활용했습니다.
*   **Gate 0**: `success == False` 이거나, 로컬 모델 스스로 어렵다고 판단한 `cloud_handoff == True`일 경우 즉각 클라우드로 Fallback 처리.
*   **Gate 7 (토큰 복잡도 검증)**: 사용자의 텍스트 길이가 매우 길거나(`prefill_tokens > 250`), 멀티-액션이 의심될 때 동적으로 요구 Confidence를 대폭 상향시켜(e.g., `< 0.75`), 아슬아슬하게 숫자를 틀릴 만한 복잡한 케이스들을 사전에 차단했습니다.

### C. 안전하고 방어적인 정제 (Defensive Normalization)
위협적이지 않은 수준에서 F1 스코어를 살리는 "클리닝" 함수(`_sanitize_function_calls`)를 모든 툴콜에 일괄 적용했습니다.
*   단순 문자열 양쪽 공백 및 가벼운 구두점 `. , ! ?` 제거
*   Integer 타입 기대값에 `bool`이나 `float(xx.0)`이 들어왔을 때의 안전한 캐스팅
*   음수 값(시간) 방어 (`abs()`)

---

## 4. 최종 결과치 요약

이 세 가지(프롬프트 + 멀티시그널 게이트 + 방어적 정규화)를 믹스한 `main.py`로 벤치마크를 수행한 최종 리포트입니다.

*   **Total Score**: `60.5%`
*   **On-device Ratio (로컬 모델 처치율)**: `27% (8/30)`
*   **Average Time**: `905ms`
*   **Overall F1**: `0.90`

**[결론]**
편법이나 특정 테스트 케이스(Baseline 30문제)에 종속된 하드코딩(Overfitting)을 일절 사용하지 않으면서도, 시스템 근본 로직(Prompting, Token tracking, Defensive normalization)의 교정만으로 60.5점이라는 해커톤 상위권에 도달 가능한 견고한 기반 코드를 완성했습니다. 이것으로 최종 제출을 진행하기 완벽한 상태입니다.
