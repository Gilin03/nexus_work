# 아키텍처와 보안 로그 흐름

## 전체 데이터 흐름

~~~mermaid
flowchart LR
  subgraph Sources[로그 출처]
    APP[NEXUS 포털<br/>애플리케이션 보안 이벤트]
    HOST[서버·호스트 로그]
    OTHER[환경별 연동 로그]
  end
  W[Wazuh Agent / Manager]
  G[Graylog<br/>Input·Stream·Event Definition]
  N[n8n Published workflow]
  T[(Ticket)]
  X[AI-XDR API]
  XD[(Assessment)]
  I[Incident 화면]
  M[관리자 검토·승인]
  F[blocked IP feed]
  P[pfSense<br/>Alias·Firewall Rule]

  APP --> G
  HOST --> W --> G
  OTHER --> G
  G -->|Event / Alert| N
  N --> T
  N -->|events / ready window| X --> XD
  T --> I
  XD --> I
  X --> M
  M --> T
  X -. 조건부 feed 연동 .-> F
  F -. 장비 설정 필요 .-> P
~~~

## 구성요소 역할

| 구성요소 | 맡은 역할 |
|---|---|
| Flask 포털 | 업무 기능과 AI Assistant를 제공하고 인증·인가·Tool 실행 이벤트를 생성 |
| MySQL | 포털 데이터, Ticket 또는 AI-XDR 결과를 저장. 배포 구성에 따라 서비스 DB가 분리될 수 있음 |
| Wazuh | Agent와 Manager를 통해 지정된 호스트 로그를 수집하고 선택된 경보를 Graylog로 전달 |
| Graylog | 로그 Input, Stream 분류, R1–R12 Event Definition으로 보안 이벤트를 탐지 |
| n8n | Graylog 알림을 정규화하고 Ticket을 만들거나 병합한 뒤 AI-XDR로 전달 |
| AI-XDR | 이벤트를 상관 분석하고 AI 결과와 서버 정책을 assessment로 저장 |
| Incident | 기존 Ticket, assessment, 대응 정보를 조회하고 사건 종결 처리 |
| pfSense | 차단 feed와 Alias·Firewall Rule을 연결해 네트워크 정책을 적용하는 외부 장비 |

## 이벤트 생성과 수집은 다른 역할

포털 내부의 로그인, 권한 거부, AI Tool 실행은 앱 코드가 구조화된 보안 이벤트로 생성합니다. 공통 경로는 [app/security.py의 log_event()](../../app/security.py)이며, 설정된 핸들러로 JSONL 또는 GELF 로그를 전달합니다.

Wazuh는 호스트에서 발생한 로그를 수집하는 경로입니다. Manager syslog 설정은 선택한 Wazuh rule 경보를 Graylog로 보내며, 포털이 직접 만든 이벤트의 생성자 역할을 하지는 않습니다.

Graylog는 들어온 원본 메시지를 Stream으로 분류하고 Event Definition 조건을 평가합니다. 경보가 생성되면 설정된 Notification이 n8n webhook으로 전달합니다.

![Graylog 탐지 규칙 설정 화면](assets/graylog-rules.webp)

*최종 시연 환경에서 운영한 R1–R12 탐지 규칙 중 설정 화면을 보여주는 캡처입니다.*

![n8n 이벤트 처리 workflow](assets/workflow.webp)

*Graylog 경보 수신, Ticket 처리, AI-XDR 요청과 후속 경로를 잇는 workflow 화면입니다.*

## 보안 이벤트 필드

로그는 이벤트 유형에 따라 다음 메타데이터를 기록합니다.

- event_type, source_component, severity
- user, role, src_ip
- method, path, decision, reason
- request_id와 탐지·분석 상관관계 식별자

agent_tool_call 및 authz_deny처럼 이벤트 유형과 decision을 명확히 기록해 Graylog query가 실제 서버 권한 결과를 탐지하도록 합니다. 비밀번호, API token, 원문 prompt 및 첨부 내용은 보안 이벤트 필드에 포함하지 않습니다.

## 네트워크 구역

공개 문서에서는 내부 주소 대신 논리적 역할로 구분합니다.

- **앱 구역:** Flask 포털과 내부 API
- **호스트 구역:** Wazuh Agent 대상 서버
- **관제·자동화 구역:** Wazuh Manager, Graylog, n8n
- **데이터 구역:** 포털·Ticket·AI-XDR 데이터베이스
- **경계 구역:** pfSense 및 외부 네트워크 정책

Graylog·n8n·Wazuh 구성 파일과 재현 절차는 [실행·재현 문서](07-reproduction-and-limitations.md)에 연결했습니다.
