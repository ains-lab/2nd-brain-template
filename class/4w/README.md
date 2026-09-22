# 4주차 — Hermes + OMH SNS 키워드 자동 수집·분석

**Threads · X · Reddit의 관심 키워드 검색 → 주기적 수집 → 중복 제거·저장 → Hermes 분석**을 배우는 핸즈온이다.

핵심 설계는 **Hermes cron + Python 수집기 + SQLite**, 그리고 **OMH를 활용한 설계·검토·분석**이다. OMH 자체를 SNS 데이터 제공 서비스나 독립 cron 엔진으로 가정하지 않는다.

## 읽는 순서

| 순서 | 문서 | 배우는 내용 |
| --- | --- | --- |
| 1 | [파이프라인 설계](01-pipeline-design.md) | 역할 분리, 키워드 관리, 데이터 구조, 게시물과 기사 구분 |
| 2 | [OMH 및 API 준비](02-omh-and-api-setup.md) | 확인된 OMH 명령, 플랫폼별 권한·토큰, 비용·제약 |
| 3 | [핸즈온](03-hands-on.md) | 키 없이 demo 실행, 테스트, live 전환, 데이터 확인 |
| 4 | [cron 운영](04-cron-operations.md) | wrapper 설치, 환경변수 전달, 1회 검증, 반복 등록·중지 |
| 5 | [Hermes에서 분석](05-analysis-with-hermes.md) | 품질 점검, SQL·주제 분류·기사 분석 프롬프트 |
| 6 | [근거와 검증 범위](06-sources-and-verification.md) | 확인한 문서·버전, 실행 결과, 미검증 사항 |

## 우선 실행해 보기

저장소 루트에서 Python 3.9 이상으로 실행한다. 추가 패키지는 필요하지 않다.

```bash
python3 -m unittest discover -s class/4w/lab -p 'test_*.py' -v
python3 class/4w/lab/pipeline.py \
  --config class/4w/lab/keywords.example.json \
  --data-dir "$HOME/.local/share/hermes-sns-demo" \
  --mode demo
python3 class/4w/lab/pipeline.py \
  --data-dir "$HOME/.local/share/hermes-sns-demo" \
  --report
```

**demo의 게시물은 의도적으로 만든 합성 fixture다. 실제 SNS 검색 결과가 아니다.** 수집·저장·재실행·분석 흐름을 API 비용 없이 확인하기 위한 것이다. live 데이터와는 별도 폴더를 사용한다.

## 제공 파일

- [lab/pipeline.py](lab/pipeline.py): Python 표준 라이브러리 기반 실습 수집기.
- [lab/test_pipeline.py](lab/test_pipeline.py): 모의 API 응답 기반 회귀 테스트.
- [lab/test_regressions.py](lab/test_regressions.py): 통합 검토에서 추가한 오류·페이지네이션·URL 회귀 테스트.
- [lab/keywords.example.json](lab/keywords.example.json): 사용자 키워드 등록 예시.
- [examples/run-sns.py](examples/run-sns.py): Hermes 프로필의 scripts 폴더에 설치할 cron wrapper.

## 기대할 수 있는 것과 없는 것

| 포함 | 포함하지 않음 |
| --- | --- |
| 세 플랫폼의 API 연결 예제 | 계정·앱 승인이나 유료 API 이용권 발급 |
| 키워드별 검색, 페이지 제한, 오류 기록 | 플랫폼 전체 글의 완전한 수집 보장 |
| 게시물 중복 제거·검색 매칭·JSONL/SQLite | 기사 전문 무단 수집·유료벽 우회 |
| cron 등록 및 운영 절차 | 사용자 환경의 자동 설치·설정 변경·cron 등록 |
| 데이터 품질·분석 가이드 | 실제 API 인증을 완료했다는 주장 |

현재 자료는 **문서와 로컬 검증 가능한 실습 코드**다. 장기 운영 전 OAuth 갱신, 정확한 증분 체크포인트, 삭제 정책, 예산·장애 알림을 추가해야 한다. 자세한 구현·검증 경계는 마지막 문서에 기록한다.

**Reddit 연구용 이용 주의:** 공식 정책은 연구 목적에 RFR(Reddit for Researchers) 경로를 요구한다. 일반 Data API 어댑터를 연구용으로 바로 돌리지 말고, 승인된 이용 목적과 제공되는 접근 방식부터 확인한다.

수집된 실제 데이터, 토큰, DB, 백업은 Git 저장소 밖에서 관리한다. 이 강의 폴더는 기존 Wiki canonical 데이터와 분리되어 있다.
