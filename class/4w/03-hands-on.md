# 4주차 — SNS 수집·raw 내보내기·Wiki 연결 핸즈온

> 실행 위치: 저장소 루트. Python 3.9 이상, 표준 라이브러리만 사용한다.
> [구조](01-pipeline-design.md)와 [API 준비](02-omh-and-api-setup.md)를 먼저 읽는다.

## 실습 1. 키워드 등록 파일 확인

[키워드 예시](lab/keywords.example.json)를 열어 `queries`를 확인한다. 각 항목은 `id`, `platform`, `query`, `enabled`로 관리한다. 개인 설정은 저장소 밖에 복사한다.

```bash
mkdir -p "$HOME/.local/share/hermes-sns"
cp class/4w/lab/keywords.example.json \
  "$HOME/.local/share/hermes-sns/keywords.json"
```

기존 파일이 있으면 위 복사 명령으로 덮어쓰지 말고 먼저 비교한다. 편집기에서 본인의 검색어로 수정한다. 문서의 예시 키워드는 수업용이며 사용자가 이미 등록한 실제 키워드를 대신한 것이 아니다.

- `platform`: `x`, `threads`, `reddit` 중 하나.
- `id`: 공백 없는 고유 이름. 검색 의미를 바꾸면 새로운 ID로 관리한다. 이미 등록된 ID를 다른 플랫폼/검색식으로 재사용하면 오류이며, 기존 정의를 덮어쓰지 않는다.
- `enabled`: `false`로 설정하면 해당 검색을 실행하지 않는다.
- `max_pages`: 조회량과 비용을 제한하는 설정. 다음 페이지가 남아 있는데 상한에 도달하면 `partial`이다.
- 플랫폼마다 검색식 문법이 다르므로 동일 문자열·동일 결과를 기대하지 않는다.

**실습 과제:** 관심 주제 하나를 고르고, 세 플랫폼 검색식을 각각 작성한다. 쿼리의 언어·기간·제외 조건과 의도를 메모한다.

## 실습 2. 먼저 테스트 실행

```bash
python3 --version
python3 -m unittest discover -s class/4w/lab -p 'test_*.py' -v
```

테스트의 API 응답은 합성/mock 데이터이며 네트워크 인증 검증이 아니다. 테스트가 실패하면 live API부터 호출하지 말고 오류를 해결한다.

## 실습 3. 키 없이 demo 수집

```bash
export DEMO_DIR="$HOME/.local/share/hermes-sns-demo"
python3 class/4w/lab/pipeline.py \
  --config class/4w/lab/keywords.example.json \
  --data-dir "$DEMO_DIR" \
  --mode demo
python3 class/4w/lab/pipeline.py \
  --data-dir "$DEMO_DIR" \
  --report
```

demo는 사전에 정한 합성 응답으로 수집 흐름을 재생한다. 검색어를 바꿔도 인터넷에서 새 글을 찾지 않는다. 분석 결과에 반드시 **합성 실습 데이터**라고 표시한다.

저장 폴더에서 확인할 내용:

1. 고유 게시물·콘텐츠 버전·관측·키워드 매칭을 저장한 SQLite DB.
2. 실행·키워드별 `ok`, `partial`, `error` 기록.
3. 재처리에 사용할 응답 캡처.
4. 분석에 사용할 JSONL 내보내기.

파일은 `pipeline.sqlite3`, 모드 구분용 `mode.json`, 실행별 임의 ID의 `.json` 스냅샷으로 저장된다. `--report`가 `export-*.jsonl`을 새로 만든다. 수집 명령만 실행하면 JSONL은 생성되지 않는다. 스냅샷은 허용 필드만 남긴 정규화 응답이며 원시 HTTP 응답 그대로가 아니다.

DB의 `posts`는 `(platform,id)`당 최초 캡처 한 행이며 최신 콘텐츠 테이블이 아니다. `post_versions`는 콘텐츠 버전, `observations`는 실행·검색별 관측, `query_definitions`는 검색 정의다. `matches`는 검색 ID별 매칭, `runs`는 실행, `health`는 실행별 검색 상태를 유지한다. `observation_facts` view로 관측과 해당 콘텐츠·검색식을 함께 읽을 수 있다.

