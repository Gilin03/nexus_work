# Incident와 대응 이력

## 역할 분리

Incident는 Ticket을 중심으로 사건과 처리 내역을 보여주는 화면입니다. AI-XDR 평가와 관리자 조치를 함께 확인할 수 있지만, AI 판정이나 차단 승인을 Incident에서 수행하지 않습니다.

| 기능 | 담당 |
|---|---|
| Incident | 사건 목록·상세, 탐지 요약, 평가·대응 이력, 종결 |
| AI-XDR | 이벤트 분석, verdict·점수·confidence, 정책 평가, 승인·대응 판단 |
| n8n | Graylog 이벤트 전달, Ticket 생성·병합, AI-XDR API 호출 |
| pfSense | feed 및 방화벽 정책에 연결된 실제 네트워크 처리 |

## 데이터 원천과 연결

~~~mermaid
flowchart TD
  G[Graylog Alert] --> N[n8n Ticket 처리]
  N --> T[(security_incident_tickets)]
  N --> X[AI-XDR events / process]
  X --> E[(security_xdr_events)]
  X --> A[(security_xdr_assessments)]
  T --> L[/admin/incidents]
  T --> D[/admin/incidents/{numeric id}]
  A --> D
  API[n8n Ticket 조회 API] --> L
  API --> D
~~~

Ticket은 로컬 DB의 security_incident_tickets와 n8n Ticket API 조회 결과를 표시용 Ticket ID를 기준으로 병합합니다. AI-XDR assessment는 security_xdr_assessments에서 조회하고, 연결 우선순위는 다음과 같습니다.

1. incident_ticket_id가 있으면 Ticket의 numeric id로 연결
2. numeric FK가 없으면 event_summary.ticket_ids에 NX-DB 표시 ID가 포함되는지 확인

Ticket의 responses에는 기존 후속 처리와 대응 이력이 저장됩니다. AI-XDR response_result는 assessment의 처리 결과이며, 두 자료는 서로 다른 저장 위치를 갖습니다.

## Ticket 식별자

- 화면에는 NX-DB-xxxxxx 표시 ID를 사용합니다.
- 내부 route는 numeric Ticket id를 사용합니다.
- ticket_key는 IP 또는 사용자 기준으로 묶는 grouping key입니다.
- 다른 DB의 numeric PK끼리는 직접 연결하지 않고 외부 Ticket ID로 상관관계를 유지합니다.

## 탐지 이력과 상세 정보

상세 화면은 Ticket의 latest_event와 Ticket API가 제공하는 알림 정보를 이용해 탐지 내용을 표시합니다. AI-XDR assessment, recommended actions, policy reason, response result, Ticket responses도 함께 보여줍니다.

현재 화면의 탐지 이력은 원본 보안 이벤트 테이블의 모든 행을 무제한으로 펼친 timeline이 아니라 Ticket/API가 제공하는 자료를 중심으로 구성됩니다. 상세 화면은 민감한 raw payload 대신 발생 시각, Rule, event_type, 사용자, src_ip와 같은 요약 정보를 표시합니다.

## 종결

Incident에서 허용하는 상태 변경은 종결입니다. 관리자 권한과 CSRF를 확인한 뒤 기존 Ticket action 경로로 결과와 메모를 전달하고, Ticket의 status, resolution, closed_at, note, responses를 갱신합니다. 이미 종결된 Ticket은 같은 요청이 반복되어도 안전하게 처리하도록 구성합니다.

## 화면과 route

| 기능 | 경로 | 구현 위치 |
|---|---|---|
| 목록 | GET /admin/incidents | app/admin.py, app/incidents.py |
| 상세 | GET /admin/incidents/<numeric id> | app/admin.py, app/incidents.py |
| 종결 | POST /admin/incidents/<numeric id>/close | app/admin.py, app/incidents.py |
| 목록·상세 화면 | 관리자 UI | app/templates/admin_incidents.html, app/templates/admin_incident_detail.html |

## 구현 자료

- [Incident data access](../../app/incidents.py)
- [관리자 route](../../app/admin.py)
- [목록 template](../../app/templates/admin_incidents.html)
- [상세 template](../../app/templates/admin_incident_detail.html)
- [Ticket·AI-XDR schema](../../db/schema.sql)
- [Incident 동작 테스트](../../tests/test_incidents.py)
