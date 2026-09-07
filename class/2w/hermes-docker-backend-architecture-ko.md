# Hermes Agent의 Docker terminal backend: 아키텍처와 데이터 분석 워크플로우

작성일: 2026-09-07  
대상: Hermes를 호스트에서 실행하고 분석용 코드 실행을 Docker로 분리하려는 사용자

> 이 문서는 앞선 대화의 개념을 공식 문서와 소스로 재검증한 운영 안내서다. 구현 설명은 NousResearch/hermes-agent의 `0daa993450d3dadfce0ed514abd333b0907da0d0` 커밋을 기준으로 한다. 설치된 버전에서는 설정과 수명 주기가 다를 수 있다. 이 문서를 작성하면서 사용자 Hermes 설정을 변경하거나 분석 컨테이너를 생성하지 않았다.

## 1. 핵심 개념

`terminal.backend: docker`는 **Hermes가 명령을 실행할 장소를 Docker 컨테이너로 지정하는 설정**이다. Hermes Agent, 모델 API 통신, 대화 관리까지 자동으로 컨테이너 안으로 이동하는 설정은 아니다.

호스트에서 실행되는 Hermes가 Docker CLI와 Docker daemon을 통해 실행 컨테이너를 준비한다. `terminal`의 셸 명령, backend에 연결된 파일 도구, `execute_code`의 Python 실행은 그 환경을 사용한다. 기본 지속 모드에서는 같은 프로필의 세션들이 장기 실행 컨테이너를 재사용한다. 최초 호출에서 컨테이너를 만들고 이후 호출은 주로 `docker exec`를 사용한다. [구현: 환경 선택과 세션 범위][S1] [구현: Docker 실행][S2]

다음 항목은 서로 다르다.

| 항목 | 의미 |
| --- | --- |
| Docker image | Python, 분석 라이브러리, OS 패키지가 들어 있는 실행 환경의 원본 |
| Container | 이미지에서 생성되어 실제 명령과 프로세스가 실행되는 인스턴스 |
| Persistent container | 여러 도구 호출 또는 세션에서 재사용하는 살아 있는 컨테이너 |
| Persistent filesystem | 컨테이너를 재생성해도 다시 연결할 수 있는 저장 공간 |
| `/workspace` | 컨테이너 안의 작업 경로. 호스트 폴더일 수도, Hermes 관리 저장 공간일 수도 있음 |
| Python kernel | `execute_code`의 변수와 import 상태를 가진 Python 프로세스. 파일 보존과 별도 수명 |

`/workspace`가 있다는 사실만으로 Mac의 현재 폴더가 연결되는 것은 아니다. 또한 컨테이너 재시작 후 파일이 남아 있어도 실행 중이던 프로세스나 Python 변수는 사라질 수 있다.

## 2. 전체 아키텍처

다음 그림은 **호스트 Hermes + Docker terminal backend** 구성이다. Mermaid를 지원하지 않는 뷰어에서는 아래 ASCII 흐름을 참고한다.

```mermaid
flowchart TD
    U[사용자: CSV와 XLSX 분석 요청] --> A[호스트의 Hermes Agent]
    A <--> L[모델 API: 판단과 응답 생성]
    A --> T[terminal: 셸 명령]
    A --> E[execute_code: Python 및 도구 조합]
    A --> F[파일 도구: 읽기와 쓰기]
    T --> B[Docker backend 환경 객체]
    E --> B
    F --> B
    B --> D[Docker CLI 및 daemon]
    D --> C[Persistent 실행 컨테이너]
    C --> P[Python과 분석 라이브러리]
    P <--> W[/workspace: 코드와 작업 파일]
    H[선택한 호스트 디렉터리] -. 명시적 bind mount .-> W
    P --> R[표준 출력과 실행 상태]
    R --> B
    B --> A
    A --> O[요약 응답 및 산출물 경로]
    E -. 허용된 도구의 RPC 요청 .-> A
```

```text
요청 → Hermes Agent → terminal 또는 execute_code
     → Docker backend → Docker daemon → persistent container
     → Python → /workspace 또는 /data/input 읽기
     → 집계·검증 → 결과 파일 저장
     → 출력·오류·상태 → Hermes Agent → 사용자 응답
```

