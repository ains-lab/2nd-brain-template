검토 결과, **OMH에 ARS(Academic Research Skills)를 결합하는 것은 충분히 가치가 있습니다.** 다만 “ARS 스킬을 OMH 스킬 디렉터리에 그대로 복사”하는 방식보다는, **ARS를 논문 연구용 전문 workflow engine으로 유지하고 OMH가 상위 orchestration 계층을 맡는 구조**가 가장 안전합니다.

ARS는 현재 단순 스킬 몇 개가 아니라 `deep-research → academic-paper → integrity verification → reviewer → revision → final integrity → finalize → process summary`를 가진 10단계 파이프라인입니다. 각 단계마다 checkpoint와 handoff 계약이 있고, Stage 2.5와 4.5의 integrity gate는 건너뛸 수 없도록 설계되어 있습니다. [GitHub](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-pipeline/SKILL.md?utm_source=chatgpt.com)

## 1. 결론부터 보면

제가 권장하는 역할 분리는 다음과 같습니다.

```
사용자
   │
   ▼
Hermes Agent
   │
   ▼
┌──────────────────────────────┐
│ OMH                          │
│                              │
│ 상위 Orchestration           │
│ Model Routing                │
│ Parallel Execution           │
│ Long-term Memory             │
│ Tool / Sandbox               │
│ Cost / State / Verification  │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ ARS                          │
│ Academic Domain Engine       │
│                              │
│ Research                     │
│ Paper Writing                │
│ Integrity Check              │
│ Peer Review                  │
│ Revision                     │
│ Finalization                 │
└──────────────────────────────┘
```

즉,

**OMH = 연구 인프라 / 실행 관리자**

**ARS = 논문 연구 방법론 / 논문 작성 관리자**

로 나누는 것입니다.

이렇게 하면 두 시스템의 장점이 거의 겹치지 않고 상호보완적으로 작동합니다.

---

# 2. OMH와 ARS에서 실제로 겹치는 부분

완전히 충돌하지 않는 것은 아닙니다. 특히 아래 네 영역은 중복도가 높습니다.


| 영역                        | OMH                             | ARS                               | 충돌 위험 |
| ------------------------- | ------------------------------- | --------------------------------- | ----- |
| Research workflow         | `ulw-research`                  | `deep-research`                   | 🔴 높음 |
| Planning                  | `ulw-plan`                      | ARS Stage 1 / plan mode           | 🟠 중간 |
| Model routing             | Mixture-of-Models               | ARS Model Tiering                 | 🔴 높음 |
| Multi-agent orchestration | `ulw-work` / Maestro            | ARS 자체 39-agent 구조                | 🔴 높음 |
| QA/Verification           | `ulw-qa`, verification skills   | Integrity Stage 2.5/4.5           | 🟠 중간 |
| Memory                    | OMH Memory                      | Material Passport / state tracker | 🟡 낮음 |
| Writing                   | writing skill                   | `academic-paper`                  | 🟠 중간 |
| Review                    | quality/security/general review | academic reviewer agents          | 🟡 낮음 |


여기서 가장 조심해야 할 것은 **Research, Model Routing, Multi-Agent orchestration**입니다.

ARS 자체가 이미 꽤 강력한 orchestrator이기 때문입니다.

ARS `academic-pipeline`은 단순 호출기가 아니라 각 stage의 상태, 전달 artifact, checkpoint, retry, integrity failure 등을 직접 관리합니다. [GitHub](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-pipeline/SKILL.md?utm_source=chatgpt.com)

---

# 3. 특히 피해야 할 구조

다음처럼 만드는 것은 권장하지 않습니다.

```
OMH
 ↓
ulw-research
 ↓
ARS deep-research
 ↓
OMH research skill
 ↓
ARS research agent
 ↓
OMH ulw-work
 ↓
ARS multi-agent
```

이렇게 되면 **orchestrator 안에 orchestrator가 중첩**됩니다.

문제가 생길 수 있습니다.

