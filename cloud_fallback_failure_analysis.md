# Cloud Fallback Failure Analysis

## 요약
- 리더보드 결과에서 `on-device=100%`, `F1≈on-device baseline` 패턴이 반복됨.
- 이는 hidden eval에서 cloud 경로가 사실상 매 케이스 실패하고, 예외 시 on-device로 degrade되는 흐름과 일치.
- 다른 팀은 cloud 비율이 0%~80%로 정상 분포를 보이므로, 서버 전체 장애보다는 **우리 코드 경로의 hidden 케이스 비호환** 가능성이 높음.

---

## 관측된 사실
1. 로컬 벤치:
- cloud fallback이 작동할 때 점수/정확도 상승.

2. hidden eval:
- `on-device=100%`
- 평균 지연이 낮고(`~200ms`) F1이 on-device-only 수준(`~0.24`)으로 수렴.

3. 현재 `main.py` 동작:
- cloud 실패 시 예외를 잡고 해당 케이스를 on-device 결과로 반환.
- 전역 latch(`_disable_cloud_fallback`)는 제거되어 있으나, 케이스별 실패가 반복되면 결과적으로 on-device 100%처럼 보일 수 있음.

---

## 유력 원인 (우선순위)

## 1) Cloud tool schema 변환의 hidden 비호환 (최우선 가설)
- 파일: `main.py:231` 근처
- 현재 변환은 `t["parameters"]["properties"]`를 단순 평면 구조로 가정.
- hidden eval tool schema가 nested object/array/enum/anyOf 등 복합 구조면 변환 단계에서 예외 또는 invalid schema가 발생할 수 있음.
- 공개 30개 벤치가 단순 스키마라 통과하고 hidden에서만 실패하는 패턴과 부합.

## 2) SDK 파라미터 호환성 문제
- 파일: `main.py:254`
- `GenerateContentConfig`에 전달하는 옵션(`system_instruction`, `candidate_count` 등)이 서버측 SDK 버전과 호환되지 않으면 런타임 예외 가능.
- 공개 벤치와 서버 실행 환경의 패키지 버전 차이가 있으면 hidden에서만 재현될 수 있음.

## 3) 인증/환경 변수 키 차이
- 현재 코드는 `GEMINI_API_KEY`만 직접 사용.
- 서버 환경이 `GOOGLE_API_KEY`만 보장하는 경우 API 키 누락으로 cloud 실패 가능.
- 다만 google-genai는 환경 fallback을 일부 지원하므로 단독 원인이라기보다는 보조 원인 가능성.

---

## 왜 “서버가 cloud를 못 써서”는 아닐 가능성이 높은가
- 상위 팀들의 on-device 비율이 0%/57%/67%/80%처럼 다양함.
- 이는 같은 리더보드 인프라에서 cloud 경로가 실제로 동작하는 제출이 존재함을 의미.
- 따라서 원인 범위는 서버 전체 장애보다 **우리 제출 코드의 cloud 호출 경로**에 집중하는 것이 합리적.

---

## 즉시 개선 권고
1. Tool schema 재귀 변환기 도입
- JSON Schema를 재귀로 `types.Schema`로 변환.
- unknown field는 보수적으로 drop하고 기본 타입 fallback 적용.

2. Cloud config 호환 fallback
- 1차: 고급 옵션 포함(`system_instruction`, strict config)
- 실패 시 2차: 최소 옵션(`tools`만)으로 재호출
- 실패 원인을 `cloud_error_type`, `cloud_error_msg`로 기록

3. API key fallback 강화
- `api_key = GEMINI_API_KEY or GOOGLE_API_KEY`로 명시 처리

4. Hidden-safe 방어
- `_generate_cloud` 내부 변환 단계/호출 단계를 분리 try/except
- 어떤 단계에서 실패했는지 reason code를 반환(`schema_build_error`, `api_call_error`, `parse_error`)

---

## 결론
- 현재 증거로는 “모델 버전 2.5 제한”보다, **hidden tool schema/환경 호환성으로 인한 cloud 경로 실패**가 더 유력.
- 다음 제출은 cloud 호출 안정화(스키마 변환 + 호환 fallback + 키 fallback)를 우선 적용해야 함.