그림의 `/workspace`는 실행 컴포넌트가 아니라 컨테이너에서 접근하는 파일시스템 경로다. macOS에서는 Docker Desktop의 Linux VM 안에서 Linux 컨테이너가 실행된다. 마운트된 Mac 폴더는 Docker Desktop의 파일 공유를 통해 컨테이너에 보인다.

## 3. 요청부터 결과까지

1. **요청 해석:** Hermes는 사용자 요청과 대화 문맥으로 필요한 데이터, 분석 방법, 도구를 정한다.
2. **도구 선택:** 셸 명령은 `terminal`, Python 실행과 여러 도구의 조합은 `execute_code`, 파일 확인은 파일 도구로 처리할 수 있다. 모든 요청이 `terminal`과 `execute_code`를 차례로 통과하는 것은 아니다.
3. **환경 결정:** 설정, 프로필, 세션 식별자에 따라 Docker 환경을 선택한다. 아직 없다면 지연 생성한다.
4. **컨테이너 생성 또는 재사용:** 이미지, 마운트, 네트워크, 자원 제한 등을 적용한다. 기준 구현의 신규 컨테이너는 `docker run -d ... <image> sleep infinity` 형태로 유지된다. 실제 인자에는 보안·환경 설정이 추가된다.
5. **명령 실행:** backend가 `docker exec`로 셸 또는 Python 프로세스를 실행한다. 분석 라이브러리는 호스트가 아니라 실행 이미지에 있어야 한다.
6. **파일 접근:** 코드가 `/workspace`, `/data/input` 등 컨테이너 경로에서 데이터를 읽고 결과를 쓴다.
7. **결과 수집:** `terminal`은 명령 출력과 종료 상태를 반환한다. `execute_code`는 Python 출력, 오류 및 실행 메타데이터를 도구 결과로 정리하며 큰 출력은 제한되거나 파일로 분리될 수 있다.
8. **응답 작성:** Hermes가 결과를 해석해 요약한다. PNG/XLSX 파일이 자동으로 텍스트 응답에 포함되는 것은 아니며, 공유 마운트의 파일 경로 또는 해당 채널의 파일 전달 기능으로 제공한다.

이 흐름은 [terminal 환경 선택][S1], [Docker 실행 구현][S2], [execute_code 구현][S3]을 종합한 것이다.

### `execute_code`는 별도의 Docker 제품이 아니다

`execute_code`는 Python으로 Hermes 도구를 호출하는 Programmatic Tool Calling 기능도 제공한다. Docker backend를 선택하면 같은 backend 환경을 확보하고, 기준 구현에서는 원격 세션 kernel 경로를 먼저 사용한다. 이용할 수 없으면 호출별 Python 스크립트 실행 경로로 전환한다. backend에 Python 3가 필요하다. [S3]

스크립트가 허용된 Hermes 도구를 호출할 때는 RPC로 호스트 측 도구 실행기에 요청을 보낼 수 있다. Docker 경로에서는 요청·응답 파일을 backend로 읽고 쓰는 방식도 사용한다. 따라서 **`docker_network: false`는 컨테이너의 직접 네트워크를 차단하지만, Hermes의 모델 통신이나 RPC로 호출되는 호스트 측 웹 도구까지 차단하지 않는다.** 엄격한 외부 통신 차단에는 Hermes 도구 권한과 호스트 네트워크 정책도 필요하다. [S3]

Python 변수나 셸 상태를 영구 저장소로 취급하지 않는다. 재현할 분석은 스크립트와 결과 파일로 남기고, 실행 시 작업 경로와 입력을 명시하는 구성이 좋다.

## 4. 지속성과 세션 격리

### 기본 지속 모드

`container_persistent: true`에서는 Hermes가 `/root`와, 별도 마운트가 없는 `/workspace`를 관리 저장 공간에 연결한다. 기본 저장 루트는 `~/.hermes/sandboxes/`이며 실제 하위 경로는 작업 식별자 등으로 결정된다. `/root`는 호스트의 실제 홈 폴더 전체를 의미하지 않는다. [S2]

