# Configuration

Hermes Agent에서 데이터 분석용 Docker Sandbox를 붙이려면, 핵심은 **Hermes 자체를 Docker에 넣는 것**이 아니라 **Hermes의** `terminal` **backend를** `docker`**로 지정하는 것**입니다. 그러면 Hermes는 호스트에서 실행되면서 `terminal`, 파일 작업, `execute_code` 같은 실행을 Docker 컨테이너 안에서 수행합니다. [GitHub](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/configuration.md?utm_source=chatgpt.com)

가장 간단한 설정은 `~/.hermes/config.yaml`에 아래처럼 넣는 방식입니다.

```
terminal:
  backend: docker
  docker_image: "python:3.11-slim"
```

다만 **데이터 분석 목적**이라면 `python:3.11-slim`보다 NumPy/Pandas와 Node 환경까지 갖춘 기본 이미지가 편합니다.

```
terminal:
  backend: docker
  docker_image: "nikolaik/python-nodejs:python3.11-nodejs20"
```

Hermes 공식 문서 기준으로 Docker backend는 하나의 persistent container를 만들고, 이후 명령을 `docker exec`로 계속 같은 컨테이너에 전달합니다. 그래서 첫 명령에서 `pip install pandas`를 하면 다음 명령에서도 그대로 사용할 수 있습니다. `/new`, `/reset`, subagent에서도 컨테이너 상태를 유지하도록 구성할 수 있습니다. [GitHub](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/configuration.md?utm_source=chatgpt.com)

### 데이터 파일까지 Hermes가 읽게 하려면

예를 들어 Mac의 다음 폴더가 있다고 하겠습니다.

```
~/data-analysis/
├── sales.csv
├── customers.xlsx
└── notebooks/
```

Hermes를 이 디렉터리에서 실행하고,

```
cd ~/data-analysis
hermes
```

설정을 이렇게 하면:

```
terminal:
  backend: docker
  docker_image: "nikolaik/python-nodejs:python3.11-nodejs20"
  docker_mount_cwd_to_workspace: true
```

호스트의

```
~/data-analysis
```

가 Docker 내부에서는

```
/workspace
```

로 보입니다. 즉 Hermes에게

```
sales.csv를 pandas로 분석해서
매출 추이와 이상치를 찾아줘.
```

라고 하면 내부적으로는 대략 다음 환경을 사용하게 됩니다.

```
Mac
 │
 │ Hermes Agent
 ▼
┌─────────────────────────┐
│ Docker Sandbox          │
│                         │
│ /workspace              │
│ ├─ sales.csv            │
│ ├─ customers.xlsx       │
│                         │
│ Python                  │
│ pandas                  │
│ numpy                   │
│ matplotlib              │
└─────────────────────────┘
```

`docker_mount_cwd_to_workspace: true`는 편리하지만 **현재 디렉터리를 컨테이너에 직접 노출하는 것**이므로, 민감한 프로젝트 전체를 무심코 마운트하지 않는 것이 좋습니다. 공식 문서도 이 옵션을 sandbox isolation과의 보안 트레이드오프로 설명합니다. [GitHub](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/configuration.md?utm_source=chatgpt.com)

### 제가 권하는 데이터 분석용 설정

```
terminal:
  backend: docker

  docker_image: "nikolaik/python-nodejs:python3.11-nodejs20"

  # Hermes를 실행한 현재 폴더 → /workspace
  docker_mount_cwd_to_workspace: true

  # 컨테이너 상태 유지
  container_persistent: true

  # 분석 작업용 리소스
  container_cpu: 4
  container_memory: 8192
  container_disk: 51200
```

Hermes는 Docker/컨테이너 backend에 CPU, 메모리, 디스크 제한도 둘 수 있습니다. 환경변수 기준 기본값은 CPU 1코어, 메모리 5120MB, 디스크 51200MB입니다. [GitHub](https://github.com/nousresearch/hermes-agent/blob/main/website/docs/reference/environment-variables.md?utm_source=chatgpt.com)

그다음 Hermes에서 최초 한 번:

```
데이터 분석 환경을 구성해줘.
pandas, numpy, scipy, matplotlib,
seaborn, scikit-learn, openpyxl을 설치해.
```

또는 직접:

```
pip install pandas numpy scipy matplotlib seaborn scikit-learn openpyxl pyarrow
```

하면 됩니다.

### 인터넷을 차단한 분석 Sandbox도 가능

외부 통신이 필요 없는 CSV/XLSX 분석이라면 다음처럼 구성할 수 있습니다.

```
terminal:
  backend: docker
  docker_image: "nikolaik/python-nodejs:python3.11-nodejs20"
  docker_mount_cwd_to_workspace: true
  docker_network: false
```

이 경우 sandbox가 `--network=none` 상태로 실행되어 Hermes가 분석 과정에서 외부로 데이터를 보내는 것을 막을 수 있습니다. Hermes 문서에서도 `docker_network: false`를 공식적인 network-egress 차단 방법으로 제공합니다. [GitHub](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/configuration.md?utm_source=chatgpt.com)

다만 패키지를 `pip install`해야 한다면 인터넷이 필요하므로, **필요 패키지가 이미 포함된 custom Docker image를 만들어 두는 방식**이 가장 깔끔합니다.

예를 들어:

```
FROM python:3.11-slim

RUN pip install --no-cache-dir \
    pandas \
    numpy \
    scipy \
    matplotlib \
    seaborn \
    scikit-learn \
    openpyxl \
    pyarrow \
    jupyter

WORKDIR /workspace
```

빌드:

```
docker build -t hermes-data-analysis .
```

Hermes:

```
terminal:
  backend: docker
  docker_image: "hermes-data-analysis"
  docker_mount_cwd_to_workspace: true
  docker_network: false
  container_cpu: 4
  container_memory: 8192
```

그러면 구조가 상당히 안전해집니다.

```
                   Hermes Agent
                       │
               terminal / execute_code
                       │
                       ▼
             ┌──────────────────┐
             │ Docker Sandbox   │
             │                  │
CSV / XLSX → │ /workspace       │
             │                  │
             │ pandas / numpy   │
             │ sklearn          │
             │ matplotlib       │
             │                  │
             │ network = NONE   │
             └──────────────────┘
```

**따라서 데이터 분석용으로는 아래 3개가 핵심입니다.**

```
terminal:
  backend: docker
  docker_image: "hermes-data-analysis"
  docker_mount_cwd_to_workspace: true
```

보안을 조금 더 중시하면:

```
  docker_network: false
```

까지 추가하면 됩니다.

그리고 여기서 중요한 구분이 하나 있습니다. `docker run nousresearch/hermes-agent`**는 Hermes 자체를 Docker 안에서 실행하는 방식이고**, 지금 말씀하신 데이터 분석 Sandbox 목적에는 `terminal.backend: docker` **방식이 더 적합합니다.** 공식 Hermes 문서에서도 이 두 방식을 별개의 구성으로 구분합니다. [Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/docker/?utm_source=chatgpt.com)

원하시면 제가 다음 답변에서 **Mac + Hermes + Docker Desktop 기준으로** `config.yaml` **→ Dockerfile → 실행 명령 → CSV/XLSX 분석 테스트까지 그대로 복사해서 쓸 수 있는 완성 구성**으로 정리해드릴 수 있습니다.