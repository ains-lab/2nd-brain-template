# 4주차 — Hermes cron으로 반복 실행하기

> 앞 단계: [실습](03-hands-on.md)의 demo 검증과 각 활성 플랫폼의 live 1회 검증을 완료한다.
> 아래 명령은 **사용자가 실행할 설치·등록 절차**다. 이 자료를 작성하면서 실제 cron을 생성하거나 기존 gateway를 재시작하지 않았다.

## 1. 어디에서 실행되는지 먼저 확인

```bash
hermes --version
hermes cron create --help
hermes cron status
hermes gateway status
```

공식 문서보다 로컬 버전이 오래되면 옵션이 다를 수 있다. 이 자료 작성 환경의 `hermes cron create --help`에서 `--script`, `--no-agent`, `--deliver`, `--workdir`를 확인했다.

**cron의 script는 `$HERMES_HOME/scripts/` 안에 있어야 한다.** 저장소의 `class/4w/lab/pipeline.py` 절대 경로를 바로 `--script`에 넣거나 외부 파일로 심볼릭 링크하는 방식은 피한다. 프로필 scripts 폴더에 작은 wrapper를 복사하고 wrapper가 설치된 수집기를 호출한다.

- 기본 프로필: 보통 `~/.hermes/scripts/`.
- 이름 있는 프로필: 그 프로필의 실제 `HERMES_HOME`과 동일한 CLI/gateway를 사용한다.
- 아래 실습은 **기본 프로필** 기준이다. 다른 프로필에 무심코 복사하지 않는다.
- Docker에서는 호스트와 컨테이너의 `HOME`, 경로, 볼륨이 다르다. cron script가 실행되는 환경에 코드·config·데이터 경로를 배치한다. 대화형 terminal의 Docker backend 설정이 script-only cron에도 자동 적용된다고 가정하지 않는다.

## 2. 저장소 밖에 실행 사본 설치

저장소 루트에서 실행한다. 기존 운영 사본이 있으면 덮어쓰기 전에 비교·백업한다. 아래 명령은 최초 설치에서만 실행한다.

```bash
export SNS_ROOT="$HOME/.local/share/hermes-sns"
export HERMES_PROFILE_HOME="${HERMES_HOME:-$HOME/.hermes}"
mkdir -p "$SNS_ROOT/lab" "$HERMES_PROFILE_HOME/scripts"
chmod 700 "$SNS_ROOT" "$SNS_ROOT/lab"
cp class/4w/lab/pipeline.py "$SNS_ROOT/lab/pipeline.py"
cp class/4w/lab/wiki_pipeline.py "$SNS_ROOT/lab/wiki_pipeline.py"
cp class/4w/lab/keywords.example.json "$SNS_ROOT/keywords.json"
cp class/4w/examples/run-sns.py "$HERMES_PROFILE_HOME/scripts/sns-collect.py"
chmod 600 "$SNS_ROOT/keywords.json" "$HERMES_PROFILE_HOME/scripts/sns-collect.py"
python3 "$SNS_ROOT/lab/wiki_pipeline.py" init \
  --wiki-dir "$SNS_ROOT/live-wiki" --schema SCHEMA.md --mode live
```

[wrapper 원본](examples/run-sns.py)은 Python 표준 라이브러리만 사용하며 현재 Hermes Python으로 **수집 → SQLite 커밋 → raw export**를 순차 실행한다. config, `live-data`, `live-wiki`는 `$HOME/.local/share/hermes-sns/` 아래에서 찾는다. wrapper는 토큰 파일을 직접 읽지 않으며 위키를 자동 초기화하지 않는다. `init`은 새 위키에서 한 번만 실행하고 기존 위키에서는 생략한다.

수집 exit 1(부분 수집/검색 실패)이어도 커밋된 자료의 raw export는 시도하지만 **최종 종료 코드는 실패로 유지**한다. 설정 오류 등 exit 2에서는 export를 건너뛴다. export 자체가 실패해도 nonzero다. 기존 raw를 덮어써 오류를 숨기지 말고 원인을 확인한다. 이 wrapper는 `prepare`, 모델 호출, canonical 편집, `finish`를 수행하지 않는다.

키워드 config를 개인 편집기로 열어 원하는 검색어와 활성 플랫폼만 남긴다. 토큰은 config에 쓰지 않는다. `chmod 600`이어도 Python 인터프리터로 실행하므로 실행 비트는 필요 없다.

## 3. 인증정보를 gateway에 전달

터미널에서 한 `export`는 **이미 실행 중인 gateway에 소급 적용되지 않는다.** 프로필의 `.env` 또는 지원되는 외부 secret store에 사용자가 직접 값을 넣는다. 채팅·강의 파일·명령 인자·Git에는 토큰을 적지 않는다.

이 실습에서 사용하는 환경변수 이름:

| 변수 | 쓰임 |
| --- | --- |
| `X_BEARER_TOKEN` | X 검색 API 인증 |
| `THREADS_ACCESS_TOKEN` | Threads 검색 API 인증 |
| `REDDIT_ACCESS_TOKEN` | Reddit OAuth 액세스 토큰 |
| `REDDIT_USER_AGENT` | Reddit 앱과 운영자를 식별하는 문자열 |