최신 기준 구현에서는 같은 프로필의 대화, `/new`, `/reset`, subagent가 기본적으로 컨테이너를 공유한다. `docker_persist_across_processes: true`는 Hermes 프로세스를 종료하고 다시 실행해도 컨테이너를 찾아 재사용하는 별도의 정책이다. 프로필 간 공유는 `docker_shared_container_key`를 명시적으로 설정하는 경우와 구분한다. [S1] [S4]

### 세션별 격리 모드

`container_persistent: false`는 기준 버전에서 세션별 컨테이너를 사용하도록 전환한다. 정상적인 세션 범위에서는 프로세스 간 지속 재사용도 해제되며, 세션 종료·유휴 정리 시 컨테이너가 제거된다. subagent는 부모 환경을 공유하므로 subagent마다 독립된 보안 경계가 생기는 것은 아니다. [S1] [S4]

**단, 명시적으로 연결한 호스트 폴더의 파일은 그대로 남는다.** 여러 세션에 동일한 입력·출력 폴더를 마운트하면 그 폴더를 통한 데이터 공유는 계속된다. `container_persistent: false`가 bind mount까지 지우거나 격리해 주지는 않는다.

| 상황 | 유지되는 것 | 잃을 수 있는 것 |
| --- | --- | --- |
| 같은 실행 컨테이너 재사용 | 파일, 설치 패키지, 살아 있는 프로세스 | 별도 종료·timeout이 발생한 프로세스 상태 |
| 같은 컨테이너 정지 후 시작 | 이미지와 컨테이너 쓰기 계층, bind mount 파일 | 백그라운드 프로세스, Python 메모리, tmpfs 내용 |
| 컨테이너 제거 후 새로 생성 | 이미지에 포함된 패키지, 다시 연결한 호스트 파일 | 기존 쓰기 계층에만 설치한 패키지·파일 |
| `container_persistent: false` 세션 정리 | 명시적 호스트 마운트의 파일 | 임시 작업 공간, 세션 프로세스 |

`pip install`로 즉석 설치한 패키지는 같은 컨테이너에서는 계속 사용할 수 있지만 이미지에 반영되지는 않는다. `/usr/local` 등에 설치했다면 컨테이너 재생성 시 없어질 수 있다. 반복 분석에 필요한 패키지는 custom image에 넣는다.

## 5. 주요 설정

설정 파일은 일반적으로 `~/.hermes/config.yaml`이다. 프로필 또는 `HERMES_HOME`을 따로 사용하면 해당 환경의 설정 파일을 수정한다. 다음 표의 기본값은 기준 구현과 공식 설정 문서의 값이다. [설정 문서][D1] [설정 매핑][S4]

| 키 (`terminal` 아래) | 기본값 | 의미와 권장 사용 |
| --- | --- | --- |
| `backend` | `local` | 분석용 실행 분리에는 `docker` |
| `docker_image` | 문서 예시: Python+Node 이미지 | 실제 분석 패키지를 포함한 자체 이미지를 권장 |
| `docker_mount_cwd_to_workspace` | `false` | 실행 디렉터리를 `/workspace`에 연결하는 명시적 opt-in |
| `container_persistent` | `true` | 관리 파일 보존과 Docker 환경 공유 정책. `false`는 세션별 격리 |
| `docker_persist_across_processes` | `true` | Hermes 종료 이후 컨테이너 재사용. 파일 보존과 별도 |
| `docker_network` | `true` | `false`이면 실행 컨테이너에 `--network=none` |
| `container_cpu` | `1` | CPU 코어 환산 한도. `0`은 제한 없음 |
| `container_memory` | `5120` | 문서상 MB 단위, Docker에는 `5120m` 형태 전달. `0`은 제한 없음 |
| `container_disk` | `51200` | 지원 storage driver에서만 컨테이너 디스크 quota 적용 |
| `timeout` | `180` | terminal 명령 timeout, 초 단위 |
| `lifetime_seconds` | `300` | 유휴 정리 기준. 기본 프로세스 간 지속 모드에서는 이것만으로 실행 컨테이너가 종료되지 않음 |
| `docker_volumes` | `[]` | `호스트절대경로:컨테이너경로[:ro]` 목록 |
| `docker_run_as_host_user` | `false` | 호스트 UID/GID로 실행. 이미지·마운트 쓰기 권한 확인 필요 |

### `docker_mount_cwd_to_workspace`

예를 들어 호스트에서 다음과 같이 실행한다.

