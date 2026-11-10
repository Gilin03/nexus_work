# Incident와 대응 이력

## 역할 분리

Incident는 사건의 Ticket, 탐지·분석·대응 기록을 조회하고 사건을 종결하는 화면입니다. AI-XDR의 위험 판단이나 차단 승인을 대신하지 않습니다.

- **Incident:** 목록·상세, 탐지 자료, assessment 요약, responses, 종결
- **AI-XDR:** 이벤트 분석, verdict/score/confidence, 정책 평가, 관리자 승인·대응
- **n8n:** Graylog 이벤트 전달, Ticket 생성·병합, API orchestration
- **pfSense:** feed와 alias/rule이 연결되어야 실제 네트워크 적용

## 데이터 원천

~~~mermaid
flowchart TD
  T[(security_incident_tickets<br/>id, ticket_key, status, latest_event, responses)]
  E[(security_xdr_events<br/>alert_id, incident_ticket_id, event fields)]
  A[(security_xdr_assessments<br/>verdict, score, policy, response_result)]
  API[n8n Ticket API<br/>fallback·보완 정보]
  L[/admin/incidents]
  D[/admin/incidents/{numeric id}]

  T --> L
  API --> L
  T --> D
  API --> D
  A -->|FK 또는 ticket_ids correlation| D
  E -. schema에 있으나 화면의 완전한 timeline source로 단정하지 않음 .-> D
~~~

위 도식은 schema와 조회 경로를 구분합니다. security_xdr_events 테이블이 존재한다는 사실만으로 Incident 화면이 그 테이블의 모든 행을 조회해 완전한 탐지 timeline을 보여준다고 볼 수 없습니다.

## Ticket 식별자

- 화면의 외부 ID는 NX-DB-xxxxxx 형태입니다.
- route와 Ticket DB 내부 참조에는 numeric id가 사용됩니다.
- ticket_key는 같은 IP 또는 user 등 사건을 묶는 grouping key입니다.
- 서로 다른 DB의 numeric PK는 같다는 보장이 없습니다. DB가 분리되면 incident_ticket_id FK가 NULL일 수 있고, 외부 Ticket ID가 상관관계 수단이 됩니다.

## 현재 코드의 조회 경계

GET /admin/incidents 목록은 로컬 security_incident_tickets와 n8n Ticket API 결과를 표시 ID 기준으로 병합합니다. 상세는 로컬 Ticket을 우선하고 API 상세 결과를 fallback/보완으로 사용할 수 있습니다.

탐지 이력은 Ticket의 latest_event 요약과 API 상세가 제공하는 alerts 자료 범위에 의존합니다. 현재 app/incidents.py는 security_xdr_events를 직접 SELECT해 모든 원본 event를 구성하지 않습니다. 따라서 상세 화면의 이력을 사건 내 모든 이벤트의 완전한 timeline이라고 표현하지 않습니다.

AI-XDR 요약은 security_xdr_assessments를 조회하며 다음 우선순위로 상관관계를 찾습니다.

1. incident_ticket_id가 있으면 numeric Ticket id로 연결
2. FK가 없으면 event_summary의 ticket_ids에 NX-DB 표시 ID가 있는지 확인

## 대응 이력과 종결

Ticket의 responses JSON은 Ticket 쪽에 기록된 대응 이력입니다. AI-XDR의 response_result는 assessment 처리 결과입니다. 서로 다른 저장 위치이므로 화면에서 함께 보여도 동일한 데이터는 아닙니다.

Incident에서 허용하는 상태 변경은 종결입니다. 관리자 권한을 확인하고 resolution 및 optional note를 기존 Ticket action 경로로 전달합니다. 차단 승인과 AI 승인/거부 기능은 Incident에 두지 않습니다.

## route와 화면

| 기능 | 현재 경로 | 구현 |
|---|---|---|
| 목록 | GET /admin/incidents | app/admin.py, app/incidents.py |
| 상세 | GET /admin/incidents/<numeric id> | app/admin.py, app/incidents.py |
| 종결 | POST /admin/incidents/<numeric id>/close | app/admin.py, app/incidents.py |
| 목록·상세 UI | 관리자 화면 | app/templates/admin_incidents.html, app/templates/admin_incident_detail.html |

## 관련 schema와 테스트

- [Incident 코드](../../app/incidents.py)
- [관리 route](../../app/admin.py)
- [목록 template](../../app/templates/admin_incidents.html)
- [상세 template](../../app/templates/admin_incident_detail.html)
- [DB schema](../../db/schema.sql)
- [Incident tests](../../tests/test_incidents.py)

테스트 코드는 동작 의도와 검증 위치를 알려 줍니다. 테스트 실행·통과 여부는 이 문서 정리와 별개입니다.