`hermes config edit`로 기존 설정을 보존하면서 다음 허용 목록을 **병합**한다. 기존 `terminal` 블록을 새로 중복 생성하거나 기존 allowlist를 지우지 않는다.

```yaml
terminal:
  env_passthrough:
    - X_BEARER_TOKEN
    - THREADS_ACCESS_TOKEN
    - REDDIT_ACCESS_TOKEN
    - REDDIT_USER_AGENT
```

공식 cron 문서는 script subprocess 환경이 정리되므로 서비스용 변수도 `terminal.env_passthrough`로 명시하라고 안내한다. 이 설정은 해당 프로필의 terminal 도구에도 노출 범위를 늘리므로 필요한 변수만 허용한다. LLM 제공자 API 키나 gateway 토큰을 수집기에 전달하지 않는다.

설정을 적용할 필요가 있을 때만, 다른 작업이 실행 중이지 않은지 확인하고 사용자가 실행한다.

```bash
hermes gateway restart
hermes cron status
```

gateway가 없다면 `hermes gateway install` 및 `hermes gateway start`로 해당 OS의 서비스 설치 절차를 진행한다. 한 번의 실습에서는 `hermes gateway run`으로 전경 실행할 수도 있다. macOS가 잠들거나 서버가 꺼지면 수집이 지연된다. 무인 운영에는 상시 실행 호스트가 적합하다.

토큰 갱신은 별도 문제다. 특히 Reddit 단기 access token을 한 번 입력했다고 영구 운영이 되지 않는다. 실제 운영 전 플랫폼이 허용하는 OAuth refresh 절차나 토큰 공급기를 연결하고, 401 시 갱신 실패를 운영자에게 알려야 한다. 예제는 자동 갱신을 구현하지 않는다.

## 4. 반복 등록 전에 1회 cron 검증

먼저 [live 실행 절차](03-hands-on.md)를 거쳐 코드와 API 권한을 확인한다. 그 다음 동일한 gateway 환경에서 검증할 **1회 제한 작업**을 만든다.

```bash
hermes cron create 'every 1m' \
  --name sns-smoke-once \
  --script sns-collect.py \
  --no-agent \
  --deliver local \
  --repeat 1
hermes cron list
hermes cron status
```

생성 출력의 실제 job ID를 기록한다. scheduler가 실행한 뒤 로컬 실행 결과와 `live-data` 실행 기록을 확인한다. `cron run`을 요청해도 완료를 뜻하는 것이 아니라 다음 tick 실행 요청일 수 있다.

성공 조건:

- 키워드별 상태가 `ok`. 0건인 키워드도 API 성공 여부가 따로 남는다.
- `partial`이 있으면 검색 범위를 줄이거나 허용 예산 안에서 페이지 설정을 조정한다.
- 토큰 누락·401·403이면 실패로 남고, stdout/stderr에 토큰이 나타나지 않는다.
- DB, 응답 캡처의 경로가 기대한 개인 데이터 폴더이고 `live-wiki/raw/web/`에 새 내용 버전만 기록된다. JSONL은 별도 `--report` 명령으로 생성한다.
- 같은 내용을 다시 수집해도 raw 수·기존 바이트는 불변이고, 관측 이력만 늘어난다.
- raw export 성공을 canonical 컴파일 성공으로 보고하지 않는다.

실패하면 아직 반복 작업을 만들지 않는다. 테스트 작업이 남았다면 `hermes cron list`에서 ID를 확인한 후 그 ID만 제거한다.

## 5. 정식 반복 작업 만들기

```bash
hermes cron create 'every 1h' \
  --name sns-keyword-collect \
  --script sns-collect.py \
  --no-agent \
  --deliver local
hermes cron list
hermes cron status
```

`every 1h`는 매 정각이라는 뜻이 아니라 반복 간격이다. 정각이 필요하면 `'0 * * * *'`를 사용하고, 생성 결과의 `next_run_at`과 UTC offset을 확인한다. `'0 9 * * *'`가 무조건 한국 오전 9시라고 가정하지 않는다. gateway 시간대와 DST 정책을 확인한다.

`--no-agent`는 이 **수집 실행에서** LLM을 호출하지 않는다. SNS API 비용, 서버 비용, 별도 분석 job의 모델 비용이 사라지는 것은 아니다. 페이지 수·검색어 수·반복 횟수에 맞춰 API 대시보드에서 예산 상한을 설정한다.

### 결과 확인과 알림

- `--deliver local`: 결과를 로컬에 남긴다. **TUI에 나중에 자동 메시지가 뜨지 않는다.** CLI 목록/실행 결과와 설치 버전의 cron 출력 저장 위치를 확인한다.
- 알림이 필요하면 먼저 Telegram 등 gateway 플랫폼을 연결·검증하고, 해당 대상의 `--deliver`를 사용한다. 계정·채팅·토픽 지정 형식은 로컬 help와 공식 문서에서 확인한다.
- script-only 작업은 stdout을 그대로 전달하므로 게시물 전문·토큰·개인정보 대신 수집 건수와 상태만 출력한다.
- script가 nonzero로 끝나면 실패로 처리된다. `local`만 쓴다면 원격 경보도 가지 않는다. 무인 운영에서는 실제 알림 채널과 별도 “마지막 성공 시각” 감시가 필요하다.