```bash
cd "$HOME/data-analysis"
hermes
```

설정이 `docker_mount_cwd_to_workspace: true`이면 해당 디렉터리가 `/workspace`에 연결된다. 호스트의 `sales.csv`는 `/workspace/sales.csv`로 읽는다. CLI와 달리 Gateway/Desktop에서는 해당 세션에 실제로 연결된 workspace를 확인해야 한다.

이 옵션은 파일 복사가 아니라 **기본적으로 읽기·쓰기가 가능한 bind mount**다. `/workspace`에서 삭제하거나 덮어쓰면 원본에도 영향을 준다. 원본 보존이 필요하면 자동 마운트를 끄고 `docker_volumes`로 입력 경로를 `:ro` 연결한다. `/workspace` 명시 마운트와 자동 마운트를 동시에 지정하지 않는다. [S2]

### CPU·memory·disk의 실제 제한

`container_cpu: 2`는 CPU 사용량을 두 코어 수준으로 제한하며, 특정 물리 코어 두 개를 전용 할당하는 뜻은 아니다. `container_memory: 4096`은 컨테이너 메모리 한도이며 초과 시 프로세스가 OOM으로 종료될 수 있다. 공유 컨테이너에서는 여러 세션과 subagent가 같은 한도를 나눠 쓴다.

기준 구현은 cgroup 제한 기능을 검사한다. 일부 rootless/LXC 환경에서 사용할 수 없으면 경고 후 CPU·memory·PID 제한 없이 실행할 수 있으므로, 설정 파일만 보고 적용됐다고 판단하지 않는다. `container_disk`는 storage driver 지원 조건이 있고 macOS 호스트 경로에서는 적용을 생략한다. bind mount 입력·출력 용량을 이 값이 제한해 주는 것도 아니다. [S2]

### 네트워크와 재사용

오프라인 분석은 `docker_network: false`로 한다. 필요한 패키지는 이미지 빌드 때 설치한다. 실행 중 `pip install`, 외부 API 요청, 인터넷 파일 다운로드는 실패하는 것이 정상이다. 이미지 pull/build 자체는 실행 컨테이너의 네트워크 설정과 별개다.

기존 네트워크 허용 컨테이너를 재사용하는 상태에서 `false`로 전환하면 기준 구현은 호환되지 않는 컨테이너를 제거하고 새로 만든다. 반면 이미지·마운트·자원 설정 변경이 기존 컨테이너에 모두 자동 적용된다고 가정해서는 안 된다. 공유 컨테이너는 최초 생성 설정이 남을 수 있으므로 결과를 보관하고 실제 설정을 확인한다. [S2] [D1]

## 6. config.yaml 예제

### A. 개인의 반복 분석: 간편 구성

다음은 **기존 `terminal` 섹션에 병합할 예시**다. 기존 모델 설정이나 인증 설정을 대체하지 않는다.

```yaml
terminal:
  backend: docker
  docker_image: "hermes-analysis:2026-09"
  docker_mount_cwd_to_workspace: true
  container_persistent: true
  docker_persist_across_processes: true
  docker_network: false
  container_cpu: 2
  container_memory: 4096
  container_disk: 0
  timeout: 180
```

`container_disk: 0`은 이식 가능한 예시를 위해 quota를 지정하지 않은 선택이다. 디스크 사용량 관리는 별도로 한다. 실행 폴더에는 이번 분석에 필요한 파일만 두고, 데이터는 원본의 복사본을 사용한다.

### B. 권장 구성: 읽기 전용 입력 + 별도 출력 + 세션별 실행

먼저 입력과 출력 폴더를 만들고, 아래 `/ABS/PATH/...`를 실제 호스트 **절대 경로**로 바꾼다. `:ro`가 없는 출력 마운트는 읽기·쓰기 가능하다.

```yaml
terminal:
  backend: docker
  docker_image: "hermes-analysis:2026-09"
  docker_mount_cwd_to_workspace: false
  docker_volumes:
    - "/ABS/PATH/data-analysis/input:/data/input:ro"
    - "/ABS/PATH/data-analysis/output:/data/output"
  container_persistent: false
  docker_persist_across_processes: false
  docker_network: false
  docker_forward_env: []
  container_cpu: 2
  container_memory: 4096
  container_disk: 0
  timeout: 180
  lifetime_seconds: 1800
```

