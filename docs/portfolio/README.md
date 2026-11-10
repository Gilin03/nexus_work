# NEXUS WORK 기술 포트폴리오

NEXUS WORK는 4인 팀이 만든 사내 업무 포털·AI Agent 보안관제 프로젝트입니다. 포털과 호스트에서 나온 보안 이벤트를 Graylog 탐지, n8n Ticket 처리, AI-XDR 평가와 관리자 검토로 연결했습니다.

이 문서 세트는 팀 전체 구현과 김태빈의 담당 범위를 구분하고, 코드·운영자 제공 사실·저장된 실행 기록을 서로 다른 근거로 표시합니다.

## 먼저 보는 흐름

~~~mermaid
flowchart LR
  S[포털·호스트·연동 로그] --> G[Graylog<br/>R1–R12 탐지]
  G --> N[n8n<br/>Event 정리·Ticket 연결]
  N --> X[AI-XDR<br/>상관 분석·정책 평가]
  X --> I[Incident<br/>조회·이력·종결]
  X --> A[관리자 검토·승인]
  A --> R[대응 기록]
  R -. feed가 별도 연결된 경우 .-> P[pfSense]
~~~

도식은 구조 설명용입니다. pfSense의 실제 Alias/Firewall 동작을 실측한 증거가 아닙니다.

## 문서 안내

| 순서 | 문서 | 내용 |
|---|---|---|
| 1 | [프로젝트와 기여 범위](01-project-and-contribution.md) | 배경, 팀 결과, 김태빈 담당 업무, 배운 점 |
| 2 | [아키텍처와 로그 흐름](02-architecture-and-logs.md) | Flask/MySQL, Wazuh, Graylog, n8n, AI-XDR, 외부 시스템 경계 |
| 3 | [Graylog 탐지 규칙](03-detection-catalog.md) | R1–R12 탐지 목적, snapshot과 운영 상태의 차이 |
| 4 | [n8n과 AI-XDR](04-automation-and-ai-xdr.md) | Ticket 병합, 이벤트 API, provider fallback, 정책·승인 |
| 5 | [Incident와 대응 이력](05-incident-and-response.md) | Ticket·event·assessment 데이터 연결과 UI 범위 |
| 6 | [검증과 문제 해결](06-validation-and-troubleshooting.md) | R8 실측, R3 경로 분석, /process 504 사례 |
| 7 | [실행과 재현](07-reproduction-and-limitations.md) | 로컬 실행, Graylog/n8n 재현 자료, 제약 |

## 사실을 읽는 기준

- **코드 확인**: 현재 checkout의 코드·설정·schema에 구현 경로가 있다는 뜻입니다. 배포되었거나 정상 운영됐다는 증거와는 다릅니다.
- **운영자 제공**: 프로젝트 참여자가 최종 시연 환경의 상태로 알려 준 정보입니다. 이번 문서 작업에서 운영 장비를 다시 조회한 결과는 아닙니다.
- **실행 기록**: 날짜·환경·시나리오가 기록된 manifest 또는 실행 자료에서 확인한 결과입니다.
- **미확인**: 현재 저장소 자료만으로 실제 운영 설정이나 성공 여부를 판단할 수 없는 항목입니다.

## 최종 시연 환경 기준

프로젝트 참여자가 제공한 최종 시연 환경 정보에 따르면 Graylog R1–R12 12개 규칙을 운영했고 n8n workflow는 Published 상태였습니다. 개별 Rule의 테스트 성공과 각 n8n 실행의 성공은 별도 증거로 판단합니다.

저장소의 기본 Graylog export 8개와 재현 패키지의 OBS 포함 13개는 운영 시연 환경과 다른 시점의 snapshot입니다. n8n의 66-node 비활성 template도 재현용 자료입니다.

AI-XDR의 운영 provider 설정은 auto이며 우선 fallback 순서는 Groq → NVIDIA → Ollama로 제공받았습니다. 실제 개별 assessment가 어느 provider/model을 사용했는지는 해당 실행 기록으로 확인해야 합니다. AI Chat은 별도 provider 설정을 사용합니다.

## 공개 자료 상태

저장된 로컬 R8 실행 기록의 비식별 요약은 [검증 문서](06-validation-and-troubleshooting.md)에서 볼 수 있습니다. Mermaid는 설명용 도식입니다. 기존 캡처에는 내부 주소, 계정명, 로컬 경로 또는 환경설정 출력이 포함되어 있어 이 포트폴리오에 삽입하지 않았습니다.

저장소 전체를 공개하기 전에는 기존 캡처·개인 기록·취약점 보고서·Git 이력을 별도 검토해야 합니다. 포트폴리오 문서를 정리한 것만으로 저장소 전체가 공개 준비된 것은 아닙니다.