`--report`의 versions/observations 건수도 확인한다. 내보낸 JSONL은 기존 호환성을 유지하는 **검색 매칭당 한 줄**이므로 한 게시물이 여러 줄에 나오며, 최신 관측 전체를 담는 형식은 아니다. SQLite를 모르는 경우 Hermes에 “이 폴더 DB의 sqlite_master와 PRAGMA table_info를 읽어 테이블·view와 JSONL의 행 단위가 다른 데이터 사전을 만들어줘. 데이터는 수정하지 마”라고 요청한다. [분석 문서](05-analysis-with-hermes.md)의 최신 관측 SQL을 기준으로 삼는다.

## 실습 4. 같은 명령 재실행

실습 3의 수집 명령을 한 번 더 실행하고 `--report`로 비교한다.

- **고유 게시물 수**는 같은 게시물의 재수집으로 늘어나면 안 된다.
- **콘텐츠 버전 수**는 같은 콘텐츠라면 늘어나지 않는다. 지표·검색어·수집 시각은 버전 해시에서 제외된다.
- **검색 매칭 수**는 같은 검색 ID와 같은 게시물 조합에서 중복되면 안 된다.
- **실행 이력과 관측 수**는 다음 실행에서 다시 발견된 사실을 기록하므로 늘어날 수 있다. 같은 실행·검색·버전 안에서만 중복 관측을 제거한다.
- 서로 다른 검색 ID에 같은 게시물이 걸리면 게시물 하나에 여러 매칭이 생긴다.

이는 “파일 이름이 같은지”가 아니라 `(platform, post_id)`라는 의미 있는 키로 중복을 막는 연습이다. 특정 글의 재노출 횟수와 고유 글 수는 다른 지표다.

기본 demo는 고정 콘텐츠를 재생하므로 재실행만으로 본문 수정 사례가 생기지 않는다. 콘텐츠 수정·지표만 변화·검색 ID 변경은 mock 회귀 테스트로 구분해 확인한다. 과거 DB를 읽을 때도 없던 과거 참여 지표나 관측 시점을 추정해 채우지 않는다.

## 실습 5. 실패도 데이터로 다루기

테스트 코드에서 다음 상황을 확인한다.

- HTTP 오류 또는 자격 증명 누락.
- API 호출에 성공했지만 결과가 없는 경우.
- 다음 페이지가 있는데 `max_pages`에 도달한 경우.
- 한 플랫폼은 실패하고 나머지는 성공하는 경우.
- demo 폴더를 live 모드로 잘못 재사용하는 경우.

**합격 기준:** 오류가 있는 실행이 “성공, 새 글 0건”으로 둔갑하지 않고, 부분 수집도 `partial`로 드러나야 한다. 전체 프로세스의 실패 상태도 cron이 감지할 수 있어야 한다.

## 실습 6. SQLite에서 개인 Wiki로 연결

### 새롭고 빈 demo Wiki를 최초 한 번만 초기화

```bash
D="$HOME/.local/share/hermes-sns-demo"
W="$HOME/.local/share/hermes-sns-demo-wiki"
python3 class/4w/lab/wiki_pipeline.py init \
  --wiki-dir "$W" --schema SCHEMA.md --mode demo
python3 class/4w/lab/wiki_pipeline.py export \
  --data-dir "$D" --wiki-dir "$W"
python3 class/4w/lab/wiki_pipeline.py prepare \
  --data-dir "$D" --wiki-dir "$W" --limit 20
```

`init`은 기존 Wiki를 마이그레이션하거나 덮어쓰는 명령이 아니다. `$W`가 이미 초기화되어 있다면 재실행 때 `init`을 생략한다. 다른 파일이 있는 디렉터리나 저장소 루트를 대상으로 삼지 않는다. 루트 [SCHEMA.md](../../SCHEMA.md)를 기준으로 별도 Wiki를 만들며, 이 저장소의 raw/canonical에는 demo를 넣지 않는다.

실습은 단일 쓰기 담당자 기준이다. 수집/export가 끝난 뒤 prepare하고, Hermes 정리·검토·finish가 진행되는 동안 같은 데이터셋의 수집/export와 다른 Wiki 편집을 멈춘다. 다른 근거로 배치를 다시 만들려면 [증분 Wiki 문서](07-incremental-wiki.md)의 abort 절차를 따른다.

### 단계별 확인