분석 중 `/workspace`는 임시 코드·작업용으로 사용하고, 최종 결과는 `/data/output`에 쓴다. 세션별 원본·산출물 분리까지 필요하면 각 세션/프로필에 다른 호스트 디렉터리를 사용한다. `docker_forward_env: []`만으로 모든 인증 정보 전달 경로가 사라지는 것은 아니므로 사용하는 skill과 도구의 환경변수 요구사항도 확인한다.

Linux에서 호스트 파일 소유권이 문제가 되면 `docker_run_as_host_user: true`를 검토한다. 다만 UID/GID에 맞는 디렉터리 권한과 이미지 호환성을 먼저 확인한다. 분석에 필요하지 않은 토큰, SSH 키, Docker socket은 전달하지 않는다.

## 7. 데이터 분석용 custom image

custom image의 역할은 **분석 실행 의존성을 미리 설치하고 재현 가능한 환경을 배포하는 것**이다. Hermes Agent 자체나 모델 API 키를 넣는 이미지가 아니다.

다음 Dockerfile은 CSV/XLSX 분석, 차트 저장, 한국어 글꼴을 위한 시작 예시다. Python+Node 기본 이미지에 pandas 등의 분석 패키지가 모두 있다고 가정하지 않고 명시적으로 설치한다.

```dockerfile
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/matplotlib

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash ca-certificates fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir \
    numpy pandas openpyxl matplotlib pyarrow

WORKDIR /workspace
CMD ["sleep", "infinity"]
```

이 예시는 패키지 버전을 고정하지 않은 출발점이다. 운영에서는 검증한 버전으로 requirements/lock 파일을 만들고 base image digest도 고정해 같은 환경을 다시 만들 수 있게 한다. 위 예시는 Python 분석에 필요한 범위이며 Node.js가 필요한 Hermes 도구나 skill을 쓰려면 Node도 별도로 설치하거나 검증된 Python+Node 이미지를 기반으로 한다.

의존성의 역할은 다음과 같다.

| 의존성 | 역할 |
| --- | --- |
| `numpy` | 수치 연산 |
| `pandas` | CSV/XLSX 읽기, 결합, 집계 |
| `openpyxl` | `.xlsx` 읽기·쓰기 엔진 |
| `matplotlib` | 화면 없는 컨테이너에서 PNG 차트 생성 |
| `pyarrow` | Parquet 등 열 기반 파일 처리 |
| `fonts-noto-cjk` | 한국어 차트 글꼴. matplotlib에서 해당 글꼴을 선택해야 함 |
| `bash` | backend의 셸 명령 실행 |

빌드와 의존성 확인은 호스트에서 수행한다.

```bash
docker build -t hermes-analysis:2026-09 .
docker run --rm --network none hermes-analysis:2026-09 \
  python -c 'import numpy, pandas, openpyxl, matplotlib, pyarrow; print("analysis dependencies OK")'
```

Hermes는 컨테이너 유지 명령을 직접 전달하므로 이미지의 `CMD`가 Hermes 작업을 지휘하지 않는다. Hermes와 충돌하는 사용자 정의 `ENTRYPOINT`는 추가하지 않는 편이 단순하다. `/root`와 `/workspace`는 실행 시 마운트로 가려질 수 있어 이미지의 핵심 의존성을 그 안에만 설치하지 않는다. [S2]

## 8. 실제 CSV/XLSX 분석 예시

### 8.1. 입력 준비

권장 구성 B를 기준으로 한다.

```text
data-analysis/
├── Dockerfile
├── input/
│   ├── sales.csv
│   └── customers.xlsx
└── output/
```

`sales.csv`의 예시 내용:

```csv
order_id,date,customer_id,amount
O001,2026-07-03,C001,120000
O002,2026-07-20,C002,80000
O003,2026-08-01,C001,200000
O004,2026-08-15,C003,50000
```

`customers.xlsx`의 `customers` 시트:

| customer_id | segment |
| --- | --- |
| C001 | 기업 |
| C002 | 개인 |
| C003 | 개인 |

금액은 원 단위, 날짜는 주문일, `order_id`는 주문별 유일 키로 가정한다. 예시 값은 설명용 가상 데이터다.

