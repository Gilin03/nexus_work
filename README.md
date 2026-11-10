# NEXUS WORK

**NEXUS WORK**는 4인 팀으로 구현한 사내 업무 포털 기반 보안관제 프로젝트입니다. 포털과 호스트에서 나온 보안 이벤트를 규칙 탐지, Ticket 처리, AI-XDR 평가, 관리자 검토까지 연결했습니다.

<p align="center">
  <a href="https://nexus-work-portfolio-site.vercel.app"><strong>웹 포트폴리오 보기</strong></a>
  &nbsp;·&nbsp;
  <a href="https://nexus-work-portfolio-site.vercel.app/#demo">R3 시연 보기</a>
  &nbsp;·&nbsp;
  <a href="https://app.notion.com/p/3fed401b317c800f9315ce6521b41177">Notion 프로젝트 기록 (접근 권한 필요할 수 있음)</a>
  &nbsp;·&nbsp;
  <a href="docs/portfolio/README.md">기술 문서 모음</a>
</p>

<p align="center">
  <img src="docs/portfolio/assets/assessment-example.webp" alt="AI-XDR 평가 화면 예시: 연관 이벤트, 판정, 위험 점수와 관리자 승인 상태" width="100%">
</p>
<p align="center"><sub>AI-XDR 평가 화면 캡처 · 출발지, 계정, Ticket 식별값은 공개용 사본에서 가렸습니다.</sub></p>

| 팀 프로젝트 | 이벤트 흐름 | 검증 범위 |
|---|---|---|
| 4인 공동 구현 · 개인 담당은 별도 문서에 구분 | 포털·호스트 로그 → Graylog → n8n/Ticket → AI-XDR → 관리자 검토 | 최종 시연 환경의 R1–R12 운영은 참여자 제공 사실이며, 규칙별 성공 증거와 구분 |

## 프로젝트 배경과 목표

로그인·권한 거부·AI Agent Tool 호출·웹 요청은 서로 다른 위치에서 발생합니다. 개별 경보만으로는 행위의 맥락을 파악하기 어렵고, 탐지 이후의 검토와 대응 기록도 흩어질 수 있습니다. 이 프로젝트는 이벤트를 Ticket과 AI-XDR 평가로 이어 사건 단위로 확인하고, AI 권고와 실제 대응 권한을 분리하는 흐름을 구현했습니다.

## 시스템 아키텍처

~~~mermaid
flowchart LR
  subgraph Sources[이벤트 출처]
    APP[포털 애플리케이션 이벤트]
    HOST[호스트 보안 로그]
    EXT[기타 연동 로그]
  end
  W[Wazuh 호스트 수집 경로]
  G[Graylog 탐지]
  N[n8n 이벤트·Ticket 처리]
  T[(Ticket 저장소)]
  X[AI-XDR 평가·정책]
  XD[(Assessment 저장소)]
  I[Incident 조회·종결]
  A[관리자 검토·대응]
  APP --> G
  HOST --> W --> G
  EXT --> G
  G --> N --> T
  N --> X --> XD
  N --> X
  T --> I
  XD --> I
  X --> A
~~~

도식은 구성 요소의 역할을 설명합니다. 실제 운영망 주소나 pfSense의 패킷 차단을 증명하는 자료는 아닙니다.

## 실제 화면 증거

아래는 구성 화면의 공개용 캡처입니다. Graylog 이미지는 보관된 Event Definition 목록 일부라 최종 운영 규칙 전체나 개별 탐지 성공을 단독으로 증명하지 않습니다.

<p align="center">
  <img src="docs/portfolio/assets/graylog-rules.webp" alt="Graylog Event Definition 목록 일부: 인증, AI 보안, 웹 경로 탐지" width="100%">
</p>
<p align="center"><sub>Graylog Event Definition 설정 화면 일부</sub></p>

<details>
<summary>n8n workflow 전체 화면 보기</summary>
<br>
<p align="center"><img src="docs/portfolio/assets/workflow.webp" alt="Graylog 알림 수신, Ticket 처리, AI-XDR 호출 및 후속 처리를 연결한 n8n workflow 화면" width="100%"></p>
<p align="center"><sub>n8n workflow 보관 캡처 · 화면 이미지는 특정 실행 성공이나 현재 Published 상태를 단독으로 증명하지 않습니다.</sub></p>
</details>

## 주요 기술과 팀 역할

| 영역 | 기술·역할 |
|---|---|
| 업무 포털 | Flask, Python, MySQL |
| 로그·탐지 | 애플리케이션 보안 이벤트, Wazuh 호스트 로그 경로, Graylog Stream/Event Definition |
| 자동화 | n8n Webhook, Ticket 생성·병합, AI-XDR API 전달 |
| 분석·검토 | AI-XDR verdict·점수·근거·정책, 관리자 승인, Incident 화면 |
| 팀 구성 | 4인 공동 프로젝트. 김태빈의 담당 범위는 아래 개인 기여 문서에 별도로 표시 |

## 보안 이벤트 처리 흐름

1. 포털 또는 호스트에서 보안 관련 로그가 발생합니다.
2. Graylog가 이벤트 필드와 탐지 조건을 평가해 Event/Alert를 만듭니다.
3. n8n이 알림을 정리하고 Ticket을 새로 만들거나 기존 사건에 연결합니다.
4. 처리 가능한 이벤트 묶음을 AI-XDR로 전달하고 평가 결과를 저장합니다.
5. 관리자는 평가와 정책 상태를 검토하고 허용된 절차로 대응합니다. Incident는 이력 조회와 종결을 담당합니다.

