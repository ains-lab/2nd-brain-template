# 4주차 — SNS 수집에서 증분 Wiki와 Hermes 분석까지

**Threads · X · Reddit 검색 → SQLite에 콘텐츠 버전·관측 저장 → raw Markdown 내보내기 → omh-wiki 기반 증분 정리 → SQLite와 Wiki를 함께 분석**하는 핸즈온이다.

수집·내보내기·완료 검사는 Python, 수치 계산은 SQLite, 출처를 읽고 canonical 페이지를 정리하는 일은 **Hermes에서 로드한 omh-wiki 스킬**이 맡는다. OMH는 SNS 데이터 제공 서비스나 독립 cron 엔진이 아니며, 스킬을 로드하거나 배치를 준비한 것만으로 Wiki가 컴파일된 것은 아니다.

## 읽는 순서

| 순서 | 문서 | 배우는 내용 |
| --- | --- | --- |
| 1 | [파이프라인 설계](01-pipeline-design.md) | 개인 Wiki 운영 모델, 버전·관측·출처 계층 |
| 2 | [OMH 및 API 준비](02-omh-and-api-setup.md) | omh-wiki 대화 요청, 플랫폼별 권한·토큰, 비용·제약 |
| 3 | [핸즈온](03-hands-on.md) | 키 없이 demo 수집·raw 내보내기·배치 준비, live 분리 |
| 4 | [증분 Wiki 컴파일](07-incremental-wiki.md) | 생성된 프롬프트로 Hermes 정리, 검토·finish·재실행 |
| 5 | [cron 운영](04-cron-operations.md) | wrapper 설치, 환경변수 전달, 1회 검증, 반복 등록·중지 |
| 6 | [Hermes에서 분석](05-analysis-with-hermes.md) | SQLite 집계와 canonical→raw→버전의 근거 연결 |
| 7 | [근거와 검증 범위](06-sources-and-verification.md) | 확인한 문서·버전, 실행 결과, 미검증 사항 |

## 우선 실행해 보기

저장소 루트에서 Python 3.9 이상으로 실행한다. 추가 패키지는 필요하지 않다.

```bash
D="$HOME/.local/share/hermes-sns-demo"
W="$HOME/.local/share/hermes-sns-demo-wiki"
python3 -m unittest discover -s class/4w/lab -p 'test_*.py' -v
python3 class/4w/lab/pipeline.py \
  --config class/4w/lab/keywords.example.json \
  --data-dir "$D" \
  --mode demo
python3 class/4w/lab/pipeline.py \
  --data-dir "$D" \
  --report

# 새롭고 비어 있는 개인 Wiki에 최초 한 번만 실행한다.
python3 class/4w/lab/wiki_pipeline.py init \
  --wiki-dir "$W" --schema SCHEMA.md --mode demo
python3 class/4w/lab/wiki_pipeline.py export \
  --data-dir "$D" --wiki-dir "$W"
python3 class/4w/lab/wiki_pipeline.py prepare \
  --data-dir "$D" --wiki-dir "$W" --limit 20
```

`init`은 기존 Wiki에 덧씌우는 명령이 아니다. 같은 실습을 다시 실행할 때는 생략한다. `export`는 등록된 `raw/web/`에 버전별 Markdown을 만들고, `prepare`는 개인 데이터 폴더에 미처리 배치 manifest와 Hermes용 프롬프트를 준비한다. 출력의 `prepared`는 **정리 대기**, `noop`은 처리할 새 입력이 없다는 뜻이다. `prepared`를 컴파일 완료로 보고하지 않는다.

다음은 [증분 Wiki 컴파일](07-incremental-wiki.md)의 생성된 프롬프트를 Hermes에 전달하고, 실제 변경을 검토한 뒤 `finish`로 구조를 검사하는 단계다. 기본 demo의 짧은 합성 글만으로는 출처가 충분한 canonical 페이지와 유효한 링크 집합을 만들지 못할 수 있다. 개수를 맞추려고 페이지를 발명하지 말고 **모든 입력을 보류하고 canonical 0개를 유지해도 된다**. 별도의 합성 출처를 사용하는 구조 검사 테스트는 이 demo의 의미적 컴파일 성공을 증명하지 않는다.