### 8.2. Hermes에 전달할 요청

```text
/data/input/sales.csv와 customers.xlsx의 customers 시트를 분석해 주세요.
원본은 수정하지 말고, 작업 코드는 /workspace/analyze.py에 저장해 주세요.

1. 열 이름, 데이터형, 결측치, 중복 주문, 잘못된 날짜·금액을 검사하세요.
2. customer_id로 결합하되 customers 쪽 키가 유일한지 먼저 확인하세요.
3. 고객 정보와 매칭되지 않는 주문은 삭제하지 말고 따로 보고하세요.
4. 월별 매출과 고객군별 매출을 계산하세요.
5. /data/output에 monthly_sales.csv, segment_sales.csv,
   analysis.xlsx, monthly_sales.png, summary.md를 저장하세요.
6. 결과 합계가 원본의 유효 금액 합계와 일치하는지 확인하고,
   제외·보정한 행 수와 적용 기준을 summary.md에 기록하세요.
7. 사용한 analyze.py와 라이브러리 버전도 /data/output에 남겨 주세요.
외부 통신은 사용하지 마세요.
```

### 8.3. 실행 단계

| 단계 | Hermes가 수행할 작업 | 확인 기준 |
| --- | --- | --- |
| 환경 확인 | Python 및 패키지 import, 입력 파일·시트 목록 확인 | 필요한 파일과 의존성이 있음 |
| 품질 검사 | CSV 타입 지정, Excel 시트 확인, 날짜·금액 파싱 | 오류·결측·중복 수가 기록됨 |
| 결합 | 고객 키 유일성 검사 후 `many_to_one` 관계로 join | 주문 행 수가 불필요하게 증가하지 않음 |
| 집계 | 월별·고객군별 매출 계산 | 집계 합계가 원본 합계와 일치 |
| 시각화 | 월별 막대/선 차트 PNG 생성 | 축·단위·기간이 명확함 |
| 저장 | CSV, XLSX, PNG, Markdown, 실행 코드 저장 | `/data/output`에 실제 파일 존재 |
| 재확인 | 산출물 재열기, 주요 합계 비교 | 읽기 가능하고 값이 일치 |
| 반환 | 요약과 호스트 output 경로 안내 | 사용자에게 결과 파일이 전달됨 |

`terminal`을 사용한다면 실행 명령은 예를 들어 다음과 같다. `execute_code`에서 같은 입력을 읽어 분석하는 방식도 가능하다.

```bash
mkdir -p /workspace
cd /workspace && python analyze.py
```

위 명령은 **Hermes가 먼저 `analyze.py`를 작성한 뒤** 실행하는 예시다. 이 문서에 분석 스크립트가 내장되어 있지는 않다.

### 8.4. 예시 데이터의 기대 결과

| 월 | 매출 |
| --- | ---: |
| 2026-07 | 200,000원 |
| 2026-08 | 250,000원 |
| 합계 | 450,000원 |

고객군별로 기업은 320,000원, 개인은 130,000원이다. 8월 매출은 7월보다 25% 증가한다. 이 값들은 위 가상 데이터의 산술 기대값이며, 실제 Hermes 실행 결과를 제시한 것은 아니다.

원본 XLSX에 수식이 있다면 `openpyxl`이 Excel처럼 수식을 계산하는 엔진은 아니라는 점을 고려한다. 수식 결과의 캐시 유무와 최신성을 확인하고, 필요한 계산은 분석 코드에서 명시적으로 재계산한다. 날짜·문자열 ID의 선행 0, 통화 단위, 반품의 음수 금액 처리 규칙도 분석 전에 정한다.

## 9. Hermes 자체를 Docker에서 실행하는 방식과 비교

| 구분 | 호스트 Hermes + `terminal.backend: docker` | Docker 안의 Hermes + `terminal.backend: local` |
| --- | --- | --- |
| Agent 프로세스 | 호스트 | Hermes 애플리케이션 컨테이너 |
| 모델 API 통신 | 호스트의 Hermes | 애플리케이션 컨테이너의 Hermes |
| 분석 명령 | 별도 Docker 실행 컨테이너 | Hermes와 같은 컨테이너 |
| 인증·대화 상태 | 호스트의 Hermes 저장 공간 | 컨테이너 내부 또는 별도 상태 볼륨 |
| 주요 목적 | 실행 코드를 Agent와 분리 | Hermes 설치·배포 환경을 패키징 |
| 실행 코드와 Agent 경계 | 별도 실행 컨테이너가 경계 제공 | 같은 컨테이너 내부에서는 경계가 약함 |

