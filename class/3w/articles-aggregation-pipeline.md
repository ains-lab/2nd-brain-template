네. 이 경우에는 기존의 **“논문 DB를 구축하고 DB를 검색하는 구조”**보다, **LLM Wiki를 연구 지식의 중심 저장소로 두는 구조**가 더 적합합니다.

LLM Wiki의 핵심은 새 논문이 들어올 때마다 단순히 논문 요약 파일 하나를 추가하는 것이 아니라, **기존 Wiki의 개념·주제·비교·Research Gap 페이지까지 함께 갱신하는 것**입니다. 공식적인 LLM Wiki 패턴도 raw source → wiki → schema의 계층을 두고, 새 source가 들어오면 관련 페이지를 업데이트하고 서로 연결하면서 지식을 증분적으로 유지하는 방식을 지향합니다. [GitHub](https://github.com/microsoft/llmwiki/blob/main/README.md?utm_source=chatgpt.com)

## 전체 목표 구조

제가 추천하는 최종 구조는 다음입니다.

```
                    Hermes Agent
                         │
                  Cron Scheduler
                         │
                         ▼
                ① 논문 자동 발견
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
     OpenAlex      Semantic Scholar      arXiv
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                 신규 후보 논문
                         │
                         ▼
                ② 관련성 1차 평가
                         │
                relevance >= 기준
                         │
                         ▼
               ③ Raw Source 저장
                         │
                         ▼
                  LLM Wiki Ingest
                         │
              ┌──────────┼───────────┐
              ▼          ▼           ▼
          논문 페이지   개념 페이지   주제 페이지
              │          │           │
              └──────────┼───────────┘
                         ▼
                 기존 Wiki 재구성
                         │
              새 주장 / 관계 / 충돌
                         │
                         ▼
              ④ Cross-paper Synthesis
                         │
         ┌───────────────┼────────────────┐
         ▼               ▼                ▼
      비교표          Research Gap       Trend
         │               │                │
         └───────────────┼────────────────┘
                         ▼
               ⑤ Research Idea Engine
                         │
                기존 지식 + 신규 논문
                         │
                         ▼
                  새로운 연구 아이디어
                         │
                  가설 / RQ / 실험설계
```

즉, **DB 대신 Markdown Wiki 자체가 지식 저장소**가 됩니다.

---

# 1. 가장 중요한 변화: Paper 중심이 아니라 Knowledge 중심

기존 방식은 보통 다음과 같습니다.

```
Paper A → Summary A
Paper B → Summary B
Paper C → Summary C
```

100편을 수집하면 100개의 요약이 생깁니다.

문제는 이것만으로는 지식이 서로 연결되지 않는다는 점입니다.

LLM Wiki 방식은 다음과 같습니다.

```
Paper A ──┐
Paper B ──┼──→ [[AI Agent Security]]
Paper C ──┘              │
                         ├── [[Tool Misuse]]
                         ├── [[Behavior Monitoring]]
                         ├── [[CTI Grounding]]
                         └── [[Knowledge Graph Reasoning]]
```

그리고 새 논문 Paper D가 들어오면:

```
Paper D
   │
   ├─ 기존 주장 보강
   ├─ 기존 주장 반박
   ├─ 새로운 방법 추가
   ├─ 기존 연구 한계 수정
   └─ 새로운 Research Gap 생성
```

이 되는 구조입니다.

Microsoft의 `llmwiki` 프로젝트도 이를 **LLM이 지속적으로 관리하는 personal knowledge base**로 설명하며, 새로운 source를 추가할 때 기존 entity/topic 페이지를 수정하고 contradiction과 cross-reference까지 갱신하는 방식을 채택하고 있습니다. [GitHub](https://github.com/microsoft/llmwiki/blob/main/README.md?utm_source=chatgpt.com)

---

# 2. DB 없는 디렉터리 구조

예를 들어 연구 프로젝트를 다음과 같이 구성합니다.

```
research-wiki/
│
├── .hermes.md
│
├── schema.md
│
├── index.md
│
│
├── config/
│   ├── keywords.yaml
│   ├── research-question.md
│   └── collection-policy.md
│
├── raw/
│   └── papers/
│       ├── 2026/
│       │   ├── paper-a.pdf
│       │   ├── paper-a.md
│       │   ├── paper-b.pdf
│       │   └── paper-b.md
│
├── wiki/
│
│   ├── papers/
│   │   ├── paper-a.md
│   │   ├── paper-b.md
│   │   └── paper-c.md
│   │
│   ├── concepts/
│   │   ├── ai-agent-security.md
│   │   ├── cti-grounding.md
│   │   ├── knowledge-graph.md
│   │   ├── behavior-chain.md
│   │   ├── spec-gaming.md
│   │   └── tool-misuse.md
│   │
│   ├── topics/
│   │   ├── agent-threat-detection.md
│   │   ├── cti-kg-agent-security.md
│   │   ├── runtime-monitoring.md
│   │   └── agent-guardrails.md
│   │
│   ├── methods/
│   │   ├── behavior-only-detection.md
│   │   ├── text-rag.md
│   │   ├── graph-reasoning.md
│   │   └── runtime-policy.md
│   │
│   ├── comparisons/
│   │   ├── cti-kg-vs-rag.md
│   │   └── behavior-vs-context-aware.md
│   │
│   ├── gaps/
│   │   ├── research-gaps.md
│   │   └── unresolved-questions.md
│   │
│   └── ideas/
│       ├── idea-001.md
│       ├── idea-002.md
│       └── idea-003.md
│
├── synthesis/
│   ├── weekly/
│   └── monthly/
│
└── logs/
    └── ingest-log.md
```

여기서 별도의 PostgreSQL, MySQL, SQLite DB를 연구 데이터의 원본으로 둘 필요가 없습니다.

**Markdown이 Source of Truth**입니다.

일부 LLM Wiki 구현은 검색 속도를 위해 내부적으로 SQLite 같은 파생 index를 사용할 수 있지만, 이는 언제든 Markdown으로부터 다시 만들 수 있는 cache일 뿐입니다. 실제 LLM Wiki 문서도 이 구조를 명확히 설명합니다. [LLM Wiki](https://llmwiki.cc/docs?utm_source=chatgpt.com)

---

# 3. Raw Source와 Wiki를 반드시 분리

이 설계에서 아주 중요한 원칙입니다.

```
raw/
```

는 **원본 증거 저장소**입니다.

```
wiki/
```

는 **LLM이 해석하고 정리한 지식 저장소**입니다.

예:

```
raw/papers/2026/paper123.md
```

에는:

```
Title
Authors
DOI
Abstract
Full Text
Source URL
Collected Date
```

등 원문 정보를 보존합니다.

반면:

```
wiki/papers/paper123.md
```

에는:

```
# Paper Title

## 핵심 주장

...

## 방법

...

## 주요 결과

...

## 한계

...

## 관련 개념

- [[CTI Grounding]]
- [[AI Agent Security]]
- [[Knowledge Graph Reasoning]]

## 관련 연구

- [[Paper A]]
- [[Paper B]]

## 기존 연구 대비 차이

...

## 우리 연구에 주는 의미

...

## Evidence

[[raw-paper-123]]
```

를 저장합니다.

즉,

> Raw = 증거  
> Wiki = 지식

입니다.

---

# 4. Hermes의 첫 번째 Cron — 논문 발견

Hermes Cron은 반복 작업과 Skill 연결을 지원하므로, 논문 수집 Agent를 매일 실행하면 됩니다. Cron job은 실행될 때 fresh agent session을 사용하므로 장기 상태는 대화 기억이 아니라 **workdir의 Wiki 파일**에 남기는 것이 중요합니다. [GitHub](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md?utm_source=chatgpt.com)

예:

```
매일 오전 07:00

Paper Discovery Agent
```

역할:

```
OpenAlex
Semantic Scholar
arXiv
 ↓
신규 논문 검색
 ↓
기존 raw/ 확인
 ↓
신규 논문만 처리
```

검색 키워드는:

```
ai_agent:
  - AI agent security
  - LLM agent security
  - agentic AI security

cti:
  - cyber threat intelligence
  - CTI grounding

kg:
  - knowledge graph
  - security knowledge graph
  - CTI knowledge graph

behavior:
  - agent behavior
  - tool misuse
  - spec gaming
  - reward hacking
```

형태로 유지합니다.

---

# 5. 중복 검사도 DB 없이 처리

중복 제거 역시 DB가 필수는 아닙니다.

Raw Markdown의 frontmatter를 이용합니다.

예:

```
---
title: "..."
doi: "10.xxxx/xxxx"
arxiv: "2609.12345"
semantic_scholar_id: "..."
collected: 2026-09-08
---
```

새 논문을 발견하면 Hermes 또는 수집 Script가:

```
raw/
```

에서 DOI 또는 arXiv ID를 검색합니다.

판정 순서는:

```
DOI
 ↓
arXiv ID
 ↓
Semantic Scholar ID
 ↓
normalized title
```

이면 충분합니다.

따라서:

```
DB query
```

대신:

```
Markdown metadata search
```

를 사용하는 것입니다.

논문이 수천~수만 편까지 늘어나면 BM25나 local index를 **검색 가속용**으로 추가할 수 있지만, 여전히 Wiki가 원본입니다.

---

# 6. 관련성 판단 후에만 Wiki로 Ingest

수집된 모든 논문을 Wiki에 넣으면 금방 오염됩니다.

그래서:

```
검색
 ↓
관련성 평가
 ↓
중요 논문만 Wiki ingest
```

해야 합니다.

예:

```
0 = 무관
1 = 약간 관련
2 = 간접 관련
3 = 관련
4 = 매우 중요
5 = 핵심 선행연구
```

그리고:

```
score >= 3
```

인 논문만 Wiki에 반영합니다.

---

# 7. 핵심 단계 — Ingest가 단순 “추가”가 아니어야 함

여기가 LLM Wiki 방식의 핵심입니다.

새 논문:

```
Paper X
```

가 들어오면 Hermes에게:

```
Paper X를 요약하고 저장해라.
```

라고 하면 안 됩니다.

대신:

```
Paper X를 읽어라.

기존 Wiki에서 관련 개념, 연구, 방법,
주장, Research Gap을 찾는다.

새 논문의 지식을 기존 Wiki와 비교한다.

필요하면:

- 기존 페이지 수정
- 새로운 개념 페이지 생성
- 관련 페이지 간 wikilink 추가
- 기존 주장 강화
- 기존 주장 약화
- contradiction 기록
- research gap 갱신

을 수행한다.
```

라고 해야 합니다.

LLM Wiki 문서가 이것을 **append가 아니라 refactor pass**로 설명하는 이유가 바로 이것입니다. 새 source 하나가 들어올 때 Wiki 전체 중 관련 영역이 다시 구조화됩니다. [LLM Wiki](https://llmwiki.cc/docs?utm_source=chatgpt.com)

---

# 8. 예를 들어 신규 논문 한 편이 들어오면

기존 Wiki:

```
[[AI Agent Security]]
     │
     ├── [[Behavior Monitoring]]
     └── [[Tool Misuse]]
```

새 논문:

```
CTI-based temporal behavior graph for LLM agents
```

가 들어왔다고 가정하면,

자동으로:

```
[[AI Agent Security]]
     │
     ├── [[Behavior Monitoring]]
     │        │
     │        └── [[Temporal Behavior Chain]]
     │
     ├── [[CTI Grounding]]
     │
     └── [[Knowledge Graph Reasoning]]
```

가 생성됩니다.

그리고 기존:

```
wiki/topics/agent-threat-detection.md
```

도 수정됩니다.

예:

```
## 주요 탐지 접근

### Behavior-only

Paper A, B에서 사용.

한계:
행동 발생 이후 판단하는 경우가 많음.

### Text-RAG

Paper C에서 사용.

장점:
외부 CTI grounding 가능.

한계:
관계 구조와 시간 구조 표현에 제한.

### CTI-KG

Paper D, E에서 사용.

새로운 연구에서 temporal path reasoning을
Agent runtime monitoring에 적용하기 시작함.
```

이게 바로 **지식 증분**입니다.

---

# 9. Wiki Link가 곧 Knowledge Graph 역할

별도 Neo4j도 처음에는 필요하지 않습니다.

```
[[CTI]]
[[MITRE ATT&CK]]
[[Tool Misuse]]
[[Behavior Chain]]
[[Agent Runtime Monitoring]]
```

이 연결 자체가 lightweight Knowledge Graph가 됩니다.

예:

```
[[Spec Gaming]]
      │
      ├─ related → [[Tool Misuse]]
      │
      ├─ detected-by → [[Behavior Monitoring]]
      │
      └─ mitigated-by → [[Runtime Policy]]
```

Markdown 링크를 기반으로 Obsidian 같은 툴에서도 그래프를 바로 볼 수 있습니다.

---

# 10. Paper Page보다 Topic Page가 더 중요

논문 300편이 쌓였다고 가정해보겠습니다.

낮은 수준의 시스템:

```
300 Paper summaries
```

좋은 LLM Wiki:

```
300 papers
   ↓
80 concepts
   ↓
30 research topics
   ↓
15 comparison pages
   ↓
10 recurring limitations
   ↓
7 research gaps
   ↓
5 strong research ideas
```

입니다.

LLM Wiki 관련 구현들 역시 단순 문서 저장이 아니라, source가 기존 페이지에 cross-reference되고 시간이 지나면서 synthesis가 강화되는 것을 “compounding knowledge”의 핵심으로 설명합니다. [GitHub](https://github.com/Labhund/llm-wiki?utm_source=chatgpt.com)

---

# 11. 두 번째 Cron — Daily Wiki Refactoring

논문 수집 후 별도 Cron을 두는 것도 좋습니다.

예:

```
매일 08:00
```

작업:

```
오늘 ingest한 논문을 확인한다.

관련 Wiki 페이지를 찾는다.

다음을 수행한다:

1. 새로운 claim 추가
2. 기존 claim 보강
3. contradiction 탐지
4. 새로운 wikilink 추가
5. topic page 업데이트
6. method page 업데이트
7. research gap 업데이트
```

결과는:

```
Paper
 ↓
Knowledge
 ↓
Relationship
```

으로 올라갑니다.

---

# 12. 세 번째 Cron — Weekly Synthesis

매주:

```
일요일 21:00
```

지난 일주일 동안 변경된 Wiki를 읽습니다.

단순히:

```
이번 주 논문 10편
```

을 요약하지 않습니다.

대신:

```
어떤 지식이 바뀌었는가?
```

를 분석합니다.

예:

```
# Weekly Knowledge Synthesis

## 새롭게 강화된 주장

CTI grounding이 Agent runtime detection에
활용될 가능성을 보여주는 논문이 3편 추가됨.

## 약해진 주장

Behavior-only detector가 가장 효과적이라는
기존 가정과 상충하는 연구 2편 발견.

## Emerging Topic

Temporal CTI reasoning

## 반복되는 한계

기존 연구 대부분이 static CTI 사용.

## 새로운 Research Gap

Agent 행동연쇄와
temporal CTI-KG를 결합한
pre-action detection 실험이 부족함.
```

---

# 13. 네 번째 Cron — Research Gap Miner

이 자동화를 별도로 두는 것을 추천합니다.

예:

```
매주 월요일 06:00
```

다음 Wiki 페이지들을 읽습니다.

```
wiki/topics/
wiki/methods/
wiki/comparisons/
wiki/gaps/
```

그리고 다음 질문을 반복합니다.

```
1. 여러 논문에서 반복되는 한계는 무엇인가?

2. 서로 모순되는 결과는 무엇인가?

3. 아직 직접 비교되지 않은 방법은 무엇인가?

4. 아직 결합되지 않은 두 기술은 무엇인가?

5. 평가 데이터가 부족한 가설은 무엇인가?

6. 특정 환경에서만 검증된 주장은 무엇인가?

7. 시간적 인과관계가 검증되지 않은 연구는?

8. 새로운 benchmark가 필요한 영역은?
```

그리고:

```
wiki/gaps/research-gaps.md
```

를 업데이트합니다.

---

# 14. 다섯 번째 Cron — Research Idea Generator

그리고 이것이 최종 목적입니다.

예:

```
매월 1일
```

Hermes에게 논문 자체를 전부 읽게 하지 않습니다.

이미 축적된:

```
Concepts
Topics
Methods
Comparisons
Contradictions
Research Gaps
```

를 읽게 합니다.

입력:

```
                         기존 Wiki
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
           Concepts       Methods       Findings
              │             │             │
              └─────────────┼─────────────┘
                            ▼
                       Research Gaps
                            │
                            ▼
                     Idea Generation
```

출력은 단순 제목이 아니라:

```
# Research Idea 017

## 아이디어

Temporal CTI-KG 기반
AI Agent 행동연쇄 사전 탐지

## 근거

[[CTI Grounding]]
[[Temporal Reasoning]]
[[Behavior Monitoring]]

## 관찰된 Research Gap

기존 CTI 기반 연구들은 대부분
Agent action 이후 탐지에 집중.

[[Research Gap - Pre-action Detection]]

## Research Question

시간 유효성을 갖는 CTI-KG path reasoning이
behavior-only detector보다
금지 행동을 더 일찍 탐지할 수 있는가?

## Hypothesis

...

## Baselines

[[Behavior-only Detection]]
[[Text-RAG]]
[[Static KG]]

## Experimental Design

...

## Novelty Risk

Medium

## Supporting Papers

[[Paper A]]
[[Paper C]]
[[Paper H]]

## Contradicting Papers

[[Paper D]]
```

처럼 만들어야 합니다.

---

# 15. “아이디어도 Wiki에 저장”하는 것이 중요

아이디어를 보고 끝내면 복리가 끊깁니다.

그래서:

```
wiki/ideas/
```

에 저장합니다.

예:

```
idea-001
idea-002
idea-003
```

그리고 이후 새로운 논문이 들어올 때도 해당 아이디어를 비교합니다.

```
새 Paper
   ↓
Idea-001과 관련?
   ↓
YES
   ↓
근거 강화 / 약화
   ↓
Idea-001 업데이트
```

예:

```
## Evidence Status

2026-08
초기 근거: 3편

2026-09
관련 논문 4편 추가
→ 가설 근거 강화

2026-10
반대 결과 논문 2편
→ novelty 유지
→ effectiveness hypothesis 약화
```

즉 **연구 아이디어 자체가 살아 있는 Wiki object**가 됩니다.

---

# 16. 그러면 진짜 “복리”가 발생

1개월 후:

```
50 papers
 → 20 concepts
 → 8 gaps
 → 3 ideas
```

3개월 후:

```
150 papers
 → 45 concepts
 → 25 topic synthesis
 → 18 comparisons
 → 15 gaps
 → 10 ideas
```

6개월 후:

```
300 papers
      ↓
연구 분야 구조화
      ↓
상충되는 증거 축적
      ↓
Research Gap 정교화
      ↓
가설 변화
      ↓
Idea 평가
      ↓
새로운 Paper 추가
      ↓
다시 Wiki 강화
```

가 됩니다.

이를 제가 표현하면:

```
Paper
  ↓
Information
  ↓
Knowledge
  ↓
Relationship
  ↓
Synthesis
  ↓
Research Gap
  ↓
Hypothesis
  ↓
Research Idea
  ↓
새 논문
  ↺
```

입니다.

단순 RAG와 가장 큰 차이가 여기 있습니다. RAG는 질문할 때 raw corpus를 다시 검색하지만, LLM Wiki는 이전 synthesis 결과를 **지속되는 artifact로 남겨 다음 추론의 입력으로 다시 활용**합니다. [LLM Wiki](https://llmwiki.cc/docs?utm_source=chatgpt.com)

---

# 17. Hermes에는 5개 Skill을 두는 것을 추천

```
skills/

paper-discovery/
    SKILL.md

paper-ingest/
    SKILL.md

wiki-refactor/
    SKILL.md

research-gap-miner/
    SKILL.md

research-idea-generator/
    SKILL.md
```

역할은:

```
paper-discovery
       ↓
논문을 찾음

paper-ingest
       ↓
논문의 지식을 추출

wiki-refactor
       ↓
기존 Wiki와 연결/수정

research-gap-miner
       ↓
지식 공백 탐색

research-idea-generator
       ↓
새 연구 가설 생성
```

으로 나눕니다.

Hermes Cron은 Skill을 attached workflow로 실행할 수 있기 때문에 이런 분리가 잘 맞습니다. [GitHub](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/cron.md?utm_source=chatgpt.com)

---

# 18. 권장 자동화 일정

최종적으로 다음 정도가 좋습니다.


| 자동화              | 주기       | 목적              |
| ---------------- | -------- | --------------- |
| Paper Discovery  | 매일 07:00 | 신규 논문 발견        |
| Paper Ingest     | 매일 07:30 | 관련 논문 지식화       |
| Wiki Refactor    | 매일 08:00 | 기존 지식과 연결       |
| Weekly Synthesis | 일요일      | 한 주간 지식 변화 정리   |
| Gap Mining       | 매주 월요일   | Research Gap 갱신 |
| Idea Generation  | 매월       | 새로운 연구 아이디어 생성  |


여기에서 중요한 것은 **Idea Generation을 매일 돌리지 않는 것**입니다.

논문 한두 편마다 아이디어를 뽑으면 잡음이 많아집니다.

```
Daily = Evidence

Weekly = Knowledge

Monthly = Idea
```

로 역할을 나누는 것이 좋습니다.

---

# 19. Research Idea 생성에 “Novelty Ledger” 추가 권장

박사논문 목적이라면 한 단계 더 추가하겠습니다.

```
wiki/ideas/
    └── idea-017.md
```

안에:

```
## Novelty Ledger

### Known Similar Work

- [[Paper A]]
- [[Paper B]]

### What already exists

CTI-KG 기반 공격 탐지

### What appears missing

CTI-KG를 Agent action 이전
pre-action decision에 적용

### Potential novelty

Temporal attack-path reasoning
+
Agent tool decision

### Threat to novelty

새로운 논문 발견 시 반드시 재평가

### Novelty confidence

0.72
```

를 유지합니다.

새 논문이 발견될 때:

```
Novelty Ledger
      ↓
새 논문과 비교
      ↓
Novelty 유지?
      ├─ Yes → confidence ↑
      └─ No  → idea 수정/폐기
```

하도록 만듭니다.

이렇게 하면 Hermes가 그럴듯한 아이디어를 계속 만들어내는 것이 아니라 **문헌 근거로 아이디어를 살아 있게 관리**하게 됩니다.

---

# 20. 최종 추천 Hermes + LLM Wiki 아키텍처

전체를 하나로 합치면 다음 구조입니다.

```
                    HERMES
                       │
                 Cron Scheduler
                       │
                       ▼
              ┌─ Paper Discovery ─┐
              │                   │
           OpenAlex        Semantic Scholar
              │                   │
              └────── arXiv ──────┘
                       │
                       ▼
                 Relevance Filter
                       │
                       ▼
                 RAW SOURCES
            ┌─────────────────────┐
            │ immutable evidence  │
            └─────────────────────┘
                       │
                       ▼
                  LLM INGEST
                       │
                       ▼
              ┌── LLM WIKI ──┐
              │               │
            Papers         Concepts
              │               │
            Topics          Methods
              │               │
              └──────┬────────┘
                     ▼
                 Relations
                     │
                     ▼
                 Synthesis
                     │
          ┌──────────┼───────────┐
          ▼          ▼           ▼
      Comparisons  Trends  Contradictions
          │          │           │
          └──────────┼───────────┘
                     ▼
               RESEARCH GAPS
                     │
                     ▼
              IDEA GENERATOR
                     │
             ┌───────┼────────┐
             ▼       ▼        ▼
            RQ    Hypothesis  Method
             │       │        │
             └───────┼────────┘
                     ▼
               Novelty Ledger
                     │
                     ▼
                wiki/ideas/
                     │
                     │
       새로운 논문이 들어오면
                     │
                     └───────────↺
```

## 핵심 철학은 한 문장으로 정리할 수 있습니다.

**“논문을 저장하는 시스템이 아니라, 새 논문이 들어올 때마다 기존 연구 지식을 다시 편집하고 연결하며, 그 위에서 Research Gap과 연구 아이디어가 계속 진화하는 시스템”**으로 만드는 것입니다.

특히 현재 진행하시는 **CTI-KG + AI Agent Security + 행동연쇄 탐지/spec-gaming** 연구에는 이 방식이 잘 맞습니다. 예를 들어 `[[CTI Grounding]]`, `[[Temporal Reasoning]]`, `[[Behavior Chain]]`, `[[Spec Gaming]]`, `[[Tool Misuse]]`, `[[Runtime Monitoring]]` 등이 독립적인 Wiki concept으로 성장하다가, 시간이 지나면서 이들 사이에서 **“아직 실증적으로 검증되지 않은 조합”**을 자동으로 찾아내게 만들 수 있습니다.

다음 구현 단계에서는 이 구조를 기준으로 **실제로 Hermes에서 바로 사용할 수 있는** `research-wiki/` **디렉터리 전체 구조 +** `.[hermes.md](http://hermes.md)` **+ 5개** [`SKILL.md`](http://SKILL.md) **+ Cron 설정 + Wiki Markdown 템플릿**까지 만들어두면 바로 구축에 들어갈 수 있습니다.