가능합니다. Hermes에서는 **“논문 수집 → 중복 제거 → 선별 → 요약 → 파일 저장 → 주간 종합”**을 하나의 Cron 기반 연구 자동화 파이프라인으로 구성하는 방식이 가장 안정적입니다. Hermes 자체가 반복 작업을 실행하는 Cron, Skill 주입, `workdir` 기반 파일 작업을 지원하므로 이 용도와 잘 맞습니다. Hermes Cron은 각 실행마다 새로운 Agent 세션을 만들기 때문에, 자동화 프롬프트와 Skill에 검색 키워드·저장 규칙·요약 형식을 명시해 두는 것이 중요합니다. [GitHub](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md?utm_source=chatgpt.com)

### 추천 아키텍처

```
                [Hermes Gateway]
                       │
                  Cron Scheduler
                 매일 07:00 실행
                       │
                       ▼
             [Paper Collector Skill]
                       │
       ┌───────────────┼────────────────┐
       ▼               ▼                ▼
    OpenAlex       Semantic Scholar    arXiv
       │               │                │
       └───────────────┼────────────────┘
                       ▼
                후보 논문 Metadata
                       │
                       ▼
               [Deduplication]
            DOI / arXiv ID / Title
                       │
                       ▼
              [Relevance Filter]
          keyword + LLM relevance score
                       │
             ┌─────────┴──────────┐
             │                    │
          관련 없음             관련 있음
             │                    │
           폐기                   ▼
                           PDF/Abstract 수집
                                  │
                                  ▼
                           [LLM Summarizer]
                                  │
                 ┌────────────────┼──────────────┐
                 ▼                ▼              ▼
               요약             평가           태그
                 │                │              │
                 └────────────────┼──────────────┘
                                  ▼
                           Markdown 저장
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
              papers/*.md                 index.json/db
                    │
                    ▼
             Weekly Synthesis
                    │
                    ▼
       "이번 주 연구동향 / 연구공백 / 중요논문"
```

