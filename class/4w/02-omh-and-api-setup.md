# 4주차 — OMH와 SNS API 준비

> 확인일: 2026-09-22. 이 문서는 설치 방법을 안내한다. 작성 과정에서는 OMH 설치·모델 변경·토큰 발급을 실행하지 않았다.

## 1. Hermes와 OMH의 역할

Hermes Agent는 실행 환경과 cron을 제공한다. [Oh My Hermes](https://github.com/rlaope/oh-my-hermes)는 Hermes 위에 작업 계획·조사·구현·검증 워크플로를 추가한다.

SNS 수집에서는 다음처럼 사용한다.

- **처음 만들 때:** OMH로 요구사항·API 제약 조사, 계획 검토, 코드 개선과 QA.
- **주기적으로 수집할 때:** 승인된 Python 수집기를 Hermes cron `--no-agent`로 실행.
- **분석할 때:** Hermes에서 실제 SQL을 실행하고 OMH로 분석 작업 분리·검토.

`omh sns collect` 같은 전용 명령이 있는 것으로 가정하지 않는다. 이 수업은 확인된 일반 워크플로와 별도 수집기를 조합한다.

## 2. 기존 설치부터 점검

```bash
hermes --version
hermes cron create --help
command -v omh
```

OMH가 발견된다면 먼저 다음을 확인한다.

```bash
omh --help
omh doctor
```

`command -v omh`가 아무것도 출력하지 않으면 현재 PATH에서 CLI를 찾지 못했다는 뜻이다. 일부 스킬만 설치됐거나 다른 환경에 CLI가 있을 수 있으므로 “OMH가 전혀 없다”고 단정하지 않는다.

### OMH를 새로 설치하는 경우

확인한 OMH 패키지는 **Python 3.11 이상**이 필요하다. 이 강의의 순수 Python 수집기는 3.9 이상에서 실행되지만 OMH의 요구 버전은 별개다. npm/Bun으로 설치해도 OMH는 Python 기반이므로 설치 도구가 마련한 런타임과 `omh doctor` 결과를 확인한다.

OMH README에 안내된 macOS Homebrew 경로를 사용하는 예시:

```bash
brew install rlaope/tap/omh
omh setup
omh doctor
```

npm 경로를 선호한다면 Homebrew 대신 **하나만** 선택한다.

```bash
npm install -g oh-my-hermes
omh setup
omh doctor
```

수업 재현성을 높이려면 배포 버전과 확인한 저장소 commit을 기록한다. 실제 설치 전에 [OMH 설치 문서](https://github.com/rlaope/oh-my-hermes/blob/main/docs/INSTALLATION.md)와 [에이전트 설치 프로토콜](https://github.com/rlaope/oh-my-hermes/blob/main/INSTALL_FOR_AGENTS.md)을 확인한다. 변화하는 `main`의 원격 shell을 검토 없이 실행하는 방식은 피한다.

`omh setup`은 단순 확인 명령이 아니라 사용자 환경을 변경하는 설정 과정이다. 기존 Hermes 설정과 모델 선택을 보존하고, 모델 라우팅 변경은 사용자가 승인한다. SNS API 토큰은 OMH 모델 제공자 자격 증명과 별개다.

### 핸즈온: OMH로 예약 운영 설계안 만들기

설치된 버전에서 `omh ops blueprint --help`로 옵션을 확인한 뒤 실행한다. 아래 문법은 확인 커밋의 CLI 파서와 구현에서 대조했으며, 현재 환경에 OMH CLI가 없어 실제 실행한 명령은 아니다.

```bash
omh ops blueprint \
  "승인된 Threads X Reddit 접근 경로에서 등록 키워드를 수집하고 중복 제거 후 분석용 DB에 저장한다" \
  --schedule "매시간" \
  --delivery "local report" \
  --silence "새 글이 없어도 실행 상태는 기록하고 인증 실패와 부분 수집은 알림" \
  --dry-run
```

`--dry-run`은 설계 JSON을 출력하고 저장하지 않는다. 출력의 `schema_version=omh_ops_blueprint_result/v1`과 `store.written=false`를 확인한다. `--json` 옵션은 붙이지 않는다. **이 명령은 SNS 조회·cron 등록·알림 전송을 실행하지 않는다.** `--schedule`과 `--delivery`도 설계 힌트다. 실제 실행 연결은 [cron 운영](04-cron-operations.md)에서 별도로 진행한다.

실습 과제: JSON 설계안의 주기·입력·결과·실패/무변화 정책이 요구사항과 일치하는지 검토하고, 아래 `ulw-plan`에 검토 자료로 제공한다. 파일을 저장하고 싶다면 개인 작업 폴더에서 실행 범위를 확인한 후 `--dry-run`을 제거한다.

### Hermes 안에서 OMH 활용

OMH README는 `ulw-*`를 **대화에서 라우팅하는 워크플로 트리거**로 설명한다. 아래는 OS shell 명령이 아니라 Hermes 채팅에 입력할 요청이다. 설치 후 새 세션에서 스킬이 실제로 노출되는지 확인한다.

```text
ulw-research
Threads, X, Reddit의 공식 검색 API만 사용해서 관심 키워드 글을 수집하려고 해.
현재 API 권한·쿼리·페이지네이션·비용·보존 정책을 출처와 함께 조사해.
로그인 우회나 유료 API 호출, 설치·설정 변경은 아직 하지 마.
```

```text
ulw-plan
class/4w의 실습 코드를 읽고 운영용 확장 계획을 검토해.
Hermes cron은 스케줄링, Python은 수집·중복 제거, SQLite는 분석 저장소로 써.
토큰 자동 갱신, 체크포인트, 중복 실행 방지, 삭제 정책, 비용 상한을 추가할 계획을
파일 단위 작업과 테스트 기준으로 제시해. 승인 전 코드는 바꾸지 마.
```

```text
ulw-qa
승인된 SNS 수집 코드에 대해 401/403/429, 빈 결과, 페이지 상한,
두 키워드의 동일 게시물, 재실행, 프로세스 중단을 테스트해.
실제 SNS에 장애 요청을 보내지 말고 mock으로 검증해.
토큰·사용자 설정·cron은 변경하지 말고 실제 테스트 출력으로 판정해.
```

`ulw-work`는 승인된 구현 계획을 수행하는 용도다. `ulw-loop`를 cron처럼 무한 실행시키지 않는다. 모델 비용·실행 범위·완료 기준을 명확히 한다.

## 3. SNS 토큰은 사용자가 직접 준비

공통 원칙:

1. 각 플랫폼 개발자 계정과 승인된 앱을 준비한다.
2. 읽기·검색에 필요한 최소 권한만 요청한다.
3. OAuth 승인 화면·개발자 콘솔·비공개 secret manager에서 토큰을 관리한다.
4. 토큰 값은 채팅·강의 문서·Git·명령 인자에 쓰지 않는다.
5. 짧은 수명 토큰을 cron에 고정해 두는 것과 지속 가능한 인증을 구분한다.
6. 운영에 필요한 상업적 이용·연구·재배포 권한을 확인한다. API 접근 권한이 모델 학습 권한까지 포함하지 않는다.

### X

- 개발자 앱에서 검색 API 접근과 과금/할당량을 확인한다.
- 실습 endpoint: `GET https://api.x.com/2/tweets/search/recent`.
- 환경변수: `X_BEARER_TOKEN`. HTTP Authorization 헤더로만 보낸다.
- `query`, `max_results`, `tweet.fields`를 사용하고, `meta.next_token`으로 다음 페이지를 요청한다.
- 확인일의 Recent Search quickstart는 최근 **7일** 검색을 안내한다. full-archive search는 다른 기능이며 과거 검색 상품의 권한·비용을 별도로 확인한다.
- 예제의 필드: `created_at`, `lang`, `public_metrics`, `entities`.

실습의 `tweet.fields`는 [공식 quickstart](https://docs.x.com/x-api/posts/search/quickstart.md)의 HTTP 예시를 따른다. 확인일의 다른 OpenAPI 페이지에는 `post.fields` 표기도 있어 문서 간 차이가 있다. 실제 승인된 앱에서 날짜·지표 필드가 반환되는지 1회 검증하고, 서비스 변경 시 테스트와 어댑터를 함께 갱신한다. 이 자료는 두 이름의 완전한 호환을 검증하지 않았다.

Hermes에서 [공식 xurl CLI](https://github.com/xdevplatform/xurl)를 별도로 이용할 수도 있다. xurl은 필수 의존성이 아니며, xurl에 저장한 OAuth 토큰이 이 Python 수집기의 환경변수로 자동 전달되지는 않는다.

```bash
xurl --help
xurl auth status
```

xurl의 인증 파일을 에이전트가 읽게 하지 않는다. API 가격을 오래된 무료 tier 안내로 단정하지 말고 현재 개발자 콘솔의 상품·크레딧·한도를 확인한다.

### Threads

- Meta 개발자 앱의 Threads API를 설정하고, Threads 사용자 인증 흐름을 완료한다.
- 공식 문서의 필수 권한은 `threads_basic`, `threads_keyword_search`다. **`threads_keyword_search`가 승인되지 않으면 인증된 사용자 소유 글에서만 검색되며, 승인 후 공개 글을 검색할 수 있다.** 200 응답이 왔다는 것만으로 전체 공개 검색 권한을 확보했다고 판정하지 않는다.
- 실습 endpoint: `GET https://graph.threads.net/keyword_search`.
- 환경변수: `THREADS_ACCESS_TOKEN`. HTTP Authorization 헤더로만 보낸다.
- 검색 인자: `q`, `search_type=RECENT`. 요청 필드: `id,text,timestamp,permalink`.
- 다음 페이지는 허용된 endpoint에 cursor를 전달해서 요청한다. 응답의 `paging.next` URL을 그대로 저장하거나 따라가지 않는다. 그 URL에는 access token이 포함될 수 있다.
- 페이지네이션 구현은 Graph 스타일의 `paging.next` 존재 여부와 `paging.cursors.after`를 전제로 한 **미인증 예제**다. 확인한 keyword-search 문서는 `limit`은 설명하지만 이 커서 계약을 명시하지 않았다. 실제 응답과 대조해 검증하기 전에는 전체 페이지 수집 성공으로 간주하지 않는다.
- 개발 모드의 앱 역할·테스터와 일반 사용자 대상 운영 접근을 구분하고 필요한 앱 검수를 진행한다.

확인일의 [Keyword Search 문서](https://developers.facebook.com/documentation/threads/keyword-search)는 사용자 기준 rolling 24시간에 최대 2,200 queries, 페이지 기본 25건·최대 100건을 안내한다. 같은 사용자의 여러 앱이 한도를 공유한다. 민감하거나 공격적이라고 판단된 키워드는 빈 배열을 반환할 수 있다. 제한과 정책은 변경될 수 있으며 **빈 결과가 실제 관련 글의 부재를 증명하지 않는다**. 실습은 Threads 페이지 크기를 명시하지 않아 서비스 기본값을 사용한다.

토큰 발급·장기 토큰 전환·갱신 가능 조건은 [Threads 공식 문서](https://developers.facebook.com/docs/threads/)에서 확인한다. 예제는 토큰 갱신기를 포함하지 않는다.

### Reddit

- Data API 이용 승인과 현재 접근 정책을 먼저 확인한다. OAuth 앱을 만들었다는 사실만으로 모든 사용 목적의 API 사용이 허가되는 것은 아니다.
- **연구 목적은 Reddit for Researchers(RFR) 경로를 먼저 신청한다.** 확인한 Responsible Builder Policy는 RFR 외부에서 수집한 Reddit 데이터의 연구 사용을 정책 위반으로 명시한다. 따라서 이 예제의 일반 Data API 어댑터를 학술 연구용 수집 경로로 그대로 사용하지 않는다. RFR 승인 후 제공되는 데이터 접근·내보내기 방식에 맞춰 별도 입력 어댑터를 구성한다.
- 실습 endpoint: `GET https://oauth.reddit.com/search`.
- 환경변수: `REDDIT_ACCESS_TOKEN`, `REDDIT_USER_AGENT`.
- OAuth bearer token과 앱·운영자를 식별하는 User-Agent를 사용한다.
- 검색 인자: `q`, `sort=new`, `type=link`, `limit`, `raw_json=1`.
- 응답: `data.children`; 다음 페이지는 `data.after`.
- 이 예제는 submission/link 검색이다. 댓글 전체, 특정 글의 댓글 트리, 삭제된 글 복원 기능이 아니다.

Reddit access token은 갱신을 전제로 관리한다. 승인된 인증 방식에 맞는 refresh 흐름을 연결하기 전에는 장기 무인 수집이라고 부르지 않는다. 예제의 401 오류를 숨기거나 비공식 우회 endpoint로 돌리지 않는다.

삭제된 게시물·댓글의 제목·본문·내장 URL 등 관련 콘텐츠는 로컬에서도 제거해야 한다. 계정 삭제 시 작성자 식별정보도 제거한다. 삭제된 내용을 익명화해서 계속 보관하는 것도 허용되지 않는다. Data API Wiki의 “48시간 이내 저장 데이터 정기 삭제”는 **강력 권고**이며 모든 데이터에 적용되는 단일 법적 보존기한이라고 표현하지 않는다.

공식 정책: [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564), [Reddit Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092). 일반 HTML이 차단되면 공식 Help Center의 같은 article ID JSON에서 본문을 확인할 수 있다. 인증 승인 전에는 demo만 사용한다.

## 4. 최소 권한·비용 체크리스트

| 항목 | 통과 조건 |
| --- | --- |
| 접근 승인 | 앱 및 용도가 승인돼 있고 검색 endpoint 이용 가능 |
| 검색 계약 | 1개 키워드의 실제 응답 형식·빈 결과·페이지네이션 확인 |
| 비용 | 활성 검색 수·페이지 수·주기와 예산 상한 합의 |
| 토큰 | 만료 시점·갱신 주체·실패 알림 결정 |
| 저장 범위 | 공개 게시물 중 분석에 필요한 필드만 |
| 삭제 정책 | 원문·DB·내보내기·백업까지 대응 절차 정의 |
| 비밀 전달 | 허용된 프로세스 환경만 사용, 값 출력 금지 |

인증되지 않은 상태에서도 다음 [demo 핸즈온](03-hands-on.md)은 진행할 수 있다. 단, demo 통과를 실제 SNS API 연결 성공으로 보고하지 않는다.
