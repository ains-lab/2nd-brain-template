[oh-my-hermes GitHub 저장소](https://github.com/rlaope/oh-my-hermes?utm_source=chatgpt.com)를 현재 README와 Architecture 문서 기준으로 확인했습니다.

한마디로 정리하면, **Oh-My-Hermes(OMH)는 Hermes Agent 위에 설치해서 “어떤 모델을 쓰고 → 어떤 방식으로 작업하고 → 어떤 전문 Skill을 붙이고 → 결과가 정말 검증됐는지”까지 관리하는 운영/워크플로우 계층**입니다. Hermes 자체를 대체하는 것이 아니라 Hermes를 더 체계적인 에이전트 시스템으로 만들어 줍니다. [GitHub](https://github.com/rlaope/oh-my-hermes/blob/main/README.md?utm_source=chatgpt.com)

## 주요 기능


| 기능                                | 쉽게 설명하면                                | 활용 예                             |
| --------------------------------- | -------------------------------------- | -------------------------------- |
| 🧠 **Mixture-of-Models Routing**  | 작업마다 적합한 LLM 자동 선택                     | 단순 작업→빠른 모델, 설계→강한 추론 모델         |
| 🎛️ **모델별 Prompt 최적화**            | GPT/Claude/Gemini/Kimi 등 특성에 맞게 지시문 조정 | 같은 작업도 모델별 최적 프롬프트               |
| ⚡ **병렬 작업**                       | 큰 작업을 독립적인 여러 작업으로 나눠 동시에 실행           | 코드 분석·문서 조사 병렬화                  |
| 🎼 **Codex/Claude Code 위임**       | 실제 코딩 작업을 별도 coding executor에 위임       | Hermes가 계획 → Codex가 구현           |
| 🔬 **Research Workflow**          | 웹·코드 등을 조사하고 출처와 불확실성 관리               | 논문/기술 조사                         |
| 🧩 **100+ 전문 Skills**             | 작업 종류에 맞는 전문 Skill 자동 적용               | Backend, Security, QA, PDF, 문서 등 |
| 🧠 **Long-term Project Memory**   | 프로젝트 지식을 검토 후 장기 기억                    | 이전 결정·용어·설계 재사용                  |
| 🔎 **Code Search / UML**          | 코드 구조를 분석하고 아키텍처 시각화                   | 대규모 repository 분석                |
| 🛡️ **Guardrails / Verification** | 실행했다는 주장과 실제 검증 결과를 구분                 | 테스트 안 했는데 “완료” 처리 방지             |
| 📊 **HUD / 비용 추적**                | 모델·토큰·비용·진행 상태를 실시간 표시                 | Agent 작업 모니터링                    |


현재 README는 OMH의 핵심을 **coding intelligence + long-term memory + optimized workflow packages**라는 세 축으로 설명합니다. [GitHub](https://github.com/rlaope/oh-my-hermes)

### 1. 작업에 맞는 AI 모델 자동 선택

상당히 중요한 기능입니다.

OMH는 모든 작업에 같은 LLM을 쓰는 대신 작업을 `ultrabrain`, `deep`, `architect`, `quick`, `writing`, `visual-engineering` 등의 category로 분류하고, 각 category에 **모델 + reasoning effort** 체인을 연결합니다. 사용자가 이 체인을 직접 수정할 수도 있습니다. [GitHub](https://github.com/rlaope/oh-my-hermes)

예를 들면 개념적으로:

```
"파일 이름 하나 바꿔줘"
        ↓
quick
        ↓
빠르고 저렴한 모델

"이 시스템 아키텍처 분석해줘"
        ↓
architect
        ↓
강한 추론 모델

"복잡한 문제를 깊게 분석해줘"
        ↓
ultrabrain
        ↓
최상위 reasoning 모델
```

즉 **하나의 Agent가 여러 LLM을 작업 특성에 맞춰 사용하는 구조**입니다.

### 2. 모델별 Prompt 최적화

GPT, Claude, Gemini, Qwen, DeepSeek 같은 모델들은 같은 프롬프트를 줘도 행동 특성이 다릅니다.

OMH는 모델 family별 calibration을 적용합니다. README 기준으로 여러 모델 family에 각각 별도의 지시 블록을 적용하고, 실제 benchmark를 통해 도움이 되는 최적화만 유지하는 방향입니다. [GitHub](https://github.com/rlaope/oh-my-hermes)

따라서 단순한

```
Hermes → LLM
```

보다는

```
Hermes
   ↓
OMH
   ↓
작업 분석
   ↓
모델 선택
   ↓
해당 모델에 맞는 Prompt
   ↓
LLM 실행
```

에 가깝습니다.

### 3. 큰 작업을 병렬 처리

`ulw-work`가 대표적입니다.

계획을 여러 독립적인 작업 단위로 나누고 병렬 실행할 수 있습니다. 코드 작업의 경우 충돌을 줄이기 위해 서로 같은 파일을 건드리지 않는 단위로 분리하는 구조를 사용합니다. [GitHub](https://github.com/rlaope/oh-my-hermes)

예를 들어:

```
"이 프로젝트 전체를 분석하고 개선해줘"

             ┌→ Agent A : Backend 분석
             │
Hermes → OMH ├→ Agent B : Security 분석
             │
             ├→ Agent C : Test 분석
             │
             └→ Agent D : Documentation 분석
                         ↓
                    결과 통합
                         ↓
                       검증
```

사용자께서 이전에 관심을 가지셨던 **논문 자동화 파이프라인** 같은 작업에도 이 구조가 상당히 유용합니다.

### 4. Codex / Claude Code 등에 실제 코딩 위임

OMH는 Hermes가 모든 코드를 직접 처리하도록 강제하지 않습니다.

README의 `ulw-maestro`는 Codex나 Claude Code 같은 coding executor에게 작업을 넘기는 별도 lane을 제공합니다. 중요한 것은 **“누가 판단하는가”와 “누가 실제 코드를 수정하는가”를 분리**한다는 점입니다. [GitHub](https://github.com/rlaope/oh-my-hermes)

개념적으로:

```
사용자
  ↓
Hermes
  ↓
OMH
  ├─ 요구사항 분석
  ├─ Research
  ├─ Plan
  └─ Executor 선택
          ↓
   ┌───────────────┐
   │ Codex         │
   │ Claude Code   │
   │ 기타 Executor │
   └───────────────┘
          ↓
       코드 작성
          ↓
       Test / QA
          ↓
        검증
```

### 5. Ultra Workflow

현재 README에는 다음과 같은 핵심 `ulw-*` workflow가 제시되어 있습니다. [GitHub](https://github.com/rlaope/oh-my-hermes)

- `ulw-context` — 프로젝트 용어와 기존 context 정리
- `ulw-interview` — 질문을 통해 요구사항 명확화
- `ulw-research` — 코드와 웹을 조사하고 근거 확인
- `ulw-plan` — 실행 계획 수립
- `ulw-work` — 계획을 병렬 실행
- `ulw-maestro` — Codex/Claude Code 등에 작업 위임
- `ulw-loop` — Plan → Build → Review 반복
- `ulw-qa` — 공격적인 QA/검증
- `ulw-perf` — 성능 병목 측정 및 개선

따라서 복잡한 프로젝트는 대략

```
Context
   ↓
Interview
   ↓
Research
   ↓
Plan
   ↓
Work / Maestro
   ↓
QA
   ↓
Loop
   ↓
완료
```

처럼 운영할 수 있습니다.

### 6. 100개 이상의 전문 Skill

OMH의 또 다른 핵심은 **전문가 역할을 Skill 형태로 작업에 자동 주입**한다는 것입니다.

README에는 frontend, backend, Rust, debugging, inference serving, security review, performance, refactoring, design quality, verification 등 많은 전문 Skill catalog가 있다고 설명합니다. [GitHub](https://github.com/rlaope/oh-my-hermes)

즉 사용자가 매번

```
보안 전문가처럼 분석해줘.
코드 리뷰도 해줘.
성능도 검사해줘.
테스트도 해줘.
```

라고 일일이 지정하기보다는 OMH가 요청을 보고 필요한 Skill을 선택하는 방식입니다.

### 7. 장기 프로젝트 Memory

개인적으로 OMH에서 연구·장기 프로젝트에 특히 중요한 기능입니다.

단순히 대화를 모두 기억하는 방식이 아니라,

```
Conversation
      ↓
Memory Candidate
      ↓
Review
      ↓
승인
      ↓
Project Memory
      ↓
다음 Session에서 Recall
```

이라는 구조입니다.

승인된 memory에는 provenance와 review 시점이 붙고, 오래되면 중요도가 낮아지는 식으로 관리합니다. Hermes 자체 memory를 직접 수정하는 것이 아니라 **OMH 자체 file-backed memory**를 별도로 운영합니다. [GitHub](https://github.com/rlaope/oh-my-hermes)

이것은 장기간 진행되는 **박사논문 연구 프로젝트**처럼 이전 논문, 연구 gap, 실험 결과, 결정사항을 계속 축적해야 하는 경우에 특히 잘 맞는 구조입니다.

### 8. “했다고 말하는 것”과 “실제로 검증된 것”을 구분

OMH에서 제가 특히 중요한 설계라고 보는 부분입니다.

상태를 대략

```
Prepared
   ↓
Observed
   ↓
Verified
```

로 구분합니다. [GitHub](https://github.com/rlaope/oh-my-hermes/blob/main/README.md?utm_source=chatgpt.com)

예를 들어:

```
Plan · not run
```

은 계획만 만들었다는 뜻이고,

```
Code · running
```

은 실제 executor가 실행 중이라는 뜻이며,

```
Code · reported done
```

은 executor가 끝났다고 보고했지만 아직 검증되지 않았다는 의미입니다. [GitHub](https://github.com/rlaope/oh-my-hermes)

LLM Agent에서 흔히 발생하는 **“실제로 테스트하지 않았는데 테스트했다고 말하는 문제”**를 줄이기 위한 구조입니다.

---

## 전체 구조를 아주 쉽게 보면

OMH의 역할은 다음처럼 이해하면 됩니다.

```
                  사용자
                    │
                    ▼
             ┌─────────────┐
             │ Hermes Agent│
             └──────┬──────┘
                    │
                    ▼
        ┌───────────────────────┐
        │     Oh-My-Hermes      │
        │                       │
        │  요구사항 분석         │
        │  Workflow 선택         │
        │  Model Routing        │
        │  Skill 선택            │
        │  Memory               │
        │  Parallel Work        │
        │  Verification         │
        └───────────┬───────────┘
                    │
       ┌────────────┼─────────────┐
       ▼            ▼             ▼
    Hermes        Codex      Claude Code
    Agent        Executor      Executor
       │            │             │
       └────────────┼─────────────┘
                    ▼
             Test / Review
                    │
                    ▼
                 결과 검증
```

즉 **Hermes가 두뇌와 대화 인터페이스라면, OMH는 Hermes를 전문적인 Multi-Agent 작업 시스템처럼 운영하기 위한 orchestration/control layer**라고 이해하시면 가장 쉽습니다. Architecture 문서 역시 Hermes는 사용자-facing reasoning을 유지하고, OMH는 local contract/routing/memory/quality gate를 제공하며, 실제 executor가 구현을 담당하는 방향으로 설명합니다. [Ithub](https://ithub.global.ssl.fastly.net/rlaope/oh-my-hermes/blob/main/docs/ARCHITECTURE.md?utm_source=chatgpt.com)

특히 지금 구상하시는 **“Hermes 기반 논문 자동 수집 → 분석 → LLM Wiki/지식 축적 → Research Gap 발견 → 새로운 논문 아이디어 생성” 파이프라인**과 OMH를 연결하면 꽤 흥미로운 구조가 나옵니다. `ulw-research + ulw-work + OMH Memory + 주기적 Research Agent`를 중심으로 설계할 수 있습니다.