```
누가 작업을 분할하는가?
OMH? ARS?

누가 모델을 선택하는가?
OMH routing? ARS model tiering?

누가 연구 완료를 결정하는가?
OMH verification? ARS integrity gate?

누가 State를 관리하는가?
OMH workflow state?
ARS Material Passport?
```

특히 ARS는 stage 간 handoff 정보를 엄격히 관리합니다.

예를 들어 Stage 1 → Stage 2에서는 단순 텍스트가 아니라:

```
RQ Brief
Methodology Blueprint
Bibliography
Synthesis
Material Passport
Provenance
```

등을 넘깁니다. [GitHub](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-pipeline/SKILL.md?utm_source=chatgpt.com)

OMH가 이것을 임의로 재구성하면 ARS의 provenance chain을 깨뜨릴 위험이 있습니다.

---

# 4. 반대로 궁합이 좋은 부분

가장 좋은 조합은 다음입니다.

```
ARS가 결정:
"무슨 연구 작업을 해야 하는가?"

OMH가 결정:
"그 작업을 어떤 모델과 어떤 실행 방식으로 수행할 것인가?"
```

이 구분만 유지하면 상당히 좋은 시스템이 됩니다.

---

# 5. ARS 단계별 OMH 적용 가능성

ARS의 실제 10단계 pipeline 기준으로 보겠습니다. [GitHub](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-pipeline/SKILL.md?utm_source=chatgpt.com)

## Stage 1 — RESEARCH

ARS:

```
deep-research
↓
RQ Brief
Methodology
Bibliography
Synthesis
```

### OMH 적용도: ★★★★★

여기가 OMH와 결합했을 때 가장 큰 효과가 예상되는 부분입니다.

예를 들어 ARS가 다음 연구 작업을 만든다고 합시다.

```
RQ1 관련 기존 연구 조사
RQ2 관련 CTI 연구 조사
Agent Security 연구 조사
Knowledge Graph 연구 조사
Evaluation Benchmark 조사
```

이를 OMH가:

```
                 ARS Stage 1
                       │
                       ▼
                  Research Plan
                       │
               OMH task splitter
          ┌────────────┼────────────┐
          ▼            ▼            ▼
     Research A    Research B   Research C
        │              │            │
      Model A        Model B      Model C
          └────────────┼────────────┘
                       ▼
                  ARS synthesis
```

처럼 처리할 수 있습니다.

