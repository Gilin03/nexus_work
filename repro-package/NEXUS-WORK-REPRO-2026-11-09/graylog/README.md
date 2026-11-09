# Graylog 설정 적용하기

## 이 파일로 무엇을 하나요?

이미 실행 중인 Graylog에 NEXUS의 로그 입력, Stream, 탐지 규칙을 준비합니다.

- 먼저 현재 설정과 패키지 설정을 비교합니다. 이때는 아무것도 바뀌지 않습니다.
- 확인이 끝난 뒤 적용하면, Graylog에 없는 항목만 추가합니다.
- 기존 설정은 수정하거나 삭제하지 않습니다.
- n8n과 Discord 알림은 연결하지 않습니다.

Graylog가 Docker에서 실행 중이어도 사용할 수 있습니다. Docker가 아니라 Graylog 웹 주소에 접속합니다.

## 처음 하는 경우: 아래 순서만 따라 하세요

### 1) 압축을 풀고 폴더를 엽니다

ZIP 압축을 푼 다음, 안에 있는 `graylog` 폴더를 엽니다. 그 폴더에서 PowerShell을 실행합니다.

### 2) Graylog 주소와 관리자 API 토큰을 준비합니다

- Graylog가 이 PC에서 열리면 주소는 보통 `http://localhost:9000`입니다.
- 다른 PC의 Graylog라면 그 Graylog의 웹 주소를 사용합니다.
- API 토큰은 Graylog 관리자에게 받습니다. 비밀번호와 API 토큰은 다른 값입니다.

### 3) 먼저 안전 확인을 실행합니다

아래를 PowerShell에 그대로 붙여넣습니다. 토큰 입력 창에서는 토큰을 입력하고 Enter를 누릅니다. 입력한 값은 화면에 표시되지 않습니다.

```powershell
$secure = Read-Host "Graylog API token" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $env:GRAYLOG_API_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    .\import_graylog.ps1 -GraylogUrl "http://localhost:9000" -DryRun -PackageRoot $PWD
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    $secure.Dispose()
    Remove-Item Env:GRAYLOG_API_TOKEN -ErrorAction SilentlyContinue
}
```

Graylog가 다른 주소라면 명령의 `http://localhost:9000`만 실제 주소로 바꿉니다. 이 실행은 설정을 읽어 비교만 하며 Graylog를 바꾸지 않습니다.

### 4) 결과에 따라 결정합니다

| 결과 | 뜻 | 다음에 할 일 |
|---|---|---|
| `NO-OP` 또는 `REUSE` | 필요한 설정이 이미 있고 사용할 수 있습니다. | 그대로 둡니다. |
| `CREATE` | Graylog에 없는 설정입니다. 적용하면 새로 추가됩니다. | 추가하려던 항목이 맞는지 확인합니다. |
| `CONFLICT` | Graylog에 비슷한 설정이 있지만 내용이 다릅니다. | **적용하지 말고 멈춥니다.** 관리자와 차이를 확인합니다. |

### 5) 충돌이 없을 때만 적용합니다

DryRun 결과에 `CONFLICT`가 **하나도 없고**, `CREATE` 항목이 추가하려던 설정이 맞을 때만 위 명령을 다시 실행합니다. 이번에는 명령의 `-DryRun`을 `-Apply`로 바꿉니다. 적용 후 Graylog에 빠져 있던 NEXUS 설정이 추가됩니다.

`CONFLICT`가 하나라도 있으면 Apply하지 마세요. 기존 설정을 지우거나 바꾸지 말고, 충돌 내용을 Graylog 관리자에게 전달하세요.

## 이 PC에서 확인된 결과

2026-11-09에 현재 실행 중인 Graylog를 읽어 확인했습니다.

- 입력 3개와 Stream 3개는 이미 맞아 재사용할 수 있습니다.
- R1~R12 탐지 규칙은 알림 연결 설정이 달라 충돌합니다.
- R10은 그룹 기준도 패키지와 다릅니다.
- 따라서 **이 PC에서는 Apply하지 않았고 Graylog 설정도 바꾸지 않았습니다.**

다른 PC에 적용할 때는 그 PC의 Graylog 주소로 3단계 DryRun부터 실행하세요. 다른 PC의 결과는 아직 확인되지 않았습니다.

## Graylog가 아직 없는 PC

먼저 Graylog를 설치하고 실행해야 합니다. 이 패키지는 Graylog 설치 프로그램이 아닙니다.

## n8n은 별도입니다

이 안내는 Graylog 설정만 다룹니다. 이미 사용 중인 n8n workflow를 가져오거나 바꾸지 마세요. 새 n8n을 별도로 준비할 때만 `../n8n/README.md`를 참고하세요.