논문 검색 소스는 처음부터 너무 많이 붙이지 말고 **OpenAlex + Semantic Scholar + arXiv** 정도로 시작하는 것을 권합니다. 특히 Semantic Scholar는 논문 metadata뿐 아니라 추천 논문 API도 제공하므로, 단순 키워드 검색에서 나아가 **“내가 중요하다고 지정한 논문과 유사한 신규 논문”**을 자동 탐색하는 2단계 파이프라인으로 확장할 수 있습니다. [Semantic Scholar](https://api.semanticscholar.org/api-docs/recommendations?utm_source=chatgpt.com)

---

## 1. 연구 프로젝트 디렉터리 구성

예를 들어 현재 연구 주제가 AI Agent Security와 CTI-KG라면 다음처럼 구성하면 관리하기 편합니다.

```
research-agent/
│
├── config/
│   ├── keywords.yaml
│   ├── journals.yaml
│   └── prompt.md
│
├── skills/
│   └── paper-research/
│       └── SKILL.md
│
├── scripts/
│   ├── collect.py
│   ├── deduplicate.py
│   └── update_index.py
│
├── data/
│   ├── papers.json
│   └── seen_ids.json
│
├── papers/
│   ├── 2026/
│   │   ├── 2026-09-07-paper1.md
│   │   └── ...
│
├── reports/
│   ├── daily/
│   └── weekly/
│
└── README.md
```

Hermes Cron에 `--workdir`를 지정하면 이 디렉터리를 기준으로 파일 읽기·쓰기 및 코드 실행을 수행할 수 있습니다. Hermes 문서에서도 Cron 작업에 `workdir`를 지정하면 해당 디렉터리의 프로젝트 지침과 파일 도구가 그 경로를 기준으로 작동한다고 설명합니다. [GitHub](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md?utm_source=chatgpt.com)

---

## 2. 키워드는 단순 문자열보다 “연구 개념”으로 관리

`keywords.yaml`을 다음처럼 만들어 두는 것이 좋습니다.

```
research_topic:
  name: "CTI-KG for AI Agent Security"

primary:
  - "AI agent security"
  - "autonomous agent security"
  - "LLM agent security"
  - "agentic AI security"

cti:
  - "cyber threat intelligence"
  - "CTI"
  - "threat intelligence"

knowledge_graph:
  - "knowledge graph"
  - "security knowledge graph"
  - "CTI knowledge graph"
  - "threat knowledge graph"

behavior:
  - "agent behavior"
  - "tool misuse"
  - "spec gaming"
  - "reward hacking"
  - "unsafe tool use"

detection:
  - "threat detection"
  - "attack detection"
  - "behavior detection"
  - "anomaly detection"

exclude:
  - "robot navigation"
  - "medical agent"
```

그리고 검색식을 자동으로 생성합니다.

```
("AI agent security" OR "LLM agent security")
AND
("cyber threat intelligence" OR "knowledge graph")
```

검색식을 하나만 만들지 말고 5~10개 정도의 **검색 Query Set**으로 분산시키는 것이 좋습니다.

예:

```
Q1: "LLM agent" AND "cybersecurity"
Q2: "AI agent" AND "knowledge graph" AND security
Q3: "cyber threat intelligence" AND "knowledge graph"
Q4: "agentic AI" AND threat detection
Q5: "LLM agent" AND "spec gaming"
Q6: "AI agent" AND "tool misuse"
Q7: "autonomous agent" AND attack detection
```

이렇게 해야 특정 용어를 사용하지 않은 관련 연구까지 놓치지 않습니다.

---

## 3. 수집 단계에서는 LLM을 사용하지 않는 것이 좋습니다

여기가 중요한 설계 포인트입니다.

매일 Cron이 실행될 때 처음부터 Hermes에게

> 인터넷에서 논문을 찾아줘.

라고 하는 것보다, Python/API가 먼저 논문 metadata를 가져오게 하는 것이 안정적입니다.

```
Cron
 ↓
collect.py
 ↓
OpenAlex / Semantic Scholar / arXiv
 ↓
papers_raw.json
```

예:

```
{
  "title": "CTI-based Knowledge Graph for ...",
  "authors": ["A", "B"],
  "year": 2026,
  "doi": "10.xxxx/xxx",
  "arxiv_id": "2609.xxxxx",
  "abstract": "...",
  "source": "OpenAlex",
  "url": "...",
  "collected_at": "2026-09-07"
}
```

그 다음에만 Hermes/LLM을 호출합니다.

이렇게 분리하면 검색 결과가 100개인 날에도 **100개 모두를 LLM에 넣는 낭비**를 피할 수 있습니다.

---

## 4. 중복 제거는 반드시 LLM 이전에 수행

동일 논문이 OpenAlex, Semantic Scholar, arXiv 세 곳에 동시에 존재할 수 있습니다.

따라서 순서를

```
수집
 ↓
중복 제거
 ↓
관련성 평가
 ↓
LLM 분석
```

으로 해야 합니다.

중복 판정 우선순위는 다음 정도면 충분합니다.

```
1순위 DOI
2순위 arXiv ID
3순위 Semantic Scholar Paper ID
4순위 normalized title
```

예:

```
paper_key = (
    doi
    or arxiv_id
    or semantic_scholar_id
    or normalized_title
)
```

그리고

```
data/seen_ids.json
```

또는 SQLite에 저장합니다.

개인적으로는 논문이 수백 편을 넘어가면 JSON보다 SQLite를 추천합니다.

```
papers.db

papers
 ├─ id
 ├─ doi
 ├─ title
 ├─ abstract
 ├─ published_date
 ├─ relevance_score
 ├─ summary
 ├─ collected_at
 └─ status
```

---

## 5. Hermes가 담당할 핵심은 “관련성 판단”

검색된 논문을 LLM에게 바로 요약시키지 말고 먼저 점수를 매기게 합니다.

예를 들어:

```
0 = 연구와 무관
1 = 약간 관련
2 = 관련
3 = 매우 관련
4 = 핵심 선행연구
5 = 반드시 검토해야 할 논문
```

Hermes Prompt:

```
우리의 연구 주제는 다음과 같다.

"CTI Knowledge Graph를 활용하여
AI Agent의 행동 연쇄를 탐지하고
위험한 Tool 실행을 조기에 차단하는 방법"

아래 논문의 제목과 초록을 평가하라.

평가기준:

1. AI Agent와 직접 관련성이 있는가?
2. Cybersecurity와 관련있는가?
3. CTI 또는 Knowledge Graph와 관련있는가?
4. Agent 행동 탐지 또는 Tool 실행 통제와 관련있는가?
5. 우리 연구의 baseline 또는 비교대상이 될 수 있는가?

0~5점으로 relevance_score를 부여한다.

JSON으로 반환:

{
 "score": 0-5,
 "reason": "...",
 "tags": [],
 "research_role": ""
}
```

그리고 예를 들어

```
score >= 3
```

인 논문만 본격 분석합니다.

이 한 단계만 넣어도 자동화 품질이 크게 올라갑니다.

---

## 6. 논문별 요약은 “요약”보다 연구 분석 형태로 저장

단순하게

```
이 논문은 XXX를 연구하였다.
```

만 저장하면 나중에 논문 작성 때 활용도가 낮습니다.

대신 다음 형식을 권합니다.

```
# Paper Title

## Metadata

- Authors:
- Year:
- Venue:
- DOI:
- URL:
- Citation:
- Relevance Score: 4/5

## 한 줄 요약

...

## 연구 문제

...

## 핵심 아이디어

...

## 방법론

...

## 데이터셋 / 실험환경

...

## 주요 결과

...

## 강점

...

## 한계

...

## 우리 연구와의 관계

...

## 우리 연구와의 차이

...

## Baseline 활용 가능성

...

## Research Gap

...

## 인용할 만한 주장

...

## Tags

#CTI
#KnowledgeGraph
#AIAgentSecurity
#AgentBehavior
```

이 포맷은 이후 박사논문의 **Related Work 작성 자동화**에도 그대로 활용할 수 있습니다.

---

## 7. 논문 파일 저장

예를 들어:

```
papers/
└── 2026/
    └── 09/
        ├── park-2026-cti-knowledge-graph.md
        ├── kim-2026-agent-security.md
        └── smith-2026-llm-tool-misuse.md
```

그리고 별도의 index:

```
# Paper Index

| Date | Paper | Score | Category |
|---|---|---:|---|
| 2026-09-07 | CTI Knowledge Graph... | 5 | CTI-KG |
| 2026-09-07 | Agent Tool Security... | 4 | Agent Security |
```

를 자동 업데이트하도록 합니다.

---

## 8. 가장 중요한 기능: 주간 Research Synthesis

개별 논문 요약보다 이것이 박사논문 연구에는 더 가치가 있습니다.

매일 수집한 논문을 일요일 밤 Hermes가 다시 읽어서:

```
이번 주 논문 17편
        ↓
Theme clustering
        ↓
연구 동향
        ↓
주요 방법
        ↓
공통 한계
        ↓
Research Gap
        ↓
내 연구에 미치는 영향
```

을 분석하도록 합니다.

결과:

```
# Weekly Research Brief
2026-09-01 ~ 2026-09-07

## 이번 주 신규 논문
17편

## 중요 논문
5편

## 연구 동향

### 1. Agent behavior monitoring
...

### 2. CTI grounding
...

### 3. Knowledge Graph reasoning
...

## 기존 연구에서 반복적으로 나타나는 한계

1. 대부분 static CTI 사용
2. Agent 행동 연쇄를 고려하지 않음
3. Tool execution 이전 조기탐지가 부족
4. Text-RAG와 KG 비교 실험 부족

## 새롭게 보이는 Research Gap

...

## 현재 박사논문 가설에 미치는 영향

...

## 반드시 읽어야 할 논문 TOP 5

...

## 다음 주 추적 키워드

...
```

이 단계부터 단순 **논문 자동수집 시스템**이 아니라 **Research Intelligence System**이 됩니다.

---

# Hermes Cron 구성

Hermes는 자연어 일정과 표준 Cron 표현식을 모두 지원합니다. Cron 작업은 gateway가 주기적으로 확인하여 실행하고, 매 실행 시 fresh Agent session을 생성합니다. 따라서 “지난번 대화를 기억하겠지”라고 가정하면 안 되고, 파일이나 DB를 상태 저장소로 사용해야 합니다. [GitHub](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md?utm_source=chatgpt.com)

예를 들어 매일 오전 7시:

```
hermes cron create "every day at 7am" \
  "Run the research paper collection pipeline.
   Collect newly published papers matching config/keywords.yaml.
   Deduplicate against data/papers.db.
   Evaluate relevance.
   Analyze papers with relevance >= 3.
   Save the results under papers/.
   Update the research index." \
  --workdir /home/user/research-agent \
  --name "Daily Paper Research"
```

매주 일요일:

```
hermes cron create "every sunday 9pm" \
  "Review all papers collected during the last 7 days.
   Produce a weekly research synthesis.
   Identify important papers, emerging themes,
   methodological trends, research gaps,
   potential baselines and implications for our research.
   Save the report under reports/weekly/." \
  --workdir /home/user/research-agent \
  --name "Weekly Research Synthesis"
```

Hermes는 Skill을 Cron 작업에 붙이는 것도 지원하기 때문에, 장기적으로는 긴 Prompt를 매번 Cron에 넣기보다는 `paper-research` 같은 Skill로 만드는 것이 더 깔끔합니다. [GitHub](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md?utm_source=chatgpt.com)

예:

```
hermes cron create "every day at 7am" \
  "Collect and analyze newly published papers." \
  --skill paper-research \
  --workdir /home/user/research-agent
```

---

# 추천 Skill 구성

```
skills/paper-research/SKILL.md
```

안에 다음을 고정합니다.

```
# Paper Research Skill

## Objective

Continuously discover and analyze academic literature
related to the configured research topic.

## Workflow

1. Read config/keywords.yaml
2. Run scripts/collect.py
3. Load newly discovered papers
4. Remove duplicates
5. Score relevance from 0-5
6. Ignore papers below 3
7. Analyze remaining papers
8. Save Markdown
9. Update papers.db
10. Update research index

## Analysis format

- One-line summary
- Research question
- Method
- Dataset
- Results
- Strength
- Limitation
- Relationship with our work
- Research gap
- Potential baseline
- Tags

## Rules

Never overwrite existing paper notes.

Use DOI as primary unique identifier.

Separate facts stated by the paper from your interpretation.

Do not claim full-paper findings when only the abstract
was available.

Mark evidence_source as one of:

- title
- abstract
- fulltext
```

특히 마지막 세 줄이 중요합니다.

**초록만 읽어 놓고 LLM이 논문 전체 방법론·실험 결과를 추측하는 문제를 막아야 합니다.**

---

# 최종적으로는 3개 Cron으로 나누는 것을 추천합니다

```
┌─────────────────────────────────────┐
│       Hermes Research Pipeline      │
└─────────────────────────────────────┘

① Daily Discovery
매일 07:00

OpenAlex
Semantic Scholar
arXiv
    ↓
신규 논문
    ↓
Dedup
    ↓
Relevance
    ↓
Markdown + DB


② Weekly Synthesis
일요일 21:00

지난 7일 논문
    ↓
Theme clustering
    ↓
Research trends
    ↓
Research gaps
    ↓
Weekly report


③ Monthly Thesis Review
매월 1일

지난 30일 연구
       +
기존 논문 DB
       ↓
박사논문 Research Question
       ↓
가설 변화
       ↓
Baseline 변화
       ↓
연구공백 변화
       ↓
"논문 전략 업데이트"
```

이 **③ Monthly Thesis Review**까지 넣으면 꽤 강력합니다.

---

## 제가 권하는 최종 구조

단순히

> `Hermes → 검색 → 요약`

으로 만들기보다는,

```
                 Hermes
                   │
             Cron Scheduler
                   │
        ┌──────────┴──────────┐
        │                     │
     Python/API             LLM
        │                     │
논문 검색·중복제거       의미 판단·분석
        │                     │
        └──────────┬──────────┘
                   ▼
                SQLite
                   +
               Markdown
                   │
          ┌────────┴────────┐
          ▼                 ▼
     Daily Papers      Weekly Synthesis
                            │
                            ▼
                     Research Gap DB
                            │
                            ▼
                    박사논문 연구전략
```

가 가장 좋습니다.

**Python/API는 “정확하고 반복적인 일”을 담당하고, Hermes LLM은 “읽고 판단하고 연결하는 일”을 담당**하게 만드는 것입니다. 검색·중복 제거까지 전부 Agent에게 맡기는 것보다 훨씬 재현 가능하고 비용도 낮습니다.

또 Semantic Scholar에는 기존 논문을 기반으로 관련 논문을 추천하는 API가 있으므로, 나중에는 `키워드 검색 → 핵심논문 선정 → 핵심논문 기반 추천 → citation/reference graph 추적`의 **4단계 Literature Discovery**로 발전시키는 것이 좋습니다. [Semantic Scholar](https://api.semanticscholar.org/api-docs/recommendations?utm_source=chatgpt.com)

현재 진행 중인 **CTI-KG / AI Agent Security / spec-gaming 연구**라면, 이 구조에서 단순 `관련/비관련`이 아니라 **① CTI, ② KG, ③ Agent Security, ④ Behavior Detection, ⑤ Spec-gaming, ⑥ Tool Security, ⑦ Baseline 후보, ⑧ Research Gap**의 8개 축으로 자동 태깅하게 만드는 것이 특히 유용합니다.