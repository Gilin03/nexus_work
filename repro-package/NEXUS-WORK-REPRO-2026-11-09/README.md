# NEXUS WORK 로컬 재현 패키지

패키지 기준일: 2026-11-09  
기준 checkout: **C:\ktb\1_nexus_work\nexus_work**

## 이 PC에서 확인한 구성

| 구성요소 | 로컬 연결 | 상태 |
|---|---|---|
| Flask 포털 / AI-XDR | 브라우저 http://127.0.0.1:5070, n8n 컨테이너 http://host.docker.internal:5070 | healthz HTTP 200 |
| 격리 MySQL 복제본 | 호스트 127.0.0.1:3308, 컨테이너 내부 MySQL 포트 3307 | nexus-mysql-local; 원본 nexus-mysql / 3307과 별도 |
| Graylog | 기존 실행 인스턴스 | 포털 GELF 로그 및 R8 이벤트 검색 확인 |
| n8n | 기존 실행 인스턴스, 포트 5678 | 활성 Published v3를 로컬 복제 DB와 포털 API에 전환 |

Flask는 프로젝트 가상환경에서 python run.py로 실행합니다. MySQL 복제본은 루프백에만 포트를 게시하며, 기존 MySQL 컨테이너와 volume은 그대로 유지했습니다. Graylog와 n8n은 재설치하거나 재시작하지 않았습니다.

## 활성 n8n v3 로컬 전환

- workflow ID NXv3AiXdr27Qp6Lm와 production webhook 경로를 유지했습니다.
- 기존 Ticket DB 처리 노드 8개를 격리 복제 DB용 credential로 연결했습니다.
- AI-XDR events, process, decision 등 내부 API 노드 4개를 로컬 Flask로 연결했습니다.
- DB와 API credential은 n8n에 별도로 등록했습니다. 원래 credential 값을 덮어쓰거나 패키지에 내보내지 않았습니다.
- 원본 DB와 이전 실행 데이터는 전환/검증 과정에서 수정하지 않았습니다.
- AI-XDR Discord 분기는 게시된 workflow에서 강제로 닫았습니다. 재현용 템플릿에도 실행 상태/static data나 credential은 포함하지 않습니다.
- 안전 설정은 response_mode=dry-run, live_enabled=false, ip_block_enabled=false를 유지합니다.

## 최소 실측 결과

안전한 TEST-NET 출발지 198.51.100.250로 고유한 존재하지 않는 로컬 경로 30개를 요청해 R8 경로를 검증했습니다.

1. Graylog에서 not_found 원본 로그와 R8 경보를 확인했습니다.
2. n8n 실행 #4409에서 Ticket NX-DB-000365가 복제 DB에 기록되고 AI-XDR /events가 accepted=true를 반환했습니다.
3. 다음 실행 #4410에서 /process는 processed=1을 반환했습니다.
4. assessment ca054404-d842-4766-a270-b3f5f03d62a2가 Ticket과 연결돼 저장됐습니다: R8 / BENIGN / score 10 / confidence 0.80 / NO_ACTION.
5. 실제 IP 차단이나 계정 잠금은 발생하지 않았습니다.

검증 중 저장된 AI-XDR Discord 활성 값 때문에 평가 후 Discord 노드가 한 번 실행된 것을 발견했습니다. 즉시 해당 분기를 게시된 workflow에서 강제로 닫았고, 이후 추가 Discord 전송은 하지 않았습니다. 현재 템플릿도 Discord 분기가 닫힌 상태입니다.

## 다른 PC에서 설정을 적용하는 방법

### 한눈에 보기

1. Graylog가 실행 중인지 확인합니다.
2. 먼저 `DryRun`으로 미리 확인합니다. 이 단계에서는 아무 설정도 바뀌지 않습니다.
3. 결과에 `CONFLICT`가 있으면 멈춥니다. 충돌이 없고 추가할 항목이 맞을 때만 `Apply`합니다.

**Apply 후에는** 대상 Graylog에 없던 NEXUS 입력·Stream·탐지 규칙이 추가됩니다. 이미 있는 설정은 덮어쓰거나 삭제하지 않습니다. n8n, Discord 알림, 자격 증명은 연결되지 않습니다.

자세한 실행 명령은 [Graylog 쉬운 적용 안내](graylog/README.md)에 있습니다. Graylog가 Docker에서 실행 중이어도 Graylog 웹/API 주소로 접속하므로 그대로 사용할 수 있습니다.

**현재 작업 PC에서는 Apply하지 마세요.** 이미 있는 입력·Stream은 일치하지만 R1~R12 정의가 충돌합니다. 다른 PC의 상태는 확인하지 않았으므로, 그 PC에서 먼저 DryRun해야 합니다.

### Graylog가 아직 없는 PC라면

먼저 Graylog를 설치하고 실행해야 합니다. 이 패키지는 Graylog 설치 프로그램이 아니며, 이미 켜진 Graylog에 설정을 넣는 도구입니다.

### n8n은 별도 작업입니다

이미 사용하는 n8n이 있으면 현재 활성 workflow를 그대로 둡니다. 새 PC에 새 n8n을 만드는 경우에만 템플릿을 비활성 상태로 가져와 검토합니다. 자격 증명은 대상 PC에서 직접 등록해야 합니다.

새 n8n 준비 단계는 `n8n/README.md`를 참고하세요.

## 제외 및 보안

- Wazuh, Suricata, pfSense 전체 서버/VM과 데이터는 이 패키지 범위에 포함하지 않습니다.
- .env, API 키, n8n credential, DB dump, n8n 실행 static data는 공유 파일에 포함하지 않습니다.
- 다른 PC에서는 각자 소유한 Groq API key와 내부 API 토큰을 로컬 .env/credential store에 등록해야 합니다. 이 PC에서는 Groq key가 설정되어 있지만 XDR_AI_PROVIDER는 명시되지 않아 코드의 기본 provider 선택이 적용됩니다. 실제 provider 선택을 확정한 기록은 없습니다.
- MySQL은 127.0.0.1:3308에만 게시합니다. n8n 컨테이너에서 접근할 때는 host.docker.internal:3308을 사용합니다.
- 패키지의 n8n workflow는 비활성 상태이며 자격 증명이 제거돼 있습니다. 검토 없이 import/activate하지 마세요.