OMH는 병렬 tool call과 delegated lane을 지원하고, 각 lane별 모델 및 reasoning effort를 지정할 수 있습니다. [GitHub](https://github.com/rlaope/oh-my-hermes)

### 중요한 원칙

다만 ARS `deep-research` 자체를 OMH `ulw-research`로 **교체하면 안 됩니다.**

더 좋은 구조는:

```
ARS deep-research
       │
       ├── research subtask
       ├── research subtask
       └── research subtask
                 │
                 ▼
          OMH execution
```

입니다.

즉 **ARS = Research methodology**

**OMH = Research execution**

입니다.

---

# 6. Stage 2 — WRITE

ARS:

```
academic-paper
↓
Paper Draft
```

### OMH 적용도: ★★★★☆

여기도 좋은 조합입니다.

ARS가 논문의 구조를 결정합니다.

```
Introduction
Related Work
Methodology
Experiment
Results
Discussion
Conclusion
```

OMH는 작성 작업에 적합한 모델을 선택할 수 있습니다.

예:

```
논문 구조/논리
      ↓
ultrabrain

Literature synthesis
      ↓
deep

Academic prose
      ↓
writing

Figure / diagram
      ↓
visual-engineering
```

OMH는 실제로 `ultrabrain`, `deep`, `quick`, `writing`, `visual-engineering` 등 task category에 모델과 reasoning effort를 연결합니다. [GitHub](https://github.com/rlaope/oh-my-hermes)

따라서 **한 모델이 논문 전체를 작성하는 것보다 효율적인 구조**를 만들 수 있습니다.

---

# 7. Stage 2.5 — INTEGRITY

ARS:

```
Integrity Verification
```

### OMH 적용도: ★★★☆☆

이 단계는 **ARS가 주도권을 유지해야 합니다.**

ARS Stage 2.5는 단순 QA가 아니라:

```
Reference verification
Data verification
Claim verification
Experiment provenance
AI research failure modes
Citation hallucination
```

등을 검사하는 mandatory gate입니다. [GitHub](https://github.com/imbad0202/academic-research-skills)

따라서:

```
OMH ulw-qa
```

가 이것을 대체해서는 안 됩니다.

대신:

```
ARS Integrity
       +
OMH Verification
```

으로 구성하는 것이 좋습니다.

예:

```
ARS
 ├ Citation integrity
 ├ Claim-support
 ├ Research provenance
 └ Experiment provenance

OMH
 ├ 파일 존재 확인
 ├ 코드 실행 확인
 ├ 결과 재현
 └ artifact verification
```

즉 서로 다른 층을 검증합니다.

---

# 8. Stage 3 — REVIEW

ARS:

```
Journal Fit Reviewer
Reviewer 1
Reviewer 2
Reviewer 3
Devil's Advocate
```

### OMH 적용도: ★★★★★

여기서 **OMH Multi-Model Routing**을 사용하면 매우 흥미롭습니다.

ARS 기본적으로 여러 reviewer 역할을 가지고 있습니다. [GitHub](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-pipeline/SKILL.md?utm_source=chatgpt.com)

이를:

```
Reviewer 1 → Claude 계열
Reviewer 2 → GPT 계열
Reviewer 3 → Gemini 계열
Devil Advocate → 다른 frontier model
```

처럼 실제 모델 다양성으로 확대할 수 있습니다.

이것은 상당히 좋은 조합입니다.

ARS도 cross-model verification과 model-tiering 기능을 이미 갖고 있기 때문에, 여기서는 **ARS model tiering을 끄고 OMH에 모델 선택권을 주거나**, 반대로 ARS에게 맡기는 한쪽 선택이 필요합니다. ARS는 `ARS_MODEL_TIERING`을 설정하지 않으면 agent들이 세션 모델을 그대로 상속합니다. [GitHub](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-pipeline/SKILL.md?utm_source=chatgpt.com)

저라면:

```
ARS_MODEL_TIERING = unset
```

으로 두고,

```
OMH Model Router
```

가 모델을 관리하도록 하겠습니다.

---

# 9. Stage 4 — REVISE

### OMH 적용도: ★★★★☆

ARS가 reviewer의 지적을:

```
Revision Roadmap
```

으로 변환합니다.

OMH는 이를 parallel work로 실행할 수 있습니다.

예:

```
Revision Roadmap
        │
        ▼
     OMH Plan
        │
 ┌──────┼────────┐
 ▼      ▼        ▼
Intro  Method   Related Work
수정    수정      수정
```

독립적인 section이라면 병렬화할 수 있습니다.

다만 서로 강하게 연결된 문단은 병렬화하면 논리 일관성이 깨질 수 있기 때문에 **chapter/issue dependency graph**를 먼저 만들어야 합니다.

---

# 10. Stage 3' — RE-REVIEW

### OMH 적용도: ★★★★☆

여기에서도 OMH multi-model reviewer를 사용할 수 있습니다.

다만 ARS의 `R&R Traceability Matrix`는 그대로 유지해야 합니다.

ARS는 이전 reviewer 지적과 revision 결과의 대응관계를 별도로 추적합니다. [GitHub](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-pipeline/SKILL.md?utm_source=chatgpt.com)

따라서 OMH는 reviewer 실행만 담당하고:

```
Review state
Revision traceability
Decision
```

은 ARS가 관리해야 합니다.

---

# 11. Stage 4.5 — FINAL INTEGRITY

### OMH 적용도: ★★★☆☆

Stage 2.5와 동일합니다.

ARS를 authoritative gate로 두는 것이 좋습니다.

```
ARS Integrity Gate
        │
        ├ PASS → Stage 5
        │
        └ FAIL → revision
```

OMH의 verification은 보조적으로 사용합니다.

---

# 12. Stage 5 — FINALIZE

ARS:

```
MD
↓
DOCX
↓
LaTeX
↓
PDF
```

### OMH 적용도: ★★★★★

매우 좋은 결합 지점입니다.

ARS는 Stage 5에서 MD → DOCX → LaTeX → PDF pipeline을 정의하고 있습니다. 특히 PDF는 LaTeX를 통해 compile하도록 규정합니다. [GitHub](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-pipeline/SKILL.md?utm_source=chatgpt.com)

OMH가 Docker sandbox나 coding executor를 사용해:

```
Pandoc
LaTeX
tectonic
Python
R
BibTeX
```

등을 실행하도록 하면 됩니다.

---

# 13. Stage 6 — PROCESS SUMMARY

### OMH 적용도: ★★★★★

이 단계에서 OMH Memory가 매우 유용합니다.

ARS Stage 6은 연구 과정 및 human-AI collaboration 기록을 생성합니다. [GitHub](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-pipeline/SKILL.md?utm_source=chatgpt.com)

여기에서 모든 내용을 장기 저장하기보다는 **핵심 연구지식만 OMH Memory candidate로 승격**하면 좋습니다.

예:

```
논문 전체 대화
       ↓
ARS Stage 6
       ↓
Knowledge Extraction
       ↓
OMH Memory Candidate
       ↓
Review
       ↓
Long-term Research Memory
```

OMH Memory는 자동 저장이 아니라 review를 거친 정보만 provenance와 함께 보존하도록 설계돼 있습니다. [GitHub](https://github.com/rlaope/oh-my-hermes)

박사논문처럼 몇 달 이상 진행되는 연구에서는 이 기능이 특히 유용합니다.

---

# 14. 제가 권장하는 통합 아키텍처

최종적으로는 다음 구조를 추천합니다.

```
                  Researcher
                      │
                      ▼
              Hermes + OMH
                      │
             ┌────────┴────────┐
             │                 │
       Research Memory     ARS Router
                               │
                               ▼
                     Academic Pipeline
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
 Stage 1 Research         Stage 2 Write          Stage 3 Review
        │                      │                      │
        ▼                      ▼                      ▼
     OMH Deep             OMH Writing         OMH Multi-model
        │                      │                  Reviewers
        ▼                      ▼                      │
 Parallel Search          Draft generation           │
        │                      │                      │
        └──────────────┬───────┴──────────────────────┘
                       │
                       ▼
                 ARS Integrity
                 Stage 2.5/4.5
                       │
                 ┌─────┴─────┐
                 │           │
                FAIL        PASS
                 │           │
               Revise     Finalize
                             │
                             ▼
                       OMH Sandbox
                       Pandoc/LaTeX
                             │
                             ▼
                         Stage 6
                             │
                             ▼
                       OMH Memory
```

---

# 15. 기능별 소유권을 명확히 하면 충돌이 거의 사라집니다

제가 추천하는 규칙은 매우 단순합니다.


| 기능                         | Owner          |
| -------------------------- | -------------- |
| 연구방법론                      | **ARS**        |
| Research Question          | **ARS**        |
| Literature Review protocol | **ARS**        |
| 논문 구조                      | **ARS**        |
| Academic writing rules     | **ARS**        |
| Citation integrity         | **ARS**        |
| Reviewer protocol          | **ARS**        |
| Revision state             | **ARS**        |
| Pipeline state             | **ARS**        |
| Model selection            | **OMH**        |
| Reasoning effort           | **OMH**        |
| Parallel execution         | **OMH**        |
| Web/tool execution         | **OMH/Hermes** |
| Coding/analysis executor   | **OMH**        |
| Docker sandbox             | **OMH/Hermes** |
| Long-term research memory  | **OMH**        |
| Cost/token tracking        | **OMH**        |
| Runtime verification       | **OMH**        |


이렇게 하면 **ARS와 OMH의 역할 경계가 명확합니다.**

---

# 16. 설치 방식도 “그대로 복사”보다 Adapter 방식이 좋습니다

ARS 공식 설치 구조는 기본적으로 Claude Code용 네 개 스킬을 설치하는 방식입니다.

```
deep-research
academic-paper
academic-paper-reviewer
academic-pipeline
```

ARS 자체 package도 이 네 skill을 노출합니다. [GitHub](https://github.com/Imbad0202/academic-research-skills/blob/main/docs/SETUP.md?utm_source=chatgpt.com)

하지만 OMH는 자체 managed skill catalog를 $OMH_HOME 아래 관리하고, 이를 Hermes `skills.external_dirs`에 등록합니다. 생성된 OMH managed skill은 직접 수정하지 않는 것이 전제입니다. [GitHub](https://github.com/rlaope/oh-my-hermes/blob/main/CONTEXT.md?utm_source=chatgpt.com)

따라서 이런 방식:

```
~/.omh/skills/
    academic-paper/
    deep-research/
```

에 ARS를 직접 섞는 것보다는,

```
~/.academic-research-skills/
        │
        ├ deep-research
        ├ academic-paper
        ├ academic-paper-reviewer
        └ academic-pipeline
```

을 별도로 유지하고,

```
Hermes
 skills.external_dirs:
   - OMH managed skills
   - ARS skills
```

처럼 등록하는 구조가 더 안전합니다.

---

# 17. 더 좋은 방법: OMH용 ARS Adapter Skill

장기적으로는 이것이 가장 좋다고 봅니다.

```
omh-ars
```

라는 얇은 integration skill 하나만 만드는 것입니다.

역할은:

```
사용자 요청
   ↓
OMH Router
   ↓
omh-ars
   ↓
ARS academic-pipeline
```

그리고 `omh-ars`가 다음 규칙만 담당합니다.

```
1. ARS pipeline state는 수정하지 않는다.

2. ARS integrity gate를 OMH QA로 대체하지 않는다.

3. ARS model tiering은 비활성화한다.

4. ARS가 만든 subtask만 OMH에 delegate한다.

5. ARS Material Passport를 그대로 보존한다.

6. OMH memory에는 ARS 결과 전체가 아니라
   검토된 핵심 research knowledge만 저장한다.
```

이렇게 하면 **충돌 방지 layer** 역할까지 할 수 있습니다.

---

# 18. 사용자께서 구상하시는 논문 자동화 환경에는 특히 적합합니다

기존에 말씀하신:

```
주기적 논문 수집
      ↓
요약 / 분석
      ↓
주제별 지식 축적
      ↓
Research Gap 탐색
      ↓
논문 아이디어 생성
      ↓
논문 작성
```

시스템을 확장하면:

```
                 OMH + Hermes
                      │
       ┌──────────────┼──────────────┐
       │              │              │
 Literature       Research       Research
 Collector         Memory          Agent
       │              │              │
       └──────────────┼──────────────┘
                      ▼
                 LLM Wiki
              Compound Knowledge
                      │
                      ▼
               Gap Discovery
                      │
                      ▼
             Research Candidate
                      │
                      ▼
              ┌─────────────┐
              │     ARS     │
              └──────┬──────┘
                     │
     Research → Write → Review
                     │
               Integrity Gate
                     │
                  Revision
                     │
                  SCI Paper
                     │
                     ▼
                OMH Memory
                     │
                     ▼
          다음 논문 아이디어 생성
```

이 구조가 됩니다.

단순히 **“AI가 논문 한 편 써주는 시스템”**이 아니라,

> **연구를 할수록 지식이 축적되고, 그 지식에서 다음 연구 gap이 발견되는 연구 운영 시스템**

으로 발전시킬 수 있습니다.

따라서 현재 기준 제 평가는 **ARS 설치 자체는 추천**, 하지만 **ARS를 OMH builtin skill처럼 흡수하는 방식은 비추천**, 그리고 `OMH orchestration → ARS academic pipeline → OMH execution/memory`**의 3계층 구조를 가장 추천**합니다. ARS가 연구 절차의 authoritative state machine을 유지하고 OMH가 모델·병렬화·도구 실행·장기기억을 담당하게 만들면 두 프로젝트의 강점이 가장 잘 살아납니다.