**demo의 게시물은 의도적으로 만든 합성 fixture다. 실제 SNS 검색 결과가 아니다.** API 비용 없이 로컬 흐름을 확인하며, live 데이터 폴더와 live 비공개 Wiki는 각각 따로 둔다.

## 제공 파일

- [lab/pipeline.py](lab/pipeline.py): Python 표준 라이브러리 기반 실습 수집기.
- [lab/wiki_pipeline.py](lab/wiki_pipeline.py): 격리된 Wiki 초기화, raw 내보내기, 증분 배치 준비·완료 검사.
- [lab/test_pipeline.py](lab/test_pipeline.py): 모의 API 응답 기반 회귀 테스트.
- [lab/test_regressions.py](lab/test_regressions.py): 통합 검토에서 추가한 오류·페이지네이션·URL 회귀 테스트.
- [lab/test_incremental.py](lab/test_incremental.py): 내용 버전·관측·레거시 마이그레이션·페이지 원자성 테스트.
- [lab/test_wiki_pipeline.py](lab/test_wiki_pipeline.py): 불변 raw·배치 상태·CLI·canonical 완료 검증 테스트.
- [lab/test_scheduled_pipeline.py](lab/test_scheduled_pipeline.py), [lab/test_materials.py](lab/test_materials.py): wrapper 종료 코드와 교재 형식·링크·명령 구문 검사.
- [lab/keywords.example.json](lab/keywords.example.json): 사용자 키워드 등록 예시.
- [examples/run-sns.py](examples/run-sns.py): Hermes 프로필의 scripts 폴더에서 수집 후 raw export까지 실행하는 cron wrapper. 배치 준비·LLM 호출·finish는 하지 않는다.

## 기대할 수 있는 것과 없는 것

| 포함 | 포함하지 않음 |
| --- | --- |
| 세 플랫폼의 API 연결 예제 | 계정·앱 승인이나 유료 API 이용권 발급 |
| 키워드별 검색, 페이지 제한, 오류 기록 | 플랫폼 전체 글의 완전한 수집 보장 |
| 게시물·콘텐츠 버전·관측·검색 매칭의 SQLite 저장 | 전체 API 기록의 증분 watermark·백필 보장 |
| 버전별 raw와 미처리 배치, 검토 후 완료 검사 | 준비만으로 canonical 자동 생성·의미적 정확성 보장 |
| 호환 JSONL 및 SQL·Wiki 결합 분석 | 기사 전문 무단 수집·유료벽 우회 |
| cron 등록 및 운영 절차 | 사용자 환경의 자동 설치·설정 변경·cron 등록 |
| 데이터 품질·분석 가이드 | 실제 API 인증을 완료했다는 주장 |

현재 자료는 **문서와 로컬 검증 가능한 실습 코드**다. API 수집은 최신 검색의 제한된 반복 조회이고, 로컬 콘텐츠 버전·내보내기·컴파일 대상 관리가 증분이다. 장기 운영 전 OAuth 갱신, API 체크포인트, 삭제 정책, 예산·장애 알림을 추가해야 한다. 자세한 구현·검증 경계는 마지막 문서에 기록한다.

**Reddit 연구용 이용 주의:** 공식 정책은 연구 목적에 RFR(Reddit for Researchers) 경로를 요구한다. 일반 Data API 어댑터를 연구용으로 바로 돌리지 말고, 승인된 이용 목적과 제공되는 접근 방식부터 확인한다.

수강생 본인과 Hermes가 읽는 **개인 비공개 Wiki**를 전제로 하며, 수강생이 매 ingest 후 또는 매일 미처리 입력·근거·삭제 요청을 점검한다. 팀으로 확장하면 페이지별 책임자·쓰기 권한·동시 편집 규칙이 필요하다. 관리자가 없다면 Wiki를 방치하지 말고 **SQLite만 유지하는 분석 방식**을 선택한다.

수집된 실제 데이터, 토큰, DB, raw, canonical, 백업은 Git 저장소 밖에서 관리한다. 저장소 루트의 [SCHEMA.md](../../SCHEMA.md)가 규칙의 기준이며, 실습은 별도 Wiki로 복사한 계약을 따른다. 강의 실행으로 루트의 빈 raw/canonical을 채우거나 실제 데이터셋을 배포하지 않는다.