1. **export:** `post_versions`의 버전마다 `raw/web/sns-{platform}-{version_id}.md`가 생긴다. 해시는 frontmatter 뒤 본문 바이트 기준이고 `raw_exports`가 DB와 파일을 연결한다. JSON 응답 캡처와 이 Markdown은 서로 다른 산출물이다.
2. **재export:** 같은 버전은 같은 raw 경로로 연결되고 기존 본문을 덮어쓰지 않아야 한다. 지표만 달라진 관측 때문에 새 raw를 만들지 않는다. 새 콘텐츠 버전은 별도 raw로 추가된다.
3. **prepare:** 출력의 상태·`batch_id`·manifest·프롬프트 경로를 확인한다. `prepared`는 미처리 배치 준비일 뿐이고, `noop`은 대상 없음이다. 완료되지 않은 열린 배치가 있으면 재사용한다.
4. **Hermes + omh-wiki:** 생성된 프롬프트를 해당 개인 Wiki 경로와 함께 전달한다. 출처를 읽고 기존 주제를 갱신하거나 근거 있는 새 주제를 정리하는 것은 이 단계다.
5. **검토 + finish:** [증분 Wiki 컴파일](07-incremental-wiki.md)의 절차로 실제 변경과 출처를 검토하고 완료 검사한다. canonical `sources`로 연결되지 않은 입력은 미처리로 남는다. `finish` 성공도 의미적 정확성·외부 API 인증 성공을 뜻하지 않는다.

**보류도 정상 결과다.** 기본 demo의 짧은 합성 문장으로 근거 있는 canonical 집합을 만들 수 없다면 전부 보류한다. SCHEMA의 페이지당 두 유효 링크 규칙 때문에 페이지 수를 억지로 채우지 않는다. canonical 0개와 미처리 배치를 유지하고 구조 검증 테스트와 실제 지식 정리 결과를 구분한다. 근거가 충분해 정리한 경우에도 필수 frontmatter·등록 태그·sources·링크·index/log를 함께 검토한다.

### 유지보수 과제

수강생 본인이 ingest 후 또는 매일 미처리 배치와 낡은 주장을 확인하고, 삭제·보존 요청이 raw·DB·내보내기·canonical·index·백업에 반영되는지 점검한다. 자동 cron에 LLM 컴파일까지 몰래 추가하지 않는다. 담당자를 둘 수 없다면 Wiki 정리를 중단하고 읽기 전용 SQLite 분석만 유지한다.

## 실습 7. 승인된 실제 API로 전환

### 준비

1. [API 준비 문서](02-omh-and-api-setup.md)에 따라 각 서비스의 승인·권한·토큰을 확보한다.
2. 개인 config에서 준비되지 않은 플랫폼은 `enabled: false`로 둔다.
   Reddit을 연구 목적으로 활용한다면 일반 Data API 예제는 비활성화하고 RFR 승인·제공 경로를 먼저 확인한다. RFR 접근이 일반 Data API 토큰과 동일하다고 가정하지 않는다.
3. 비밀 값은 사용자가 비공개 로컬 환경 또는 secret store에 넣는다. 채팅이나 명령 인자에 붙이지 않는다.
4. 새 데이터 폴더와 별도의 비공개 live Wiki 경로를 선택한다. demo DB/Wiki는 재사용하지 않는다.
5. 처음에는 한 플랫폼, 한 키워드, 적은 페이지 수로 실행한다. 실제 요청에는 과금이 발생할 수 있다.

### 실행

아래 명령은 해당 프로세스 환경에 토큰이 준비된 경우에만 성공한다. 단독 shell에서 실행할 때와 Hermes 도구 또는 gateway에서 실행할 때 환경 전달 방식이 다르다는 점은 [cron 운영](04-cron-operations.md)을 참고한다.

```bash
python3 class/4w/lab/pipeline.py \
  --config "$HOME/.local/share/hermes-sns/keywords.json" \
  --data-dir "$HOME/.local/share/hermes-sns/live-data" \
  --mode live
python3 class/4w/lab/pipeline.py \
  --data-dir "$HOME/.local/share/hermes-sns/live-data" \
  --report
```

401/403이면 권한을 해결한다. 429면 주기·페이지 수를 조정하고 재시도 대기 정책을 따른다. 잘못된 검색 문법의 400을 네트워크 문제처럼 무한 재시도하지 않는다. 오류 내용을 확인할 때 인증 헤더나 토큰이 포함된 URL을 공유하지 않는다.