두 방식을 함께 쓸 수도 있다. Docker 안의 Hermes에 `terminal.backend: docker`를 지정하면 별도 실행 컨테이너를 제어할 수 있는 Docker CLI와 daemon 접근을 마련해야 한다. 호스트 Docker socket을 전달하는 방식은 강한 호스트 제어 권한을 부여하므로 일반 분석용 기본 구성으로 권하지 않는다.

또한 bind mount의 호스트 경로는 **Docker daemon이 실행되는 쪽의 경로**다. Hermes 애플리케이션 컨테이너 안에서 보이는 경로가 호스트 daemon에서도 존재한다고 가정하면 마운트가 잘못 연결될 수 있다. [Docker bind mount 문서][D2]

## 10. 보안과 격리의 범위

Docker는 파일시스템·프로세스·네트워크를 나누는 실행 경계를 제공한다. 그러나 Linux kernel을 공유하므로 독립 VM과 같은 격리라고 단정할 수 없다. macOS Docker Desktop에서는 그 공유 대상이 Linux VM의 kernel이다.

기준 Docker backend는 capability를 먼저 제거하고 파일 접근·소유권 처리에 필요한 일부를 다시 추가한다. `no-new-privileges`, PID 제한 및 tmpfs 관련 방어도 적용하지만, 호환 모드와 cgroup 지원 등에 따라 달라질 수 있다. 따라서 “모든 capability가 완전히 제거되며 어떤 환경에서도 동일하게 제한된다”는 표현은 부정확하다. [S2]

권장 원칙은 다음과 같다.

- **입력 최소화:** 이번 분석에 필요한 폴더만 `:ro`로 연결한다. 홈 디렉터리 전체와 자격증명 디렉터리는 피한다.
- **출력 분리:** 쓰기 권한은 별도 output 디렉터리에 준다. 결과는 백업하고 보존 정책을 정한다.
- **네트워크 분리:** 외부 데이터가 필요 없는 분석은 `docker_network: false`로 실행한다. 호스트 측 웹 도구와 모델 API 통신은 별도로 통제한다.
- **세션 분리:** 서로 신뢰하지 않는 데이터·사용자·작업은 세션별 실행 및 별도 마운트 경로를 사용한다. 단순 프로필 구분을 적대적 사용자 간 완전한 보안 경계로 간주하지 않는다.
- **권한 최소화:** `--privileged`, Docker socket 마운트, `--network=host` 같은 격리를 약화하는 구성을 추가하지 않는다.
- **재현성 확보:** 패키지를 custom image에 넣고, 입력 해시·실행 코드·라이브러리 버전·처리 규칙을 결과와 함께 보관한다.
- **자원 적용 검증:** CPU·memory 제한을 실제 컨테이너에서 확인한다. tmpfs 및 출력 파일 사용량도 관리한다.

실행 컨테이너를 오프라인으로 만들어도, Hermes가 읽은 데이터 일부를 모델 API에 전달할 수 있다. 민감 데이터의 외부 전달 정책은 실행 격리와 별도로 결정해야 한다.

## 11. 운영 확인과 문제 해결

먼저 Docker 연결을 확인한다.

```bash
docker version
docker info
```

Hermes에서 첫 terminal 호출을 실행한 뒤 관리 컨테이너를 찾는다.

```bash
docker ps -a --filter label=hermes-agent=1 \
  --format 'table {{.ID}}\t{{.Names}}\t{{.Status}}'
```

대상 컨테이너 ID를 실제 값으로 바꿔 설정을 확인한다.

```bash
docker inspect <CONTAINER_ID> --format '{{json .Mounts}}'
docker inspect <CONTAINER_ID> --format '{{.HostConfig.NetworkMode}}'
docker inspect <CONTAINER_ID> --format '{{.HostConfig.NanoCpus}} {{.HostConfig.Memory}}'
docker inspect <CONTAINER_ID> --format '{{json .HostConfig.SecurityOpt}}'
```

