# Final Submission Scenario Matrix (2026-02-22)

## Current Known Baseline
- Last completed hidden result:
  - `score=70.7`, `f1=0.7744`, `on_device_pct=100.0`, `avg_time_ms=3691.39`
- Current submission:
  - `id=d2482dd4cd0e4ffabc1f55bdbf858f14`
  - status: `queued`

## Fast Decision Formula

Assume hidden eval usually has `avg_time_ms > 500`, so time term is often near 0.

- Score delta (approx):
  - `ΔScore ≈ 0.60*ΔF1 + 0.25*ΔOnDevice`
  - (`OnDevice` is 0~1 ratio)

Meaning:
- If on-device drops by 10% (`ΔOnDevice=-0.10`), you need about `ΔF1 > +0.0417` to break even.
- 20% drop -> need `+0.0833` F1.
- 30% drop -> need `+0.1250` F1.

## Core 2x2 Matrix

### 1) Cloud fallback 실행됨 + On-device 비율 상승/유지
- Interpretation:
  - 가장 이상적인 구간. cloud가 필요한 케이스만 건드렸을 가능성.
- Action:
  - 그대로 유지.
  - 다음 제출이 1회뿐이면 추가 수정 금지(파라미터 미세조정도 금지).

### 2) Cloud fallback 실행됨 + On-device 비율 하락
- Interpretation:
  - 정상적으로 흔한 패턴. 핵심은 F1 상승 폭이 on-device 손실을 상쇄하는지.
- Action:
  - 위 break-even 식으로 즉시 판단.
  - `0.60*ΔF1 + 0.25*ΔOnDevice > 0` 이면 유지.
  - <= 0 이면 cloud trigger를 더 좁혀서 재시도(저F1 시그니처만 fallback).

### 3) Cloud fallback 미실행 + On-device 비율 상승/유지(대개 100%)
- Interpretation:
  - 실질 on-device-only 결과.
- Action:
  - 점수가 `70.7`보다 높으면 on-device 전략이 hidden에 통하는 것. 유지.
  - 점수가 정체/하락이면 과적합 또는 hidden 분포 불일치. 다음 1회는 최소 cloud fallback 복구 전략으로 전환.

### 4) Cloud fallback 미실행 + On-device 비율 하락
- Interpretation:
  - 메트릭/로깅 불일치, 혹은 분기 버그 가능성. 가장 위험.
- Action:
  - 제출 전 마지막 1회라면 해당 코드 버전 배제.
  - 직전 안정 버전(main freeze)로 롤백 제출.

## Additional Cases (실전에서 자주 발생)

### A) `status=queued` 장기 지속
- Action:
  - 코드 변경하지 말고 결과 확정까지 대기.
  - 다음 1회 의사결정은 확정 결과 기반으로만 수행.

### B) `status=error` 또는 제출 거부(rate limit 제외)
- Action:
  - 즉시 같은 커맨드 재시도하지 말고 응답 본문 기록.
  - 제출 스크립트/네트워크 이슈와 모델/전략 이슈를 분리.

### C) Rate limit
- Action:
  - 남은 시간 역산 후 “수정 마감 시각”을 먼저 고정.
  - 마감 이후엔 코드 수정 금지, 제출만 수행.

### D) Cloud 호출은 됐는데 F1 개선 없음
- Interpretation:
  - 잘 맞는 케이스까지 cloud로 보냈거나, cloud 출력이 strict match에 불리.
- Action:
  - fallback을 멀티툴/저신뢰/검증실패 케이스로만 축소.

### E) Cloud 호출 자체가 전혀 안 됨(반복)
- Interpretation:
  - hidden 환경에서 trigger 미발화 또는 예외 후 local degrade가 대부분.
- Action:
  - 현실적으로 on-device-only 최고 안정 전략으로 승부.
  - hard한 규칙 추가보다 single-tool/high-precision 유지에 집중.

## One-Shot Execution Plan (남은 기회가 사실상 1회일 때)

1. 현재 queued 결과가 완료될 때까지 `main.py` 수정 금지.
2. 결과 확인 후 아래 기준으로만 결정:
   - `score > 70.7` and (cloud 동작 또는 on-device 개선): 그대로 최종 제출.
   - `score <= 70.7` and cloud 미동작: on-device 안정 버전으로 최종 고정.
   - `score <= 70.7` and cloud 동작: fallback 범위 축소 버전으로 1회만 재도전.
3. 마지막 제출 전 체크리스트:
   - `python3 -m py_compile main.py`
   - 제출 커맨드/팀명/로케이션 고정 확인
   - 제출 직후 `submission_id` 기록

## Practical Rule of Thumb
- 지금 단계에서는 “새 아이디어 추가”보다 “손실 방지”가 더 중요.
- 마지막 1회는 반드시:
  - known-good 코드 경로,
  - 최소 변경,
  - 명시적 fallback 조건
  만 사용.
