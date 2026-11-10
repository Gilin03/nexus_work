# 실행과 재현

## 로컬 포털과 MySQL 실행

이 저장소는 Flask 포털과 격리형 MySQL 개발 구성을 제공합니다. Windows PowerShell 기준으로 프로젝트 루트에서 실행합니다.

~~~powershell
Copy-Item .env.example .env
# .env에 로컬 전용 SECRET_KEY와 DB 계정 값을 입력하고 DB_PORT=3308 설정
docker compose -f docker-compose.local.yml up -d
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
~~~

포털 기본 주소는 http://127.0.0.1:5070이며, Compose MySQL은 호스트의 127.0.0.1:3308에 바인딩됩니다. 로컬 실행에 필요한 값과 외부 연동 주소는 각 PC 환경에 맞게 설정합니다. 비밀값은 로컬 .env에서 관리하며 저장소나 재현 패키지에 넣지 않습니다.

테스트를 실행하려면 로컬 DB와 Python 의존성을 준비한 뒤 다음을 사용합니다.

~~~powershell
python -m pytest -q
~~~

## 로그 관제 환경

Flask와 MySQL은 이 저장소에서 실행할 수 있습니다. Graylog, n8n, Wazuh, Suricata, pfSense는 별도 서비스·호스트·네트워크 장비로 구성합니다.

- Wazuh 적용 자료는 security_migration/export/wazuh/와 security_migration/scripts/에 있습니다.
- Graylog Input, Stream, Event Definition과 import/export 스크립트는 security_migration/에 있습니다.
- n8n workflow JSON과 환경별 적용 설명은 repro-package 아래에 있습니다.
- API credential과 provider key는 재현 환경에서 별도 등록합니다.

## 최종 운영 환경과 재현 snapshot

최종 시연 환경에서는 Graylog R1–R12 12개 규칙을 운영했고 n8n workflow는 Published 상태였습니다. 저장소 안의 export와 재현 package는 설정을 다른 환경으로 옮기기 위한 별도 snapshot입니다.

Graylog 기본 export에는 8개 Event Definition이 있고, 재현 package에는 OBS 항목을 포함한 13개 정의가 들어 있습니다. 두 snapshot은 최종 운영 R1–R12 설정과 같은 시점의 사본이 아닙니다.

n8n도 같은 원칙으로 구분합니다. 최종 시연 workflow는 Published 상태로 실행했고, 재현 package의 66-node workflow는 credential과 실행 상태를 제외한 비활성 template입니다. 이는 운영 workflow의 상태를 나타내지 않습니다. 새 n8n 환경에서만 template을 가져와 주소·credential을 등록한 뒤 별도 확인합니다.

## AI-XDR provider

최종 AI-XDR provider 설정은 auto이며 Groq를 우선 시도하고 NVIDIA와 Ollama를 fallback으로 사용합니다. 실행별 provider와 model은 가용 설정과 호출 결과에 따라 달라집니다. AI Chat은 별도의 provider 설정을 사용합니다.

## 재현할 때 필요한 외부 조건

- Graylog Input, Stream, Event Definition과 Notification을 대상 Graylog에 맞게 설정합니다.
- n8n에서 webhook endpoint, 내부 API 주소, Ticket DB 연결과 credentials를 새 환경에 등록합니다.
- Wazuh Agent/Manager의 로그 경로와 syslog 전달 대상을 해당 호스트망에 맞춥니다.
- Suricata 로그를 사용할 경우 실제 수집 경로와 Graylog 입력을 설정합니다.
- pfSense 연동은 feed, Alias, Firewall Rule과 갱신 주기를 별도 장비에 구성합니다.
- Groq·NVIDIA 등의 API key와 DB password는 실행 환경의 secret store 또는 로컬 환경변수로 관리합니다.

## 실제 범위와 개선 지점

현재 Incident 상세는 Ticket의 latest_event와 Ticket API가 제공하는 알림 자료를 중심으로 표시합니다. 별도 원본 이벤트 테이블의 모든 로그를 펼친 완전한 시간순 timeline은 제공하지 않습니다.

pfSense feed와 앱의 blocked IP 관리 기능은 연동 기반을 제공하지만, 실제 네트워크 정책은 대상 pfSense의 Alias·Firewall Rule 구성과 장비 측 검증이 필요합니다. 재현 package를 새 PC에 적용할 때도 Graylog의 기존 설정 충돌을 먼저 확인하고 n8n workflow를 중복 활성화하지 않아야 합니다.

## 실행 및 설정 자료

- [로컬 MySQL Compose](../../docker-compose.local.yml)
- [환경 변수 예시](../../.env.example)
- [DB schema](../../db/schema.sql)
- [DB 권한 스크립트](../../db/grants.sql)
- [Graylog·Wazuh migration 자료](../../security_migration/)
- [재현 패키지 안내](../../repro-package/NEXUS-WORK-REPRO-2026-11-09/README.md)
- [R8 E2E manifest](../../repro-package/NEXUS-WORK-REPRO-2026-11-09/manifest.json)
