# NEXUS WORK 기술 포트폴리오

NEXUS WORK는 4인 팀이 구축한 사내 업무 포털 기반 보안관제 프로젝트입니다. 포털과 호스트의 보안 이벤트를 Graylog 탐지, n8n Ticket 처리, AI-XDR 평가와 관리자 대응으로 연결했습니다.

~~~mermaid
flowchart LR
  S[포털·호스트 로그] --> G[Graylog<br/>R1–R12]
  G --> N[n8n<br/>정규화·Ticket 연결]
  N --> X[AI-XDR<br/>상관 분석·정책]
  X --> A[관리자 검토·승인]
  N --> I[Incident 조회·종결]
  X --> I
~~~

## 문서 안내

| 순서 | 문서 | 다루는 내용 |
|---|---|---|
| 1 | [프로젝트와 기여 범위](01-project-and-contribution.md) | 배경, 팀 성과, 김태빈의 담당 업무 |
| 2 | [아키텍처와 로그 흐름](02-architecture-and-logs.md) | Flask·MySQL, Wazuh, Graylog, n8n, AI-XDR |
| 3 | [Graylog 탐지 규칙](03-detection-catalog.md) | R1–R12의 목적과 이벤트 흐름 |
| 4 | [자동화와 AI-XDR](04-automation-and-ai-xdr.md) | Ticket 연결, 집계, provider fallback, 정책·승인 |
| 5 | [Incident와 대응 이력](05-incident-and-response.md) | Ticket 조회, assessment 상관관계, 종결 |
| 6 | [검증과 문제 해결](06-validation-and-troubleshooting.md) | 시연·E2E 기록과 실제 장애 대응 |
| 7 | [실행과 재현](07-reproduction-and-limitations.md) | 로컬 실행, 재현 자료, 외부 구성요소 |

최종 시연 환경에서 Graylog R1–R12 규칙을 운영하고 n8n workflow를 Published 상태로 사용했습니다. AI-XDR은 auto provider 설정에서 Groq를 우선 시도하며 NVIDIA와 Ollama를 fallback으로 지원합니다. 세부 구현과 검증 기록은 각 문서에서 확인할 수 있습니다.
