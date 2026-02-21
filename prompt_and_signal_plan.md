# 프롬프트 제어 + 다중 지표(Multi-Signal) 라우팅 결합 전략

현재 `main.py`에 적용된 v2.2 전략(파라미터 튜닝 + `_should_fallback` 게이트)은 매우 견고한 구조를 갖추고 있습니다. 특히 `confidence_threshold=0.0`, `temperature=0.2` 등을 통해 로컬 모델의 가능성을 최대한 열어둔 점이 훌륭합니다.

하지만, 모델의 기반 지시어(System Prompt)가 여전히 `"You are a helpful assistant..."`로 유지되고 있어, 로컬 모델이 대화형 응답을 시도하다 빈 리스트(`[]`)를 반환하는 고질적인 문제는 완전히 해결되지 않았습니다. 

따라서 점수 극대화(Total Score > 60%)를 달성하기 위한 최종 계획은 다음과 같습니다.

## 1. 강력한 프롬프트 주입 (Strict Prompt Engineering)

대화형 거부(Refusal)로 인한 낭비를 막고 강제로 툴 구조를 예측하게 만드는 프롬프트를 기존 코드에 결합합니다.

*   **수정 대상**: `_generate_cactus_tuned` 내부의 `cactus_complete` 호출
*   **기존**: `[{"role": "system", "content": "You are a helpful assistant that can use tools."}]`
*   **변경**: `[{"role": "system", "content": "You are a strict, logic-only function routing engine. You MUST output a tool call to fulfill the user's request. NEVER ask for clarification. NEVER output conversational text. Always select the most appropriate tool from the provided list."}]`
*   **기대 효과**: On-device 비율 내의 F1 스코어 상승, 빈 리스트(`[]`) 반환율 급감.

## 2. 숨겨진 로컬 출력물(Cactus Metadata) 추출 및 활용

현재 `_generate_cactus_tuned`는 `function_calls`, `total_time_ms`, `confidence` 세 가지만 추출하고 있습니다. 하지만 `cactus_complete`가 내부적으로 던져주는 강력한 추가 지표(Signals)들이 있습니다. 이를 모두 수집하여 라우팅 결정에 활용해야 합니다.

*   **추가 수집 지표**:
    *   `cloud_handoff`: 로컬 모델 자체가 '이 도구는 내 영역이 아니다'라고 판단한 부울(boolean) 값.
    *   `success`: Cactus 내부 생성 파이프라인의 성공 여부 (예: 토큰 초과 시 등).
    *   `prefill_tokens`: 입력된 프롬프트와 툴 전체의 길이. (길수록 복잡도 높음)
    *   `decode_tokens`: 생성된 텍스트의 토큰 수. (과도하게 짧으면 비정상 의심)

## 3. 다중 지표(Multi-Signal) 기반의 Risk Score 도입 (`_should_fallback` 수정)

기존 v2.2의 훌륭한 8단계 게이트 로직(Gate 1~8)을 유지하되, 일부 하드코딩된 조건(예: `len(tools) >= 3 and local_conf < 0.75`)을 **Cactus 내부 지표**로 훨씬 더 정교하게 수정합니다.

*   **우선순위 1순위 (즉시 Fallback)**:
    *   `cloud_handoff == True` 이거나 `success == False`인 경우 무조건 Cloud.
*   **우선순위 2순위 (토큰 복잡도 리스크 가중치)**:
    *   `prefill_tokens`가 아주 높고(예: >500) `decode_tokens`가 매우 적게(예: <20) 반환되었음에도 빈 콜(`[]`)이 아니라 엉뚱한 값 하나만 내뱉었다면 클라우드로 우회.
*   **우선순위 3순위 (동적 Confidence 검증)**:
    *   `local_conf`가 낮아도 구조 결함이 없는 단일 액션(`is_multi_action_request() == False` 이고 `len(tools) == 1`)이라면 클라우드로 보내지 말고 그대로 On-device로 유지.

## 4. 최종 실행 계획 (Action Items)

1. **Step 1**: `main.py`의 `_generate_cactus_tuned` 부분에서 시스템 프롬프트를 교체하고 추가 메타데이터(`cloud_handoff`, `prefill_tokens` 등)를 리턴 딕셔너리에 포함시키도록 수정.
2. **Step 2**: `_should_fallback` 최상단에 `cloud_handoff`와 `success`를 방어하는 Gate 0 조건을 추가. 
3. **Step 3**: 로컬 벤치마크 실행 후, 생성된 로그 파일(예: `benchmark_runs/`)을 분석하여 F1 유지 및 On-device 상승 목표치(25~35%) 도달 여부 확인.
