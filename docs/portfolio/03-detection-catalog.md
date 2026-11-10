# Graylog 탐지 규칙 R1–R12


## 규칙 카탈로그

아래는 각 Rule의 목적을 요약한 것입니다. 운영 query, search window, execute interval, group-by, notification을 고정해서 설명하지 않습니다. 이 값은 운영 Published 설정 export가 있어야 정확하게 확정할 수 있습니다.

| Rule | 탐지 목적 | 탐지에 쓰이는 대표 신호 |
|---|---|---|
| R1 | 계정 침해 의심 | 로그인 실패 뒤 성공 또는 잠금과 연계된 인증 이벤트 |
| R2 | 직접 Prompt Injection 차단 | direct 입력에서 injection 탐지와 DENY 결정 |
| R3 | AI Tool 권한 위반 | 보호 Tool 호출을 서버 권한 검사에서 거부 |
| R4 | 비정상 내부 API 접근 | 허용되지 않은 내부 API 호출과 인증/권한 거부 |
| R5 | 계정 스프레이 | 한 출발지에서 여러 계정에 걸친 로그인 실패 |
| R6 | 잠금 후 재시도 | 계정 잠금 이후 관련 출발지/계정의 재시도 |
| R7 | 심야 로그인 성공 | 정책상 심야 시간대의 login_success |
| R8 | 웹 경로 스캔 | 같은 출발지에서 누적된 not_found/404 요청 |
| R9 | 관리자 권한 접근 거부 | 관리자 권한이 없는 역할의 관리 경로 요청 |
| R10 | 기밀 자료 접근 거부 | 권한 밖 confidential/finance/payroll 자원 접근 |
| R11 | 반복 Tool 권한 거부 | 동일 사용자·세션 등의 맥락에서 반복된 보호 Tool DENY |
| R12 | 간접 콘텐츠 유발 Tool 거부 | 간접 콘텐츠 추적 맥락에 이어 보호 Tool 호출이 DENY된 경우 |

## 재현 snapshot에서 확인되는 조건 예

다음은 최종 운영값이 아니라 재현 패키지 snapshot의 예입니다.

- R5: 같은 출발지에서 300초 안에 서로 다른 사용자 5명 이상 실패하는 조건
- R7: KST 00:00–05:00의 login_success 조건
- R8: 같은 출발지에서 60초 내 not_found 30회 이상
- R11: 같은 사용자/세션의 보호 Tool 거부 누적 조건

기본 export와 재현 패키지 사이에도 정의와 시간이 다를 수 있습니다. 발표나 운영 문서에서 숫자를 인용할 때는 반드시 해당 snapshot을 표시해야 합니다.

## 원본 로그, Event, 후속 처리

Graylog의 R1–R12는 하나의 실행 결과가 아니라 여러 경계로 이어집니다.

~~~mermaid
flowchart LR
  O[원본 로그] --> Q[Stream·query 일치]
  Q --> A[시간·집계 조건 충족]
  A --> E[Graylog Event/Alert]
  E --> W[Notification webhook]
  W --> N[n8n 처리]
~~~

원본 로그는 있는데 Alert가 없으면 Event Definition의 field/query/window/group-by를 확인합니다. Alert가 있는데 n8n execution이 없으면 Notification 설정과 HTTP 응답을 확인합니다. 한 단계의 성공을 다음 단계의 성공으로 간주하지 않습니다.

## R3와 R12에서 놓치기 쉬운 점

R3의 기준은 AI가 거절 문구를 보여 줬는지가 아니라 보호 Tool 호출이 서버까지 도달해 권한 검사에서 DENY됐는지입니다.

1. LLM이 허용 목록의 보호 Tool을 선택할 수 있습니다.
2. 서버가 현재 사용자·역할·자료 권한을 다시 확인합니다.
3. 권한이 부족하면 Tool 실행을 거부하고 agent_tool_call/DENY를 기록합니다.
4. Graylog는 그 원본 이벤트로 R3 Event/Alert를 생성합니다.

모델이 Tool을 부르지 않고 자연어로 바로 거절하면 동일한 Tool DENY 이벤트가 생기지 않을 수 있습니다. 화면에 거절 답변이 있다는 것만으로 R3 로그나 Graylog Alert가 생성됐다고 판단하지 않습니다.

R12는 간접 콘텐츠가 관찰됐다는 이유만으로 성립하지 않습니다. 저장소 설계 자료는 콘텐츠·요청 상관정보와 후속 보호 Tool 거부가 연결되는 조건을 설명합니다. 정확한 운영 query는 현재 저장소만으로 확인할 수 없습니다.

## 탐지와 위험 평가를 구분

R8의 404 임계치를 넘으면 Graylog 경보가 생길 수 있습니다. 이는 경로 스캔 신호를 탐지한 것입니다. AI-XDR은 추가 공격 성공 징후가 평가 입력에 있는지 따로 보고 점수와 verdict를 만듭니다. 그러므로 Event가 생성됐어도 낮은 threat_score 또는 BENIGN이 나올 수 있습니다.

## 근거

- [기본 Graylog export](../../security_migration/export/graylog/event_definitions.json)
- [재현용 Event Definition snapshot](../../repro-package/NEXUS-WORK-REPRO-2026-11-09/graylog/event_definitions.json)
- [앱 로그 필드](../../app/security.py)
- [AI Tool 권한 검사](../../app/ai_tools.py)
- [인증 이벤트 집계](../../app/auth_events.py)
- [AI-XDR API](../../app/internal_api.py)
- [관련 테스트 설계](../../tests/test_graylog_logging.py), [Tool 권한 테스트](../../tests/test_ai_tools.py)

테스트 파일의 존재는 이 문서 작업에서 테스트를 실행하거나 Rule별 PASS를 확인했다는 의미가 아닙니다.