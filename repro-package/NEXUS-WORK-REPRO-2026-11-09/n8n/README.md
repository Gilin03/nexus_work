# n8n 설정하기 — 쉬운 안내

## 먼저, 내 상황을 고르세요

### 이미 사용 중인 n8n이 있다면

**이 패키지의 workflow를 가져오지 마세요.** 이미 켜진 workflow와 주소를 그대로 둡니다. 같은 workflow를 또 가져오면 경보나 Ticket 처리가 중복될 수 있습니다.

### 새 n8n을 따로 준비하는 경우에만

아래 순서로 설정합니다. 이 파일은 n8n을 설치하거나 포털·MySQL을 준비해 주지는 않습니다.

## 설정하면 무엇이 되나요?

연결이 끝나면 새 n8n은 다음 일을 합니다.

**Graylog 경보 받기 → Ticket 저장 → 포털로 이벤트 전달 → AI-XDR 처리**

Discord 알림과 실제 IP 차단·계정 잠금은 꺼진 상태로 시작합니다. 설정을 시험할 때도 이 상태를 유지하세요.

## 새 n8n 설정 순서

### 1) 먼저 준비합니다

- 포털과 복제 MySQL을 실행합니다.
- n8n에서 접근할 포털 주소와 MySQL 주소를 확인합니다.
- Graylog 관리자 API 키가 아니라, 이 workflow에서 사용할 내부 API 토큰을 준비합니다.
- 원본 운영 DB가 아닌 **복제 DB**를 사용합니다.

### 2) 템플릿을 가져옵니다

n8n에서 **Import from File**을 선택하고 `NEXUS-v3-portable-template-inactive.json`을 가져옵니다. 가져온 뒤 workflow가 **비활성(Inactive)** 상태인지 확인하고, 아직 켜지 마세요.

### 3) 연결 정보를 등록합니다

workflow가 DB와 포털에 접속할 수 있도록 n8n의 Credentials 화면에서 연결 정보를 만듭니다. 비밀번호와 토큰은 패키지에 없으므로 각 PC에서 직접 입력합니다.

| 연결 대상 | n8n에 등록할 것 | 연결할 곳 |
|---|---|---|
| Ticket 저장소 | MySQL 로그인 정보 | 새 PC의 복제 MySQL |
| 포털 / AI-XDR | HTTP Bearer 인증 토큰 | 새 PC의 포털 내부 API |
| Graylog 경보 수신 | HTTP Header 인증 정보 | n8n Webhook |
| Discord | 선택 사항 | 이번 기본 설정에서는 연결하지 않음 |

Credential 이름은 알아보기 쉽게 정하면 됩니다. 예시 주소 `host.docker.internal:3308`, 포털 주소 `http://host.docker.internal:5070`은 이 PC의 Docker 구성용입니다. 다른 PC에서는 그 PC의 주소로 바꿔야 합니다.

### 4) 노드의 주소와 Credential을 확인합니다

가져온 workflow에서 MySQL 노드는 복제 DB를, AI-XDR API 노드는 새 포털을 바라보게 설정하고 위에서 만든 Credential을 연결합니다. 원본 운영 DB Credential을 재사용하거나 덮어쓰지 마세요.

### 5) Graylog 경보를 새 Webhook으로 연결합니다

n8n Webhook 주소를 확인한 뒤, Graylog의 알림이 그 주소로 경보를 보내도록 설정합니다. 이 연결이 없으면 workflow를 가져와도 Graylog 경보가 n8n에 도착하지 않습니다.

### 6) 안전하게 확인한 뒤 사용합니다

workflow를 켜기 전에 주소와 인증이 맞는지 확인하고, 무해한 테스트 이벤트로 실행 결과를 확인합니다. 기존 workflow와 같은 경보를 받지 않는지 확인한 뒤에만 새 workflow를 활성화합니다. 실제 차단이나 계정 잠금은 별도 안전 검토 전까지 켜지 마세요.

## 이 패키지에 없는 것

- n8n 비밀번호·토큰·Credential
- Groq API 키
- 운영 DB 데이터
- 기존 workflow의 실행 이력과 내부 상태

각 PC에서 새 Credential을 만들고, 그 PC에서 허용된 주소를 입력해야 합니다.

## 현재 작업 PC에서 확인한 내용

2026-11-09 확인 당시 활성 workflow는 `NXv3AiXdr27Qp6Lm`이었고, 기존 workflow를 유지한 채 로컬 복제 DB와 포털을 사용하도록 전환되어 있었습니다. 재현용 템플릿은 별도 PC에서 검토하기 위한 비활성 사본입니다. 이 안내는 다른 PC에서 실제 실행해 검증한 결과가 아닙니다.