설정 B의 기대 상태는 입력 마운트 `RW: false`, 출력 마운트 `RW: true`, 네트워크 `none`, CPU·memory 제한이 0이 아닌 값인 것이다. Docker의 `NanoCpus`는 CPU 수의 10억 배, `Memory`는 바이트 단위이므로 YAML 숫자와 그대로 비교하지 않는다.

| 증상 | 우선 확인할 사항 |
| --- | --- |
| `/workspace`에 입력이 없음 | 자동 마운트 opt-in 여부, 실제 시작 디렉터리, 세션 workspace, 권장 구성 B의 `/data/input` 경로 |
| `ModuleNotFoundError` | 호스트가 아닌 선택한 이미지에 설치했는지, 이전 컨테이너가 재사용 중인지 |
| `pip install` 또는 다운로드 실패 | `docker_network: false`라면 의도된 상태. 이미지 빌드 단계로 의존성 이동 |
| 입력 파일 쓰기 실패 | `:ro`이면 정상. output 디렉터리에 저장 |
| 결과가 호스트에 안 보임 | 임시 `/workspace`가 아니라 마운트된 `/data/output`에 저장했는지 |
| 메모리 부족·강제 종료 | 컨테이너 한도, Docker Desktop VM 메모리, 동시 작업량, XLSX 전체 로딩 크기 |
| 설정을 바꿔도 기존 동작 유지 | 재사용 컨테이너의 실제 image·mount·resource 설정 확인 |
| 다음 세션에 데이터가 남음 | 지속 모드 또는 동일한 명시적 호스트 마운트를 공유하는지 |

컨테이너를 재생성해야 할 때는 먼저 쓰기 계층 안의 필요한 파일을 출력 마운트로 보관하고 작업 프로세스를 종료한다. 일괄 `docker system prune`을 초기 문제 해결 수단으로 쓰지 말고, 해당 Hermes 컨테이너만 식별해 처리한다.

## 12. 적용 순서와 검증 범위

1. 필요한 분석 패키지로 이미지를 빌드한다.
2. 입력·출력 디렉터리를 준비한다.
3. 기존 설정에 구성 A 또는 B를 병합한다.
4. Hermes를 시작하고 Python import와 마운트를 확인한다.
5. 작은 CSV/XLSX 예제로 분석한 뒤 기대 합계와 비교한다.
6. 산출물을 호스트에서 열어 확인한다.
7. 세션 종료·재시작 후 파일과 프로세스의 보존 범위가 의도와 맞는지 확인한다.

이 문서의 설정 키·실행 경로·수명 주기는 공식 소스와 대조했다. Dockerfile과 분석 요청은 적용용 예시이며, 이 문서 작성 과정에서 이미지 빌드나 실제 Hermes 분석 실행까지 검증한 것은 아니다. 로컬 설치 버전과 Docker 환경에 대한 확인은 위 절차로 수행한다.

## 참고 자료

- [Hermes 공식 설정 문서: Docker backend][D1]
- [terminal 환경 선택·세션 식별 구현][S1]
- [Docker 컨테이너 생성·마운트·제한·cleanup 구현][S2]
- [execute_code 및 도구 RPC 구현][S3]
- [terminal backend 설정 매핑과 Docker 환경 생성][S4]
- [Docker 공식 문서: bind mounts][D2]

[S1]: https://github.com/NousResearch/hermes-agent/blob/0daa993450d3dadfce0ed514abd333b0907da0d0/tools/terminal_tool.py
[S2]: https://github.com/NousResearch/hermes-agent/blob/0daa993450d3dadfce0ed514abd333b0907da0d0/tools/environments/docker.py
[S3]: https://github.com/NousResearch/hermes-agent/blob/0daa993450d3dadfce0ed514abd333b0907da0d0/tools/code_execution_tool.py
[S4]: https://github.com/NousResearch/hermes-agent/blob/0daa993450d3dadfce0ed514abd333b0907da0d0/tools/terminal_tool_backends.py
[D1]: https://hermes-agent.nousresearch.com/docs/user-guide/configuration/#docker-backend
[D2]: https://docs.docker.com/engine/storage/bind-mounts/
