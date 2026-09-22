# 4주차 — 근거, 실제 검증 결과, 남은 작업

확인일: **2026-09-22 (KST)**. 이 파일은 문서 확인·로컬 실행·실제 API 검증을 구분한다. API 정책·요금·권한과 OMH/Hermes 옵션은 배포 시 다시 확인한다.

## 1. 확인한 원자료

| 자료 | 확인 내용 | 접근·검증 범위 |
| --- | --- | --- |
| [OMH 저장소](https://github.com/rlaope/oh-my-hermes) / [한국어 README](https://github.com/rlaope/oh-my-hermes/blob/d7271b208038895f50c74e9774616b1a0a26a0dd/README.ko.md) | Homebrew/npm 설치, `omh setup`, `omh doctor`, `ulw-*` 역할 | GitHub API/raw 문서와 remote SHA 확인; 설치 미실행 |
| [OMH 워크플로](https://github.com/rlaope/oh-my-hermes/blob/d7271b208038895f50c74e9774616b1a0a26a0dd/docs/WORKFLOWS.md) | workflow는 prompt 수준 안내이며 숨은 런타임 실행 증거가 아님 | 문서 직접 열람 |
| [omh-wiki 스킬](https://github.com/rlaope/oh-my-hermes/blob/d7271b208038895f50c74e9774616b1a0a26a0dd/skills/omh-wiki/SKILL.md) / [운영 규칙](https://github.com/rlaope/oh-my-hermes/blob/d7271b208038895f50c74e9774616b1a0a26a0dd/skills/omh-wiki/references/wiki-operations.md) | 목적·독자·유지보수·근거 중심 워크플로; 자체 호스팅/컴파일 엔진이 아님 | 증분 위키 개정 시 upstream 원문과 로컬 스킬 직접 열람 |
| [Hermes Skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) | 설치된 스킬을 대화에서 로드, 실제 도구 실행과 구분 | 증분 위키 개정 시 공식 문서 직접 열람 |
| [OMH ops 파서·구현](https://github.com/rlaope/oh-my-hermes/blob/d7271b208038895f50c74e9774616b1a0a26a0dd/src/commands/ops.py) / [패키지 명세](https://github.com/rlaope/oh-my-hermes/blob/d7271b208038895f50c74e9774616b1a0a26a0dd/pyproject.toml) | blueprint dry-run은 JSON 설계 출력만 수행; Python >=3.11 | 소스 직접 대조, CLI 실행 미검증 |
| [Hermes cron](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) | gateway, script-only, scripts 경로 제약, 환경변수 allowlist, 실패 전달 | 공식 웹문서 및 설치된 CLI help/source 대조 |
| [X Recent Search quickstart](https://docs.x.com/x-api/posts/search/quickstart.md) | 최근 7일, bearer 인증, query, tweet.fields, next_token | 공식 Markdown 직접 열람 |
| [X Recent Search OpenAPI](https://docs.x.com/x-api/posts/recent-search.md) | endpoint, max_results 10–100, 시간/ID 인자, 인증 | 공식 Markdown 직접 열람; 일부 필드 이름의 문서 간 차이 발견 |
| [Threads Keyword Search](https://developers.facebook.com/documentation/threads/keyword-search) | endpoint, 권한, 미승인 시 자기 글만 검색, 검색 한도·페이지·인자 | 공식 페이지 HTTP 200, 본문 직접 확인 |
| [Reddit API search](https://www.reddit.com/dev/api/#GET_search) | 검색 계약 재확인용 공식 위치 | 이 환경의 직접 HTTP 요청은 403으로 차단됨 |
| [Reddit Data API Wiki JSON](https://support.reddithelp.com/api/v2/help_center/en-us/articles/16160319875092.json) | 삭제 의무·보존 권고·자격 있는 무료 이용자의 한도 | 일반 HTML 403 이후 공식 Help Center JSON으로 본문 확인 |
| [Reddit Developer Platform JSON](https://support.reddithelp.com/api/v2/help_center/en-us/articles/14945211791892.json) | 접근 승인·상업적 이용·학습 제한 | 공식 Help Center JSON 본문 확인 |
| [Reddit Responsible Builder Policy JSON](https://support.reddithelp.com/api/v2/help_center/en-us/articles/42728983564564.json) | 명시적 접근 승인·RFR 외부 수집 데이터의 연구 사용 금지 | 공식 Help Center JSON 본문 확인 |

OMH 원격 `main` 확인값: `d7271b208038895f50c74e9774616b1a0a26a0dd`. 로컬 설치 버전이라는 뜻이 아니라 **자료 확인 당시 remote SHA**다. 증분 위키 개정에서도 `git ls-remote`로 같은 SHA를 확인했다. 최초 작성 환경에서는 OMH CLI가 PATH에서 발견되지 않았으며, 개정에서는 설치된 omh-wiki 스킬과 upstream 문서를 직접 읽었다. CLI 유무와 스킬 로드 여부를 혼동하지 않는다.

Reddit 어댑터는 통상적인 OAuth search 계약을 사용하는 예제다. 검색 reference의 HTML은 차단됐지만, 추가 조사에서 공식 Help Center JSON으로 현재 일반 정책 본문을 확인했다. **특정 앱의 승인·허용 범위·실제 응답은 검증하지 않았다.** 연구 목적이면 RFR 경로와 제공되는 데이터 접근 방식으로 전환해야 한다. 접근 차단을 해결하기 위한 프록시·로그인 우회는 사용하지 않았다.

### 문서 간 차이를 숨기지 않기

- X quickstart는 `tweet.fields`, 확인한 OpenAPI는 `post.fields`를 표기했다. 코드는 quickstart HTTP 예시를 따른다. 실제 앱의 호환성 검증은 필요하다.
- Hermes 최신 공식 웹문서에는 설치 버전 help에 없는 옵션이 있을 수 있다. 이 핸즈온은 로컬에서 확인한 `create --script --no-agent --deliver --repeat` 범위로 작성했다.
- OMH에서 계획·워크플로 파일이 만들어졌다는 사실과 수집기가 실제 실행·검증됐다는 사실을 구분한다.
- Threads의 keyword-search 문서는 조회 당시 커서 규약을 명시하지 않았다. 코드의 Graph-style `after` 처리는 mock으로만 검증했으며 실제 응답 계약을 확인해야 한다.

## 2. 최초 강의 작성 환경 기록

아래는 기존 강의 작성 때의 기록이며 **이번 개정 환경의 현재 상태가 아니다**:

- 시스템 `python3`: **3.9.6**.
- `hermes --version`: **Hermes Agent v0.18.2 (2026.7.7.2), upstream 861d69c7**, Hermes Python **3.11.15**.
- `hermes cron create --help`: `--script`, `--no-agent`, `--workdir`, `--repeat`, `--deliver` 존재.
- `hermes cron status`: 작성 당시 gateway가 실행 중이며 ticker heartbeat가 표시됨.
- 기존 cron은 조회만 했고 생성·수정·삭제하지 않았다.
- `.env`, 인증 파일 또는 사용자 토큰 값은 읽지 않았다.

## 3. 최초 버전 검증 기록

### 단위·회귀 테스트

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s class/4w/lab -p 'test_*.py' -v
```

최초 수집기 버전의 실행 결과: **8 tests, OK**. 증분 위키 개정 결과는 아래 별도 항목으로 구분한다.

대상:

1. demo 재실행의 고유 게시물 중복 제거와 다중 키워드 매칭.
2. 빈 결과·페이지 상한·플랫폼별 실패·demo/live 폴더 분리.
3. 세 플랫폼의 고정 endpoint와 pagination 파라미터 정규화(mock 응답).
4. 제한된 429 재시도와 비밀 오류 내용 비노출.
5. CLI demo/report와 잘못된 config 처리.
6. Threads 마지막 페이지에 `after` cursor만 있고 `next`가 없으면 중단.
7. HTTP 401을 비밀 본문 없이 `http_401` 이유로 기록.
8. 기사 URL의 `?id=42`는 보존하고 `access_token`은 제거.

API 호출과 재시도 테스트는 모의 응답이며 실제 서비스 요청이 아니다.

### CLI end-to-end 실습

임시 폴더에서 기본 설정으로 demo 수집을 두 번 실행한 **실제 결과**:

```text
demo run 1 {"mode": "demo", "status": "ok"}
demo run 2 {"mode": "demo", "status": "ok"}
report: {"posts": 3, "matches": 3, "runs": 2, "failed_runs": 0}
SQL: [('reddit', 1), ('threads', 1), ('x', 1)]
```

이 수치는 **합성 fixture의 실행 결과**다. 실제 SNS 게시물을 수집했다는 의미가 아니다.

추가 실행 검증:

| 검증 | 관측 결과 |
| --- | --- |
| JSONL 내보내기 | 3행, 각 행 `mode=demo`, provenance 경로 존재 |
| 토큰 변수를 제거한 새 live 폴더 실행 | exit 1, 세 검색의 이유 `missing_credential` |
| demo 폴더에 live 실행 | exit 2로 거부 |
| cron wrapper | 임시 HOME의 설치 사본을 찾아 수집기 실행, 토큰 없음으로 exit 1 |
| 실제 cron 등록 | **하지 않음** |
| 실제 인증된 SNS 호출 | **하지 않음** |

검증용 데이터는 임시 폴더에서만 만들고 테스트 후 제거했다. 사용자 개인 데이터 폴더·Hermes 설정·원본 Wiki는 변경하지 않았다.

당시 문서 검증은 README quickstart와 분석 SQL의 임시 HOME 실행, 내부 상대 링크, bash 구문, UTF-8/LF, 코드 fence, Python AST, JSON 파싱 및 `git diff --check`였다. OMH blueprint 명령은 실제 CLI 실행이 아니라 공식 소스 대조와 bash 구문 검사만 수행했다.

## 4. 정확한 구현 범위

| 항목 | 실습 코드의 동작 |
| --- | --- |
| 추가 패키지 | 없음; Python 표준 라이브러리 |
| 검색 | config의 활성 검색을 순차 실행 |
| 수집량 | 전역 `max_pages` 1–10, 기본 2; X/Reddit 요청 크기 100, Threads는 서비스 기본값 |
| 재시도 | HTTP 429 및 5xx 최대 3회 시도, 짧은 Retry-After 존중; 긴/해석 불가 대기는 실패로 종료 |
| 타임아웃 | HTTP 요청 20초; 전체 실행 제한은 별도 cron 설정·검색 수에 의존 |
| pagination | X next_token, Threads next 존재 여부+after, Reddit after; 응답의 다음 URL로 직접 접속하지 않음 |
| 오류 | 플랫폼/검색 단위 격리, `partial` 또는 `error`면 전체 exit 1 |
| 종료 2 | 설정·모드·폴더 등 실행 전후 오류 |
| 저장 | 전용 폴더 0700, 데이터 파일 0600; 로컬 접근 제한이지 암호화는 아님 |
| 게시물 DB | `posts`는 최초 관측 유지, 변경 내용은 `post_versions`, 지표·시각은 `observations`에 추가 |
| 검색 정의 | `query_definitions`의 ID 의미 고정; 같은 ID의 검색식/플랫폼 변경 거부 |
| 마이그레이션 | 수집 및 `--report`가 추가 테이블 생성. 증명 가능한 레거시 관측만 복원; DB 쓰기 권한 필요 |
| 페이지 저장 | 정상 페이지별 SQLite savepoint; 잘못된 페이지의 부분 행 롤백. 파일과 DB의 crash-atomic commit은 아님 |
| raw | 새 개인 Wiki의 `raw/web/`; 버전별 불변 Markdown, 본문 및 파일 해시, 멱등 export |
| 배치 | `prepare`는 미처리 입력만 고정; 열린 배치 재사용; `abort`는 입력을 완료 처리하지 않고 해제 |
| 완료 | 명시적 `finish`에서 변경 canonical의 출처·metadata·링크·index/log와 frozen raw/SCHEMA 검증 |
| 검사 형식 | 새 실습 Wiki 전용 JSON 값 YAML subset 및 flat index. 임의의 기존 vault용 범용 linter 아님 |
| 수집/모델 분리 | wrapper는 수집과 raw export만 실행. Python이 canonical을 만들거나 LLM을 호출하지 않음 |
| 응답 캡처 | 정규화·허용 필드만 저장. 원시 응답 byte-exact 백업이 아님 |
| JSONL | `--report` 때 생성; 게시물당이 아니라 검색 매칭당 한 행 |
| 링크 | X entities, Reddit URL; Threads 외부 URL 구조화 미구현 |
| 기사 전문 | 미수집 |
| `health.fetched` | 조회된 항목 수이며 새 고유 게시물 수가 아님 |

보안 경계: Authorization 헤더와 paging URL을 저장하지 않고, 알려진 토큰 query parameter와 현재 bearer 값의 단순 echo를 제거한다. 이것이 모든 개인정보나 임의 텍스트의 모든 비밀을 탐지한다는 보장은 아니다. 데이터의 외부 반출 전 별도 검토가 필요하다.

## 5. 운영 전 추가해야 할 것

- [ ] 실제 세 플랫폼의 앱 승인과 최소 권한, 실제 검색 응답 스모크 테스트.
- [ ] OAuth 만료 감지와 안전한 자동 갱신 또는 관리형 token 공급기.
- [ ] 체크포인트·시간 구간 overlap·백필·실패 구간 재처리.
- [ ] 중복 실행 방지 및 파일/DB 간 중단 복구 강화. 페이지 savepoint는 구현됨.
- [ ] 실행 시작/완료/중단 ledger와 run ID 기준 분석 스냅샷.
- [ ] 응답 schema 변경 감지, 반환 필드 누락·부분 오류에 대한 강화 검증.
- [ ] 삭제·보존 정책 자동화. 스냅샷·DB·내보내기·백업을 함께 관리.
- [ ] API 예산·할당량 제한과 실패/오래된 데이터 알림.
- [ ] 기사 전문이 필요하면 별도 승인된 수집 경로 및 URL 관계 테이블.

현재 수집 구현은 실행 전체 트랜잭션 안에 페이지별 savepoint를 둔다. 프로세스 중단 시 일부 스냅샷만 남고 DB 실행 기록은 rollback될 수 있다. 따라서 캡처 파일만으로 완료를 판정하지 않는다. Wiki helper는 단일 작성자 기준이며, 분산 잠금·일반 위키 마이그레이션·로그 회전·자동 삭제 정책을 구현한 운영 서비스가 아니다. 배치를 만든 뒤에는 같은 Wiki의 수집/export/편집을 직렬화한다. 구조 검증으로 주제의 중요성·독립 출처·상충 주장의 해석까지 증명하지 않으며 사람 검토가 필요하다.

## 6. 증분 Wiki 개정에서 직접 실행한 검증

개정 실행 환경은 **Python 3.12.3**이다. 최초 버전의 8개 테스트를 먼저 실행해 통과한 뒤 확장했다. 추가 기능·결함은 실패 테스트로 확인하고 구현했으며, 원래 통과한 회귀 커버리지는 새로운 RED 증거라고 부르지 않는다.

전체 명령은 위 unittest discover와 동일하다. 최종 확인 결과: **46 tests, OK**. `test_materials.py`에는 문서 상대 링크, Bash 구문, UTF-8/LF/EOF, 코드 fence, Python AST, JSON 검사가 포함된다. Python 3.9 문법 파싱도 통과했지만 실제 Python 3.9 런타임에서 재실행한 것은 아니다.

임시 HOME에서 **README quickstart의 Bash 블록을 그대로 실행**한 뒤 이어서 관측한 결과:

| 실행 | 실제 관측 결과 |
| --- | --- |
| 동일 demo 두 번 | posts 3, matches 3, runs 2, versions 3, observations 6, failed_runs 0 |
| 첫 raw export / 반복 export | 3개 / 0개, 기존 raw 바이트 불변 |
| prepare | pending 3, manifest와 prompt 생성, canonical 생성 없음 |
| canonical 없는 finish | exit 2, 수락 연결 0개, 배치 prepared 유지 |
| abort 후 prepare | 이전 배치를 aborted로 보존하고 새 배치 ID 생성 |
| mock 지표만 변화 / 콘텐츠 변경 | 새 raw 0개 / 1개, 이전 raw 유지; 본문 SHA 검사 통과 |
| 분석 문서 | 내장 Python 블록과 SQL 4개 실행 통과 |
| 실제 wrapper를 임시 HOME에서 실행(토큰 제거) | exit 1, 세 검색 missing_credential, raw export 0개 |
| 루트 Wiki | SCHEMA/index/log 해시와 raw/canonical 상태 변경 없음 |

별도의 합성 **구조 UNIT fixture**로 `finish` 수락 → 동일 배치 noop → 새 버전만 pending, 부분 수락, raw/frontmatter 변조 거부, index/log 오류, SCHEMA drift, created 보존·updated 갱신, abort 상태, CLI 정상/실패 종료를 검사했다. 이 fixture는 실제 Hermes가 출처를 읽고 생성한 의미적 컴파일 결과가 아니다.

독립 코드 검토에서 보류된 출처가 새 출처의 배치 진입을 막는 문제가 발견돼 수정했다. 합성 101개를 100개씩 네 차례 prepare/abort해 순환을 검증했고, 부분 finish 후에도 미검토 → 오래된 보류 순서로 선택됨을 확인했다. 미처리 수·기존 raw·manifest·prompt·이력은 보존되며 가짜 수락은 만들지 않는다. 수정 후 전체 46개 테스트와 `git diff --check`를 다시 통과했다.

실제 SNS 인증 요청, LLM 컴파일 자동 실행, 사용자 개인 DB/Wiki 변경, cron 생성·수정, 토큰·인증 파일 열람은 하지 않았다. QA 데이터는 임시 경로에서 생성하고 정리했다. 배포 전 실제 승인된 소량 데이터로 별도 검증해야 한다.

## 7. 이 자료를 갱신할 때

공식 문서 → 로컬 CLI help → mock 계약 테스트 → 승인된 live 소량 검증 → 1회 cron 검증 → 반복 등록 순서로 진행한다. 외부 API 실패를 합성 결과로 대체해 “실제 수집 성공”이라고 적지 않는다.
