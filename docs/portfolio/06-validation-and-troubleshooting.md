# 검증과 문제 해결

## 증거 수준

| 표기 | 의미 |
|---|---|
| 코드 확인 | 현재 source/config/schema에 처리 경로가 있음 |
| 운영자 제공 | 프로젝트 참여자가 최종 시연 환경의 상태를 알려 줌 |
| 실행 기록 | 날짜·환경·시나리오가 저장된 manifest나 실행 기록에서 확인 |
| 미확인 | 현재 저장소 자료만으로 운영 장비의 상태나 개별 성공을 증명하지 못함 |

테스트 코드가 존재하는 사실과 특정 테스트가 실행되어 통과한 사실도 구분합니다.

## 저장된 로컬 R8 E2E

2026-11-09 재현 패키지 manifest에는 합성 404 요청 30건을 사용한 로컬 R8 end-to-end 결과가 기록되어 있습니다.

~~~text
합성 404 요청
  → Graylog 원본 로그와 R8 Event 확인
  → n8n Ticket 처리와 AI-XDR /events 전달
  → /process processed=1
  → assessment 저장: R8 / BENIGN / score 10 / confidence 0.80 / NO_ACTION
  → IP 차단·계정 잠금 없음
~~~

민감한 correlation ID와 실행 번호를 제외한 [manifest 발췌](assets/r8-local-e2e-summary.json)를 제공합니다. 이는 한 재현 환경의 합성 R8 시나리오입니다. 전체 R1–R12 개별 PASS, 최종 운영 환경의 모든 실행, 악성 판정, pfSense 차단을 증명하지 않습니다.

## R3: 모델의 거절과 Tool DENY는 다르다

### 현상

일반 직원이 기밀 자료를 요청했을 때 AI 화면에는 거절이 보이지만 Graylog의 R3 Event는 항상 같은 방식으로 나오지 않는 경우가 있었습니다.

### 코드 경계

~~~mermaid
sequenceDiagram
  actor U as 직원
  participant L as AI LLM
  participant T as 보호 Tool
  participant S as 서버 권한 검사
  participant G as Graylog
  participant N as n8n
  participant X as AI-XDR

  U->>L: 기밀 자료 요청
  alt Tool 호출을 선택
    L->>T: restricted_document_read
    T->>S: 사용자·역할·자료 권한 확인
    S-->>G: 거부 시 agent_tool_call / DENY
    G->>N: 조건을 만족한 Event/Alert
    N->>X: Ticket 연결 후 events/process
  else LLM이 직접 거절
    L-->>U: 거절 문장
    Note over T,G: Tool dispatcher를 거치지 않으면 동일한 Tool DENY 로그가 없을 수 있음
  end
~~~

서버가 Tool 실행 전에 실제 권한을 확인하는 것이 안전성의 기준입니다. 모델의 자연어 답변은 Graylog R3 탐지가 만들어졌다는 증거가 아닙니다. 원본 DENY 로그, Event Definition 조건, Graylog Event, Notification/n8n execution을 단계별로 확인해야 합니다.

### 문제 해결에서 얻은 점

- 발표용 문구를 바꿔도 모델이 매번 보호 Tool을 선택한다고 보장할 수는 없습니다.
- Tool을 호출하지 않은 요청에 R3 DENY 이벤트를 인위적으로 만들어 넣지 않습니다.
- 시연에서는 대화 이력이 없는 계정과 권한 없는 명확한 문서 조회 요청을 사용하고, Tool 호출/원본 DENY 로그를 먼저 확인하는 편이 재현 경로를 분명히 합니다.
- 실제 탐지 여부는 Graylog의 운영 Event Definition과 해당 시각의 실행 결과로 확인해야 합니다.

## AI-XDR 지연과 /process 504

### 현상과 최초 가설

집계 시간 변경 시점에 AI-XDR /process 요청이 504로 끝나거나 결과가 늦게 도착했습니다. 처음에는 3분에서 1분으로 바꾼 집계가 원인으로 의심됐습니다.

### 비교와 원인 분리

당시 execution 기록을 비교한 결과 3분 설정 시기에도 오래 걸린 요청이 있었습니다. 변경 과정의 핵심 차이는 집계 주기였고 /process URL, payload, 인증, HTTP timeout은 같았다는 기록이 있습니다. 따라서 집계 간격만으로 처리 지연을 설명하지 않았습니다.

운영 진단에서 앞단 HAProxy 경로는 약 30초 뒤 504를 반환했고, AI-XDR 작업은 assessment 저장까지 진행된 경우가 있었습니다. 응답이 호출한 쪽까지 돌아오기 전에 중간 경로가 먼저 연결을 닫는 상황으로 구분했습니다.

### 조치와 한계

- 중간 경로의 대기 제한을 약 90초로 늘려 조기 504를 완화했습니다. 이 조정은 AI 분석 자체를 빠르게 만들지는 않습니다.
- 별도 느린 실행에서 XDR provider auto가 로컬 Ollama qwen2.5:7b를 선택한 기록이 확인됐습니다. 느린 추론은 /process 및 n8n 후속 알림을 지연시킬 수 있습니다.
- 최종 시연 환경의 제공 정보는 XDR auto fallback Groq → NVIDIA → Ollama입니다. 이는 모든 평가에서 Groq가 선택됐다는 증거가 아닙니다.
- 최신 운영 latency와 장기간 안정화 결과는 이 문서 작성에서 재측정하지 않았습니다.

이 사례는 timeout 증가를 임시 완화와 원인 해결로 혼동하지 않고, 앞단 대기와 AI provider 처리 시간을 나눠 보는 것이 중요하다는 점을 보여 줍니다.

## R1–R12 운영과 개별 검증 범위

최종 시연 환경에서 R1–R12를 운영했다는 정보는 운영자 제공 사실입니다. 현재 저장소의 기본 Graylog export는 8개, 재현 패키지는 OBS 포함 13개입니다. 개별 Rule의 성공은 원본 메시지와 Event/Alert를 같은 시점·key로 연결한 자료가 있을 때만 말할 수 있습니다.

저장소의 tests/에는 AI Tool, AI-XDR, Incident, logging 테스트가 있습니다. 이번 단계는 문서 작업이며 테스트 명령을 실행하지 않았습니다.

## pfSense와 실제 대응

앱 코드에는 blocked IP 관리 API와 TXT feed 경로가 있습니다. 그러나 feed API 존재, AI-XDR 권고, UI상의 차단 기록은 pfSense가 실제 패킷을 차단했다는 독립 증거가 아닙니다. Alias, Firewall Rule, 갱신, 만료 후 해제는 별도의 테스트망 증거가 필요합니다.

## 근거

- [R8 실행 기록 원천](../../repro-package/NEXUS-WORK-REPRO-2026-11-09/manifest.json)
- [비식별 R8 요약](assets/r8-local-e2e-summary.json)
- [AI Tool 구현](../../app/ai.py), [서버 권한 검사](../../app/ai_tools.py)
- [이벤트 logger](../../app/security.py)
- [XDR provider와 triage](../../app/ai_xdr.py)
- [내부 events/process API](../../app/internal_api.py)
- [관련 테스트 설계](../../tests/test_ai_tools.py), [AI-XDR](../../tests/test_ai_xdr.py), [Incident](../../tests/test_incidents.py)