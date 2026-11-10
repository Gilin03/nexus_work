# 프로젝트와 개인 기여

## 프로젝트 배경

업무 포털, 호스트, AI Agent에서는 로그인·권한 거부·Tool 실행·웹 요청 등 서로 다른 보안 신호가 발생합니다. NEXUS WORK는 이 로그를 중앙 탐지에 모으고, 연관 경보를 Ticket과 AI-XDR 평가로 연결해 관리자가 분석 결과와 대응 상태를 확인할 수 있게 만든 4인 팀 프로젝트입니다.

~~~text
포털·호스트 로그 → Graylog 탐지 → n8n Ticket 처리
                → AI-XDR 평가·정책 → 관리자 검토·대응 이력
~~~

핵심 설계는 규칙 탐지, AI 분석, 서버 정책, 관리자 대응을 단계별로 분리한 것입니다. AI-XDR은 위험도와 권고를 제공하고, 실제 대응은 시스템 정책과 승인 절차를 거칩니다.

## 팀 결과와 김태빈의 담당

| 영역 | 팀 프로젝트 결과 | 김태빈의 담당 및 기여 |
|---|---|---|
| 포털·데이터 | Flask 업무 포털, MySQL, 인증·인가, AI Assistant와 관리자 기능 | 보안 이벤트가 외부 탐지 파이프라인에 전달되도록 로그 필드와 연동 흐름을 다룸 |
| Wazuh | Agent·Manager 기반 호스트 로그 수집·전달 | Manager syslog 전달 설정과 적용용 Wazuh 설정 자료를 구성하고 Graylog 연동을 확인 |
| Graylog | Stream, Event Definition, 알림을 이용한 중앙 탐지 | R1–R12 규칙 구성·운영, 이벤트 필드 및 탐지 조건 연계, 시나리오별 원본 로그와 경보 확인 |
| n8n | Webhook 기반 Ticket 및 AI-XDR 자동화 | Graylog 알림 정규화, Ticket 생성·병합, AI-XDR API 전달과 결과 후처리 흐름을 연결 |
| AI-XDR | 이벤트 상관 분석, 정책 평가, 관리자 검토·승인 | provider 실행·응답 검증 문제를 추적하고 이벤트부터 assessment 및 후속 알림까지 검증 |

팀은 4명이며 포털, 데이터, AI Agent, 관리자 화면을 포함한 전체 구현은 공동 결과입니다. 위 표는 김태빈이 맡아 연결·검증한 보안 이벤트 파이프라인을 구분해 보여 줍니다.

## Wazuh: 호스트 로그를 Graylog로 전달

Wazuh는 호스트 로그를 수집하고 선택된 경보를 중앙 관제에 전달하는 역할을 합니다. 포털의 로그인·AI Tool 권한 이벤트는 포털 애플리케이션이 직접 생성하며, 모든 R1–R12 로그를 Wazuh가 만드는 구조는 아닙니다.

Manager syslog 템플릿은 Graylog 주소의 UDP 5140으로 Wazuh rule 550, 553, 554 경보를 전달하도록 구성되어 있습니다. Agent 설정 템플릿과 export/import 스크립트를 함께 정리해 적용 절차를 재현할 수 있도록 했습니다.

관련 자료: [Wazuh 설정 템플릿](../../security_migration/export/wazuh/), [Wazuh 적용·내보내기 스크립트](../../security_migration/scripts/)

## Graylog: R1–R12 탐지 운영

Graylog Input으로 로그를 받고, Stream과 Event Definition으로 인증·AI Agent·서비스 요청을 규칙별로 탐지하도록 구성했습니다. 최종 시연 환경에서 R1–R12 12개 규칙을 운영했으며, 각 규칙의 목적과 처리 신호는 [탐지 규칙 문서](03-detection-catalog.md)에 정리했습니다.

탐지는 이벤트 필드에 의존하므로 앱 로그의 event_type, decision, user, role, src_ip, resource와 같은 필드가 Graylog query 및 group-by에 전달되는지 확인하는 작업도 수행했습니다.

관련 자료: [Graylog export](../../security_migration/export/graylog/), [Graylog 적용 스크립트](../../security_migration/scripts/import_graylog.ps1), [공개용 규칙 화면](assets/graylog-rules.webp)

## n8n: 경보를 Ticket과 AI-XDR로 연결

최종 운영 n8n workflow는 Published 상태로 사용했습니다. Graylog 알림이 들어오면 필요한 필드를 정리하고 Ticket을 생성하거나 기존 Ticket과 연결합니다. 이어 AI-XDR events/process API로 분석을 요청하고, 반환된 assessment와 Ticket 정보를 후속 처리 및 알림에 사용합니다.

관련 자료: [workflow 전체 화면](assets/workflow.webp), [재현용 n8n 패키지 안내](../../repro-package/NEXUS-WORK-REPRO-2026-11-09/n8n/README.md), [내부 API](../../app/internal_api.py)

## AI-XDR: 분석 결과와 정책 검토

AI-XDR 이벤트 처리와 평가 API를 n8n Ticket 흐름에 연결했습니다. 평가에는 verdict, threat_score, confidence, reasoning, recommended_actions가 포함되며, 서버 정책은 승인 가능 여부와 대응 상태를 별도로 계산합니다.

최종 운영 설정은 auto provider이며 Groq를 우선하고 NVIDIA, Ollama를 순서대로 fallback할 수 있습니다. AI Chat은 별도의 provider 설정을 사용합니다. provider 장애 시 REVIEW fallback을 확인하고, 모델 응답의 JSON 및 strict schema 검증과 진단 로그를 통해 원인을 추적했습니다.

관련 코드: [AI-XDR 처리](../../app/ai_xdr.py), [설정](../../app/config.py), [events/process API](../../app/internal_api.py)

## 실제 검증 경험

- R3: 직원 계정의 보호 Tool 요청이 서버 권한 검사에서 DENY되고, Graylog 경보·n8n 후속 처리·AI-XDR 평가·관리자 승인 흐름으로 이어지는 시연을 진행했습니다.
- R8: 합성 404 요청으로 Graylog 탐지부터 n8n Ticket, AI-XDR assessment까지 로컬 재현 환경에서 확인했습니다.
- AI-XDR 지연: /process 504를 앞단 대기 제한과 provider별 추론 시간으로 분리해 조사하고 조치했습니다.

상세한 결과와 문제 해결 과정은 [검증과 문제 해결](06-validation-and-troubleshooting.md)에 있습니다.

## 배운 점

- 원본 로그, Graylog Event, Notification, n8n execution, AI-XDR assessment를 각 단계에서 확인해야 장애 지점을 좁힐 수 있습니다.
- AI의 자연어 거절은 서버 권한 거부와 다릅니다. 서버에서 Tool 권한을 다시 검사해야 실제 접근을 막고 감사 이벤트를 남길 수 있습니다.
- Ticket 병합 기간, n8n 실행 간격, AI-XDR 처리 window는 서로 다른 시간 설정입니다.
- AI provider의 응답속도와 실패 처리가 n8n 후속 자동화까지 영향을 주므로 provider와 요청 시간을 함께 추적해야 합니다.

## 코드와 설정 근거

- [보안 이벤트 logger](../../app/security.py)
- [AI Tool 권한 검사](../../app/ai_tools.py)
- [AI Chat provider 및 Tool 선택](../../app/ai.py)
- [AI-XDR 평가·정책](../../app/ai_xdr.py)
- [내부 API](../../app/internal_api.py)
- [Wazuh 설정 자료](../../security_migration/export/wazuh/)
- [Graylog 설정 자료](../../security_migration/export/graylog/)