최종 시연 환경에서 R1–R12 12개 Graylog 규칙을 운영하고 n8n workflow를 Published 상태로 사용했다는 사실은 프로젝트 참여자가 제공했습니다. 이는 각 규칙 또는 모든 workflow 실행의 개별 성공을 뜻하지 않습니다. 저장소 snapshot의 범위와 실행 증거는 [탐지 규칙 문서](docs/portfolio/03-detection-catalog.md)에서 구분합니다.

## 대표 검증 시나리오

저장된 2026-11-09 로컬 재현 기록에는 TEST-NET 출발지로 404 요청 30건을 발생시킨 R8 흐름이 있습니다. Graylog Event, n8n Ticket 처리, AI-XDR `/events`·`/process`, assessment 저장까지 연결됐고 결과는 `BENIGN`, score 10, confidence 0.80, `NO_ACTION`이었습니다. 실제 IP 차단이나 계정 잠금은 발생하지 않았습니다. [비식별 실행 요약](docs/portfolio/assets/r8-local-e2e-summary.json)

이 기록은 한 로컬 합성 시나리오입니다. 전체 R1–R12 PASS, 운영 pfSense 차단 또는 다른 PC에서의 재현을 의미하지 않습니다.

## 기술 문서

- [프로젝트 배경과 김태빈의 기여](docs/portfolio/01-project-and-contribution.md)
- [아키텍처와 로그 흐름](docs/portfolio/02-architecture-and-logs.md)
- [Graylog R1–R12 탐지 규칙](docs/portfolio/03-detection-catalog.md)
- [n8n 자동화와 AI-XDR](docs/portfolio/04-automation-and-ai-xdr.md)
- [Incident 데이터와 대응 이력](docs/portfolio/05-incident-and-response.md)
- [검증 결과와 트러블슈팅](docs/portfolio/06-validation-and-troubleshooting.md)
- [로컬 실행·재현 및 한계](docs/portfolio/07-reproduction-and-limitations.md)
- 별도 메신저 API의 범위가 필요하면 [API 문서](docs/02_메신저_API.md)를 참고하세요.

## 로컬 실행

다음 절차는 포털과 분리된 로컬 MySQL을 실행하는 개발용 예시입니다. Graylog, n8n, Wazuh, Suricata, pfSense는 이 Compose 파일에서 시작되지 않으며 별도 환경이 필요합니다.

PowerShell에서 프로젝트 루트 기준:

~~~powershell
Copy-Item .env.example .env
# .env에서 로컬 전용 비밀값을 설정하고 DB_PORT를 3308로 지정합니다.
docker compose -f docker-compose.local.yml up -d
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
~~~

포털은 기본적으로 `http://127.0.0.1:5070`에서 실행됩니다. 로컬 Compose의 MySQL은 `127.0.0.1:3308`에만 바인딩되고 컨테이너 내부 포트는 3307입니다. 따라서 앱의 `.env`에 `DB_HOST=127.0.0.1`, `DB_PORT=3308`을 설정해야 합니다. 실제 비밀번호·`SECRET_KEY`·API key는 각자 생성해 로컬 `.env`에만 두고 저장소에는 올리지 마세요.

시연용 데이터가 필요한 경우에만 폐기 가능한 로컬 DB에 seed를 실행합니다. 초기화 옵션은 사용하지 마세요.

~~~powershell
python scripts/seed.py --db nexus
~~~

seed는 로컬 DB에 시험 데이터를 추가합니다. `.env`의 `SEED_*_PW` 값은 공유·운영 환경에서 반드시 직접 설정하세요. 테스트는 로컬 환경을 준비한 뒤 다음 명령으로 실행할 수 있습니다.

~~~powershell
python -m pytest -q
~~~

이 저장소 변경 작업에서는 테스트를 실행하지 않았으므로 테스트 통과 여부나 개수를 주장하지 않습니다. 전체 절차와 외부 구성요소의 재현 한계는 [실행·재현 문서](docs/portfolio/07-reproduction-and-limitations.md)에 있습니다.

## 검증 범위와 한계

- 현재 코드, 참여자가 제공한 최종 운영 환경 정보, 저장된 개별 실행 기록을 문서에서 구분합니다.
- AI-XDR의 `auto` provider 우선순위는 Groq → NVIDIA → Ollama입니다. 개별 평가에서 실제 선택된 provider는 해당 실행 기록으로 판단해야 하며, AI Chat은 별도 설정입니다.
- Incident의 탐지 이력은 현재 코드가 제공하는 Ticket/API 자료 범위에 따릅니다. 완전한 원본 이벤트 타임라인으로 과장하지 않습니다.
- 앱의 blocked IP API/feed는 pfSense의 Alias·방화벽 규칙이 실제 설정됐거나 패킷이 차단됐다는 증거가 아닙니다.
- 다른 PC에서 전체 시스템을 재현한 결과와 각 R1–R12 개별 PASS는 이 저장소의 문서만으로 확인되지 않았습니다.
- GitHub 공개 전에는 Git 이력의 비밀값, 예제 자격정보, 내부 주소, 오래된 캡처와 보안 보고서를 별도로 검토해야 합니다.
