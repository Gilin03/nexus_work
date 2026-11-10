# Graylog 탐지 규칙 R1–R12

최종 시연 환경에서 Graylog R1–R12 12개 탐지 규칙을 운영했습니다. 각 규칙은 업무 포털과 AI Agent에서 생성되는 이벤트, 호스트·서비스 로그를 유형별로 구분해 Event/Alert를 만듭니다.

## 규칙 카탈로그

| Rule | 탐지 목적 | 대표 신호 |
|---|---|---|
| R1 | 계정 침해 의심 | 로그인 실패 뒤 성공 또는 계정 잠금과 연계된 인증 이벤트 |
| R2 | 직접 Prompt Injection 차단 | 직접 입력에서 injection 탐지와 DENY 결정 |
| R3 | AI Tool 권한 위반 | 보호 Tool 호출이 서버 권한 검사에서 거부됨 |
| R4 | 비정상 내부 API 접근 | 허용 범위를 벗어난 API 호출 또는 인증·권한 거부 |
| R5 | 계정 스프레이 | 한 출발지에서 여러 계정에 걸친 로그인 실패 |
| R6 | 잠금 후 재시도 | 계정 잠금 뒤 같은 사용자·IP의 재시도 |
| R7 | 심야 로그인 성공 | 정책상 심야 시간대의 login_success |
| R8 | 웹 경로 스캔 | 같은 출발지에서 누적된 not_found/404 요청 |
| R9 | 관리자 권한 접근 거부 | 관리자 권한이 없는 사용자의 관리 경로 요청 |
| R10 | 기밀 자료 접근 거부 | 권한 밖 confidential·finance·payroll 자료 접근 |
| R11 | 반복 Tool 권한 거부 | 사용자·세션 맥락에서 반복된 보호 Tool DENY |
| R12 | 간접 콘텐츠 유발 Tool 거부 | 간접 콘텐츠 처리 맥락과 이어진 보호 Tool DENY |

## 탐지 데이터 흐름

~~~mermaid
flowchart LR
  O[원본 로그] --> S[Graylog Input·Stream]
  S --> Q[Event Definition 조건 평가]
  Q --> E[Graylog Event / Alert]
  E --> H[Notification webhook]
  H --> N[n8n Ticket 처리]
~~~

원본 로그는 포털이나 호스트에서 만들어집니다. Graylog는 필드를 기준으로 Stream과 Event Definition을 평가하고, 생성된 경보를 n8n 등 후속 시스템에 전달합니다.

## AI Agent 보안 규칙의 핵심

R2, R3, R11, R12는 AI Agent 보안 동작과 관련된 규칙입니다.

- **R2:** 직접 입력된 Prompt Injection 탐지·차단 결과
- **R3:** 보호 Tool 호출을 서버가 거부한 결과
- **R11:** 보호 Tool 거부가 반복되는 행위
- **R12:** 간접 콘텐츠가 후속 Tool 동작에 영향을 준 맥락

특히 R3는 AI가 화면에 “권한이 없습니다”라고 답했는지만 확인하지 않습니다. R3 경보가 되려면 모델이 보호 Tool을 선택하고, 서버 권한 검사가 DENY를 기록해야 합니다. 모델이 Tool을 부르지 않고 직접 거절하면 Tool DENY 로그는 생성되지 않습니다. 실제 R3 흐름은 [시연·검증 문서](06-validation-and-troubleshooting.md)에서 확인할 수 있습니다.

## 탐지와 위험 평가는 별도 단계

Graylog 탐지는 정의된 이벤트 조건이 충족됐는지 판단합니다. AI-XDR은 Ticket에 연결된 이벤트 맥락을 평가해 verdict, 위협 점수와 대응 권고를 만듭니다. 따라서 규칙 경보가 발생해도 악성 판정이나 높은 점수가 반드시 따라오는 것은 아닙니다.

예를 들어 R8은 반복된 404 요청을 경로 스캔 신호로 탐지합니다. AI-XDR은 평가 입력에 포함된 다른 징후와 사건 맥락을 바탕으로 위험도를 따로 판단합니다.

## 관련 코드와 설정

- [Graylog Event Definition export](../../security_migration/export/graylog/event_definitions.json)
- [Graylog Input·Stream export](../../security_migration/export/graylog/)
- [Wazuh·Graylog 적용 스크립트](../../security_migration/scripts/)
- [포털 보안 이벤트 logger](../../app/security.py)
- [인증 이벤트 집계](../../app/auth_events.py)
- [AI Tool 권한 검사](../../app/ai_tools.py)
- [AI-XDR API](../../app/internal_api.py)
- [Graylog logging 테스트 코드](../../tests/test_graylog_logging.py)
