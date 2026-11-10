# 검증과 문제 해결

## R3 AI Tool 권한 거부 시연

최종 발표 시연은 일반 직원 계정으로 보호된 기밀 문서를 요청하고, Tool 실행 단계에서 서버가 권한을 거부하는 흐름으로 진행했습니다.

[![R3 AI Tool 권한 거부 시연 영상](https://nexus-work-portfolio-site.vercel.app/assets/r3-request-poster.webp)](https://nexus-work-portfolio-site.vercel.app/assets/r3-demo.mp4)

영상은 새 요청에서 시작해 보호 Tool DENY, Graylog 원본 로그와 R3 경보, n8n 처리, AI-XDR 평가, 관리자 차단 승인, 차단 목록 기록과 포털의 403 응답까지 보여 줍니다.

### 문제

일반 직원이 기밀 문서를 요청해 AI가 거절 답변을 하더라도 R3 경보가 매번 생성되는 것은 아니었습니다.

### 조사

AI Assistant에서 실제로 어떤 경로를 탔는지 앱 보안 로그와 Graylog 원본 메시지를 비교했습니다. app/ai_tools.py에서 restricted_document_read Tool이 선택되면 서버가 사용자의 문서 권한을 다시 확인하고, 허용하지 않을 때 agent_tool_call DENY와 authz_deny를 기록합니다.

### 실제 원인

Groq가 요청을 처리할 때 보호 Tool을 선택하는 경우와 자연어로 바로 거절하는 경우가 모두 있었습니다. Tool 호출 없이 답변한 요청은 서버의 Tool 권한 검사로 진입하지 않으므로 agent_tool_call DENY가 생성되지 않습니다. R3는 거절 문구를 검색하는 규칙이 아니라 서버가 실제 Tool 호출을 거부한 로그를 탐지하는 규칙입니다.

### 시연 방식과 재확인

시연에서는 새 대화에서 일반 직원 계정으로 기밀 문서함의 목록이나 제목을 확인해 달라고 구체적으로 요청했습니다. 이 요청으로 보호 Tool 호출과 서버 DENY가 발생한 뒤, Graylog Event와 n8n 실행, AI-XDR 평가와 관리자 조치로 이어지는 장면을 녹화 자료에서 확인했습니다.

### 핵심 구현

- AI 모델은 Tool 선택을 제안하지만, 접근 권한은 서버가 다시 판정합니다.
- 보호 Tool 접근이 거부되면 거부 사유와 사용자·출발지 등의 메타데이터를 보안 이벤트로 남깁니다.
- Graylog R3는 해당 DENY 이벤트를 받아 경보를 만들고 후속 자동화에 전달합니다.

## AI-XDR process 지연과 504

### 문제

집계 주기를 3분에서 1분으로 줄인 뒤 n8n의 AI-XDR 요청에서 504가 자주 발생하고, Discord 등 후속 결과도 늦게 도착했습니다.

### 조사

실행 기록을 비교해 3분 설정 시기에도 오래 걸린 요청이 있었음을 확인했습니다. 집계 주기와 별개로 process URL, payload, 인증, 요청 timeout이 달라졌는지 비교했고, 주요 변경은 집계 주기였습니다. 또한 AI-XDR 내부에서 assessment 저장까지 진행됐는데 호출자는 504를 받은 실행도 확인했습니다.

앞단 경로는 약 30초 뒤 응답을 끊고 있었고, AI-XDR 진단에서는 auto 선택으로 Ollama의 qwen2.5:7b가 사용된 느린 실행도 확인했습니다. 따라서 504 발생 시점과 내부 분석 처리시간을 각각 원인으로 나눴습니다.

### 실제 원인

- 짧은 앞단 대기 제한이 30초를 넘는 AI 응답을 기다리지 못해 호출자에게 504를 반환했습니다.
- provider auto fallback이 Ollama를 선택한 실행에서는 모델 추론이 길어져 process와 후속 workflow가 지연될 수 있었습니다.
- 3분에서 1분으로 바꾼 집계 자체가 처리시간을 늘린 원인은 아니었습니다.

### 수정과 재확인

- 앞단 process 대기 제한을 90초로 조정해 30초 조기 종료를 완화했습니다.
- AI-XDR provider는 auto로 유지하면서 Groq를 우선하고 NVIDIA, Ollama를 fallback으로 사용하는 구조를 적용했습니다.
- 변경 후 process 성공 응답을 확인했고 504 오류는 사라졌습니다. 대기 제한 조정은 AI 추론 자체를 빠르게 하는 조치는 아니므로 provider별 처리시간을 구분해 추적했습니다.

## R8 합성 이벤트 E2E

2026-11-09 로컬 재현 manifest에 TEST-NET 출발지로 404 요청 30건을 전송한 결과가 기록되어 있습니다.

~~~text
404 요청 30건
  → Graylog 원본 로그 및 R8 Event
  → n8n Ticket 처리
  → AI-XDR events 저장
  → process processed=1
  → R8 assessment: BENIGN / score 10 / confidence 0.80 / NO_ACTION
~~~

확인한 Ticket 표시는 NX-DB-000365입니다. 이 안전한 합성 시험에서는 IP 차단과 계정 잠금이 발생하지 않았습니다. [비식별 실행 요약](assets/r8-local-e2e-summary.json)과 [재현 package manifest](../../repro-package/NEXUS-WORK-REPRO-2026-11-09/manifest.json)에 실행 결과가 남아 있습니다.

## 확인 위치

- [AI Tool 선택·권한 검사](../../app/ai.py), [서버 Tool 실행·DENY](../../app/ai_tools.py)
- [보안 이벤트 logger](../../app/security.py)
- [AI-XDR provider와 처리](../../app/ai_xdr.py)
- [events/process API](../../app/internal_api.py)
- [R8 로컬 E2E 요약](assets/r8-local-e2e-summary.json)
