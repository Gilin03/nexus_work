# n8n 자동화와 AI-XDR 평가

## n8n이 연결하는 단계

최종 시연 환경에서 n8n workflow는 Published 상태로 운영됐다는 정보를 프로젝트 참여자가 제공했습니다. Published 상태는 운영 workflow가 배포된 상태였다는 뜻입니다. 특정 이벤트가 Ticket 저장, AI-XDR 분석, Discord 알림까지 모두 성공했다는 증거는 execution별로 따로 확인해야 합니다.

~~~mermaid
sequenceDiagram
  participant G as Graylog
  participant N as n8n Published workflow
  participant T as Ticket DB
  participant X as AI-XDR API
  participant D as AI-XDR DB
  participant A as 관리자 화면

  G->>N: Event/Alert webhook
  N->>N: 필드 검사·정규화
  N->>T: 새 Ticket 또는 기존 Ticket 갱신
  N->>X: POST /events + ticket_ids
  X->>D: 이벤트 저장
  N->>X: POST /process (처리 가능한 window)
  X->>D: 이벤트 조회·assessment 저장
  X-->>N: processed·assessment 결과
  N->>T: Ticket 후처리와 대응 기록
  D-->>A: AI-XDR 결과 조회
~~~

n8n은 흐름 조율과 데이터 전달을 담당합니다. AI 위험 점수나 정책 조건을 n8n에서 다시 계산하지 않습니다.

![AI-XDR 평가 화면](assets/assessment-example.webp)

*평가 결과와 관리자 조치 영역의 화면 캡처 예시입니다. 한 건의 화면이 모든 실행의 provider나 결과를 대표하지 않습니다.*

## Ticket과 correlation key

| 필드 | 역할 |
|---|---|
| numeric id | Ticket DB 안의 행 PK. 다른 DB의 numeric id와 직접 비교할 수 없음 |
| ticket_key | 같은 IP/user 등으로 이벤트를 묶는 grouping key. 예: ip:… |
| NX-DB-xxxxxx | 화면 표시 및 서로 다른 시스템 사이의 외부 Ticket 식별자 |

AI-XDR 이벤트와 Ticket을 연결할 때 외부 표시 ID를 ticket_ids[]로 보존할 수 있습니다. ticket_key와 NX-DB 표시 ID는 목적이 다르므로 직접 JOIN key로 혼용하지 않습니다.

## events와 process

1. n8n은 Graylog 이벤트의 Rule, alert 식별자, 출발지, 사용자, event_type 등 필요한 필드를 정리합니다.
2. AI-XDR events API는 입력을 검증한 뒤 이벤트를 저장합니다.
3. /process는 지금 처리 가능한 window를 선택해 관련 이벤트를 조회하고 assessment를 만듭니다.
4. 응답에는 processed 수와 assessment 결과가 포함될 수 있습니다.
5. n8n은 반환된 Ticket ID와 assessment 정보를 연결해 후속 Ticket 처리나 설정된 알림 분기로 넘길 수 있습니다.

관련 구현은 [internal API](../../app/internal_api.py)와 [AI-XDR 처리](../../app/ai_xdr.py)에서 확인할 수 있습니다.

## 시간값은 각각 따로 봐야 합니다

다음 설정은 서로 다른 의미입니다.

- Ticket 병합 기간: 후속 경보를 기존 Ticket에 합칠 기준
- n8n Schedule 간격: 처리 가능한 window가 있는지 확인하는 실행 간격
- AI-XDR triage window: 한 assessment에 넣을 이벤트 시간 범위
- HTTP timeout: 응답을 기다리는 최대 시간

저장소의 XDR_TRIAGE_WINDOW_SECONDS 기본값은 60초이고 재현용 비활성 workflow에도 1분 Schedule이 있습니다. 과거 작업 중 3분 집계 설명과 1분 설정이 모두 사용됐습니다. 최종 Published workflow의 설정값을 확인할 수 있는 운영 export가 이 저장소에는 없으므로 현재 운영 window를 임의로 1분 또는 3분이라고 단정하지 않습니다.

## AI-XDR provider와 fail-safe

AI-XDR은 채팅과 별도인 XDR_AI_PROVIDER 설정을 사용합니다. 최종 시연 환경에 대해 제공된 설정은 auto이며 fallback 우선순위는 **Groq → NVIDIA → Ollama**입니다. Groq 우선은 모든 실행이 Groq였다는 뜻이 아닙니다. 개별 provider/model은 해당 실행의 진단 기록으로 확인해야 합니다.

AI Chat은 AI_PROVIDER 설정을 별도로 사용합니다. AI Chat이 Groq를 썼더라도 AI-XDR이 같은 provider를 사용했다고 가정하지 않습니다.

코드 흐름은 다음과 같습니다.

1. 처리 대상 이벤트와 summary 준비
2. 선택 provider 호출
3. JSON parse와 strict schema validation
4. verdict, threat_score, confidence, reasoning, recommended_actions 생성
5. policy 결과와 assessment 저장
6. 호출 오류 또는 schema 오류는 fail-safe REVIEW 경로로 처리

## AI 권고, 정책, 실행은 분리

recommended_actions의 block_ip는 분석 권고입니다. 이것만으로 IP를 바로 차단하지 않습니다.

- AI-XDR은 AI 평가와 서버 정책 결과를 구분합니다.
- 주간 대응은 관리자 승인 흐름을 사용합니다.
- 코드에는 자동대응 후보 경로와 security.block_ip() 연동이 있습니다. 실제 실행 여부는 policy, live mode, IP block gate, 시간대, 보호 IP, 현재 운영 설정에 달려 있습니다.
- 코드 기본값·재현 template 설정과 운영 환경의 실제 .env는 서로 다른 증거입니다.
- pfSense feed API가 있어도 실제 Alias와 방화벽 Rule이 연결됐다는 뜻은 아닙니다.

## 알림

저장소와 작업 자료에는 평가 결과를 Ticket 정보와 합쳐 Discord 메시지를 만드는 분기와 gate가 있습니다. 최종 Published에서 실제 전송된 개별 메시지는 execution과 HTTP 결과가 있을 때만 성공으로 표시해야 합니다. 재현 template의 Discord gate는 비활성 구성과 다를 수 있습니다.

## 코드·자료 근거

- [AI-XDR config](../../app/config.py)
- [provider fallback과 triage](../../app/ai_xdr.py)
- [events/process API](../../app/internal_api.py)
- [Ticket DB schema](../../db/schema.sql)
- [n8n 비활성 재현 template](../../repro-package/NEXUS-WORK-REPRO-2026-11-09/n8n/NEXUS-v3-portable-template-inactive.json)
- [재현 package n8n 안내](../../repro-package/NEXUS-WORK-REPRO-2026-11-09/n8n/README.md)

재현 template은 66-node 비활성 파일입니다. 운영 당시 Published workflow를 나타내지 않으며, credential이나 운영 execution state를 포함하지 않습니다.
