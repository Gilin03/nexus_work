# 실행과 재현

## 재현 범위

저장소의 로컬 재현 패키지는 포털과 격리 MySQL, 기존 Graylog·n8n 연결 자료를 포함합니다. Graylog, n8n, Wazuh, Suricata, pfSense 전체를 새 PC에 설치하는 완전한 VM 이미지는 아닙니다.

다른 PC에서의 전체 재현은 이 문서 작성 시점에 실행하지 않았습니다.

## 포털과 복제 MySQL

현재 로컬 구성의 근거는 [재현 package README](../../repro-package/NEXUS-WORK-REPRO-2026-11-09/README.md)와 [local Compose](../../docker-compose.local.yml)입니다.

일반적인 준비 순서:

1. Python, Docker를 준비하고 프로젝트 의존성을 설치합니다.
2. .env.example을 참고해 로컬 .env를 만들고 각자 생성한 MySQL root/app/conf 암호와 SECRET_KEY를 입력합니다. 격리 Compose를 사용할 때는 `DB_HOST=127.0.0.1`, `DB_PORT=3308`을 설정합니다. 연동을 실제로 구성할 때만 해당 시스템의 주소와 별도 credential을 추가합니다. 기존 키나 팀 자격 증명을 복사하지 않습니다.
3. 복제 MySQL만 별도 Compose로 시작합니다.

~~~powershell
docker compose -f docker-compose.local.yml up -d
~~~

4. Python 가상 환경을 준비한 뒤 Flask 포털을 시작합니다.

~~~powershell
python run.py
~~~

이 저장소의 격리 Compose 기준으로 MySQL은 호스트 `127.0.0.1:3308`에만 바인딩되고 컨테이너 내부 포트는 3307입니다. Flask 설정은 `.env`의 `DB_HOST=127.0.0.1`, `DB_PORT=3308`을 사용하고 포털 기본 주소는 `http://127.0.0.1:5070`입니다. 이 값은 해당 로컬 재현 구성의 기준이며 다른 PC의 운영 주소로 사용하지 않습니다. MySQL을 전체 네트워크 인터페이스에 공개하지 않습니다.

테스트를 실행할 때는 로컬 DB와 Python 의존성을 준비한 뒤 `python -m pytest -q`를 사용합니다. DB 의존 테스트는 초기화된 로컬 테스트 환경이 필요할 수 있습니다. 이번 문서 정리에서는 테스트를 실행하지 않았습니다.

## Graylog

재현 패키지의 Graylog 자료는 이미 실행 중인 Graylog를 대상으로 설정을 비교·적용하는 도구입니다.

- 먼저 package의 안내를 읽고 DryRun을 실행합니다.
- 충돌이 나오면 기존 Input, Stream, Event Definition을 변경하거나 덮어쓰지 말고 원인을 확인합니다.
- 현재 PC에서는 기존 Event Definition과의 충돌이 보고되어 Apply하지 않았습니다.
- 다른 PC의 충돌 여부는 그 PC에서 DryRun하기 전까지 알 수 없습니다.
- 저장소 기본 export 8개, 재현 패키지 13개는 서로 다른 snapshot입니다.

세부 절차: [Graylog 쉬운 적용 안내](../../repro-package/NEXUS-WORK-REPRO-2026-11-09/graylog/README.md)

## n8n

- 최종 시연 환경은 Published workflow를 사용했다는 운영자 제공 정보입니다.
- 현재 패키지의 66-node workflow는 credential과 static execution state가 빠진 비활성 재현 template입니다.
- 이미 사용 중인 n8n에 template을 중복 import하거나 기존 workflow를 활성화하지 않습니다.
- 새 재현 환경에서만 비활성 상태로 가져와 endpoint와 별도 credential을 등록하고, 안전한 테스트를 마친 뒤 운영자 검토를 받습니다.
- package와 README에는 n8n credential, token, Groq key, DB dump가 포함되지 않습니다.

세부 절차: [n8n 쉬운 안내](../../repro-package/NEXUS-WORK-REPRO-2026-11-09/n8n/README.md)

## 저장된 시나리오와 안전 조건

2026-11-09 package manifest에는 TEST-NET 기반 R8 합성 404 시나리오가 기록돼 있습니다. Graylog R8 Event, n8n Ticket 처리, AI-XDR /events·/process, assessment 저장까지 연결됐고 실제 IP 차단·계정 잠금은 없었습니다.

이 기록은 특정 PC의 한 실행입니다. 전체 R1–R12 재현, 다른 PC 호환성, pfSense 실차단을 보장하지 않습니다. AI-XDR provider 선택은 실행 환경의 XDR_AI_PROVIDER와 API key/model 설정에 따라 달라집니다.

## 공개 전 남은 확인

- repository 전체와 Git history에서 credential/secret 검사
- 기존 내부 IP, 계정명, local paths, Ticket/assessment IDs 포함 파일 검토
- docs/evidence 캡처와 오래된 아키텍처 이미지의 공개 범위 검토
- VULN-FINDINGS 원문과 개인/팀 작업 기록의 공개 제외 또는 안전한 요약
- 다른 PC에서 Graylog DryRun과 비활성 n8n template 연결 절차 검증
- pfSense Alias·Rule, feed 갱신, 만료·해제의 테스트망 실증

이번 단계에서는 비밀값을 읽거나 출력하지 않았고, 운영 Graylog/n8n에 요청을 보내지 않았습니다.

## 증거 파일과 코드

- [재현 패키지](../../repro-package/NEXUS-WORK-REPRO-2026-11-09/)
- [Flask 실행 entry point](../../run.py)
- [local MySQL Compose](../../docker-compose.local.yml)
- [DB schema](../../db/schema.sql)
- [DB grants](../../db/grants.sql)