승인된 live 수집을 확인한 뒤 실습 6과 [증분 Wiki 문서](07-incremental-wiki.md)의 절차를 **별도의 빈 live Wiki**에 적용한다. [cron wrapper](04-cron-operations.md)와 연결할 경로는 `$HOME/.local/share/hermes-sns/live-data`와 `$HOME/.local/share/hermes-sns/live-wiki`이며, Wiki 초기화는 `--mode live`로 한 번만 한다. raw·생성 프롬프트·canonical에는 실제 콘텐츠가 들어갈 수 있으므로 외부 모델 전달 범위와 처리 정책도 먼저 승인한다. 자료의 명령을 읽은 것만으로 실제 인증·수집·컴파일이 완료된 것은 아니다.

### 실제 수집 검증 체크리스트

- [ ] 반환된 원문 URL을 사람이 열어 게시물 ID·내용·작성 시각을 대조했다.
- [ ] 각 활성 검색의 상태가 성공인지, 부분 수집인지, 실패인지 확인했다.
- [ ] 두 번째 실행에서 같은 게시물은 중복되지 않았다.
- [ ] 같은 콘텐츠/지표만 변화/콘텐츠 변경을 버전과 관측으로 구분했다.
- [ ] raw 내보내기와 준비 배치, canonical 반영·완료 검사를 별도 상태로 기록했다.
- [ ] API 한도와 실제 청구·할당량 사용량을 대시보드에서 확인했다.
- [ ] 파일·출력에 토큰이 저장되지 않는지 비공개 환경에서 점검했다.
- [ ] 보존 기간·삭제 정책과 OAuth 갱신 방법을 결정했다.

## 실습 8. cron으로 연결

[cron 운영 문서](04-cron-operations.md)의 순서대로 **1회 제한 작업 → 결과 확인 → 반복 작업**을 진행한다. API 권한이 준비되지 않은 상태에서 실패하는 hourly job부터 등록하지 않는다.

운영용 config와 코드 사본은 저장소 밖에 있으므로 강의 코드 수정이 자동 배포되지는 않는다. `pipeline.py`와 `wiki_pipeline.py` **두 파일 모두** 설치하고, `live-wiki`를 아직 만들지 않았다면 최초 한 번 초기화한다. 코드 검토 → 테스트 → 수동 live 검증 → 실행 사본 갱신 순서를 유지한다.

wrapper는 **수집 → raw export**를 수행한다. 부분 수집/검색 실패인 exit 1에도 커밋된 자료의 export를 시도하되 실패 종료를 유지하고, 설정 오류 등의 exit 2에서는 export를 생략한다. `prepare`, LLM 호출, canonical 편집, `finish`는 하지 않는다. 자세한 설치·종료 코드·등록 절차는 [cron 운영](04-cron-operations.md)을 따른다. 사람이 확인한 뒤 실행하는 절차이며, 문서를 작성하거나 읽는 것만으로 토큰·설정·cron이 변경되지는 않는다.

## 실습 9. SQLite와 Wiki를 함께 분석

[분석 문서](05-analysis-with-hermes.md)의 품질 점검 프롬프트부터 시작한다. SQL로 게시물·버전·관측을 구분해 계산하고, Hermes에는 canonical에서 주제를 찾은 뒤 raw와 해당 버전의 관측을 대조하게 한다. canonical이 없는 demo는 SQL과 raw 추적까지만 분석하며 Wiki 정리가 완료됐다고 꾸미지 않는다.

최종 제출물 예시:

- 키워드 정의와 플랫폼별 검색식.
- 수집 구조와 수집 권한의 범위.
- 데이터 사전, 고유 게시물·콘텐츠 버전·관측·매칭 수, 상태별 실행 건수.
- export/prepare 결과와 배치 식별자, canonical 반영 또는 보류 사유, 실제 finish 결과가 있다면 그 검사 범위.
- 실제 실행한 SQL/스크립트와 간단한 시각화 또는 표.
- Wiki가 있는 경우 canonical→raw→버전→관측의 출처 연결과 최신성 한계.
- 부분 수집·편향·삭제·보존·비용에 대한 한계 메모.
- 근거 URL을 포함한 한국어 요약. demo로 진행했다면 전체를 합성 데이터 결과로 명시.