### 관리 명령

아래 `JOB_ID`는 그대로 실행하지 말고 `hermes cron list`에서 확인한 실제 값으로 바꾼다.

```bash
hermes cron run JOB_ID
hermes cron pause JOB_ID
hermes cron resume JOB_ID
hermes cron remove JOB_ID
```

삭제·중지 전에 이름과 script를 함께 확인한다. 기존의 다른 작업은 건드리지 않는다. scheduler 중복 보호와 별개로 수동 실행까지 동시에 켜지 않도록 운영한다.

## 6. 수집·컴파일·분석 작업은 분리

수집/raw export는 매시간, 컴파일은 하루 한 번 검토, 분석은 검증된 상태에서 실행하는 식으로 분리한다. `--no-agent` 수집 job에 `omh-wiki`를 적어 넣는 것만으로 LLM 컴파일이 실행되지는 않는다. 단순히 다음 job을 5분 뒤에 배치하는 것만으로 앞 단계 완료가 보장되지 않는다.

처음에는 [증분 위키 실습](07-incremental-wiki.md)의 `prepare → Hermes + omh-wiki 편집 → 검토 → finish`를 수동으로 진행한다. 그 흐름이 검증된 후에만 별도 **agent 작업**의 자동화를 설계한다. 모델 비용, 스킬 로드, 위키 쓰기 범위와 사람 승인 정책은 수집기와 별개다. 이 강의는 실제 컴파일 cron을 등록하지 않는다.

컴파일 작업의 입력 계약:

1. export가 끝난 raw만 대상으로 배치 ID·해시를 고정한다. 준비된 manifest는 실행 증거가 아니다.
2. 현재 open 배치부터 재개하고, 새 배치를 매번 쌓아 같은 출처를 중복 처리하지 않는다.
3. 같은 위키를 편집하는 작업자는 하나만 둔다. 실습은 분산 잠금이나 다중 작업자 운영을 보장하지 않는다.
4. 실패·해시 불일치·검토 보류 시 완료 checkpoint를 진행하지 않는다.
5. 재준비가 필요하면 `abort`로 배치를 닫되 pending 출처와 이전 manifest는 남긴다.
6. `finish`의 구조 검증 외에 사람이 주요 주장·출처·상충 정보를 검토한다.

분석 job은 다음을 확인하고 시작해야 한다.

1. DB에서 최근 완료된 수집 실행과 각 검색의 상태 확인.
2. 분석 대상 UTC 구간과 데이터 기준 시각 고정.
3. 오류·부분 수집·오래된 데이터가 있으면 보고서 머리에 명시.
4. SQL 집계 후 필요한 샘플만 Hermes에 제공.
5. 원문 지시문은 외부 데이터로 취급. 분석 중 추가 cron 등록 금지.

`context_from`을 지원하는 버전에서도 전달되는 것은 앞 job의 **최근 완료 결과**이지 의존성 대기나 DB 트랜잭션이 아니다. 정확한 연결은 run ID와 데이터 기준 시각으로 검증한다.

## 7. 흔한 장애

| 증상 | 우선 확인 | 대응 |
| --- | --- | --- |
| 터미널 성공, cron 실패 | gateway의 프로필·HOME·allowlist·토큰 반영 여부 | 값이 아니라 존재 여부만 확인 |
| script path rejected | `$HERMES_HOME/scripts/` 내부인지 | wrapper 설치 |
| 401 | 만료 또는 잘못된 토큰 | 승인된 갱신·재인증 절차 |
| 403 | 앱 승인·권한·API 상품 | 권한 해결, 우회 금지 |
| 429 | 조회 빈도·할당량 | 지수 backoff·주기 완화·예산 확인 |
| 계속 partial | 페이지 한도 대비 결과량 | 키워드 분할·기간 제약·증분 수집 확장 |
| raw export 실패 | demo/live, 데이터셋 바인딩, 해시·권한 | 원본 덮어쓰기 금지, 실패 원인 검토 |
| prepare만 반복됨 | 실제 편집·검토·finish 여부 | 같은 배치 재개, 근거 부족은 보류 |
| finish 실패 | raw 변조·canonical·index·log 오류 | 완료 상태를 수동 변경하지 말고 검토·수정 |
| 작업은 있는데 실행 안 됨 | cron status의 heartbeat·gateway·절전 | 실행 호스트 복구 |
| 0건이 갑자기 많아짐 | 성공 0건 vs 실패 0건 | 상태와 API 정책/검색어 변화를 함께 확인 |

## 근거

- [Hermes cron 공식 문서](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)
- [Hermes configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)
- [실제 확인 범위 및 제한](06-sources-and-verification.md)
