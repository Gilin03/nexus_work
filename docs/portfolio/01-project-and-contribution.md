# 프로젝트와 기여 범위

## 프로젝트 배경

사내 업무 포털, AI Agent, 호스트와 웹 서비스에서는 로그인 실패, 권한 거부, Tool 실행, 웹 요청 같은 보안 신호가 서로 다른 형태로 발생합니다. 개별 로그만 보면 서로 관련된 행동인지 판단하기 어렵고, 경보가 생성된 뒤 실제 검토와 대응 기록까지 이어지는 과정도 분산될 수 있습니다.

NEXUS WORK는 이 흐름을 사건 단위로 이어 주는 4인 팀 프로젝트입니다.

~~~text
보안 이벤트 → 규칙 탐지 → Ticket 연결 → AI-XDR 평가
            → 관리자 검토 → 대응 결과와 Incident 이력
~~~

목표는 AI가 자동으로 차단하는 데 있지 않습니다. 규칙 탐지, 사건 맥락 분석, 서버 정책, 관리자 판단을 분리해 결과를 확인하고 추적할 수 있도록 하는 것입니다.

## 팀 결과와 개인 기여

| 구분 | 범위 | 표현 기준 |
|---|---|---|
| 팀 프로젝트 결과 | Flask 업무 포털, MySQL, AI Assistant, 인증·인가, 관리자 기능과 보안 이벤트 흐름 | 저장소의 여러 모듈과 설정에 걸친 팀 결과 |
| 김태빈 담당 영역 | Wazuh 호스트 로그 연동, Graylog 탐지 규칙, n8n 이벤트·Ticket 흐름 연동 및 확장, AI-XDR 연결과 시나리오 검증 | 프로젝트 참여자가 제공한 역할 정보와 작업 기록을 기준으로 설명 |
| 공동·연동 영역 | 포털 이벤트에서 탐지·자동화·분석·관리자 검토로 이어지는 인터페이스 | 기능이 코드에 존재한다는 사실만으로 개인 작성자를 단정하지 않음 |

팀 구성은 4명입니다. 현재 확인 가능한 자료만으로 모든 팀원의 개인별 담당표를 확정하지 않았으므로, 다른 팀원의 이름이나 개인 성과를 임의로 배정하지 않습니다. 앱·DB·AI Agent를 포함한 팀 기능을 김태빈 단독 구현으로 표현하지 않습니다.

## 김태빈이 맡은 보안 이벤트 파이프라인

### Wazuh 로그 연동

Wazuh Agent/Manager를 이용한 호스트 로그 수집 경로와 설정 자료를 다뤘습니다. 포털에서 직접 만들어지는 로그인·AI Tool 권한 거부 이벤트까지 Wazuh가 생성한다고 설명하지 않습니다.

관련 자료: [Wazuh export](../../security_migration/export/wazuh/), [이벤트 기록 코드](../../app/security.py)

### Graylog 탐지 규칙

Graylog input, stream, Event Definition을 통해 R1–R12 탐지 규칙을 운영하는 흐름을 구성·연동했습니다. 최종 시연 환경에서 12개 규칙을 운영했다는 사실은 참여자 제공 정보입니다. 이 문서에서는 그 사실을 개별 12개 규칙의 실측 PASS로 확대하지 않습니다.

관련 자료: [기본 export](../../security_migration/export/graylog/), [재현 snapshot](../../repro-package/NEXUS-WORK-REPRO-2026-11-09/graylog/)

### n8n과 AI-XDR 연결

Graylog Event 전달, 필드 정리, Ticket 생성·병합, AI-XDR events/process 호출과 결과 후처리를 연결하는 작업을 맡았습니다. 최종 운영 workflow의 Published 상태는 참여자 제공 사실이며, 특정 execution 성공은 개별 실행 증거로 판단합니다.

관련 코드·재현 자료: [AI-XDR API](../../app/internal_api.py), [n8n 재현 안내](../../repro-package/NEXUS-WORK-REPRO-2026-11-09/n8n/README.md)

### 시나리오 검증과 문제 분석

대표적으로 R8 합성 404 시나리오를 로컬 재현 환경에서 끝단까지 확인한 기록이 있습니다. R3는 AI 모델의 Tool 선택과 서버 측 권한 거부를 구분하고, 원본 로그·Graylog Event·n8n 전달이 각각 확인되어야 함을 분석했습니다.

실측 범위와 한계는 [검증과 문제 해결](06-validation-and-troubleshooting.md)에 모았습니다.

## 기술적 판단과 배운 점

- 로그를 만드는 애플리케이션, 호스트 로그를 수집하는 Wazuh, Event를 만드는 Graylog의 역할을 구분해야 합니다.
- 탐지 경보가 발생했다는 사실과 공격 성공, 높은 AI 위험 점수는 서로 다른 결과입니다.
- AI의 Tool 선택과 서버의 권한 검사를 분리해야 모델이 선택한 요청을 실제 권한으로 오인하지 않습니다.
- 서로 다른 DB의 numeric ID는 직접 연결할 수 없을 수 있으므로 외부 Ticket 표시 ID를 correlation key로 보존해야 합니다.
- timeout을 늘리면 앞단의 조기 종료는 완화할 수 있지만, 느린 AI 분석 자체가 빨라지는 것은 아닙니다.

## 근거

- [Flask app registration](../../app/__init__.py)
- [Security event logger](../../app/security.py)
- [AI Tool 권한 검사](../../app/ai_tools.py)
- [AI-XDR 처리](../../app/ai_xdr.py)
- [내부 API](../../app/internal_api.py)
- [Incident 경로](../../app/incidents.py)