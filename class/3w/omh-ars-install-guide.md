네, **그 의미가 맞습니다.** 다만 정확하게는 **2단계 구조**로 이해하시면 됩니다.

```
[1단계] ARS 원본을 독립적으로 설치
        ↓
[2단계] OMH ↔ ARS 사이에
        omh-ars Integration Skill 추가
```

즉 **ARS를 OMH 내부에 뜯어서 합치는 것이 아니라**, ARS 원본은 별도로 유지하고 `omh-ars`가 두 시스템 사이의 **Adapter/Bridge** 역할을 하도록 만드는 방식입니다.

### 구조는 이렇게 됩니다

```
Hermes
  │
  ▼
OMH
  │
  │  "논문 연구 작업이다"
  ▼
omh-ars
Integration Skill
  │
  │  ARS workflow 호출
  ▼
ARS
├─ deep-research
├─ academic-paper
├─ academic-paper-reviewer
└─ academic-pipeline
  │
  ▼
논문 연구/작성/검증
```

여기서 중요한 점은 **Adapter 설치와 Integration Skill이 별개의 ARS 복사본을 만드는 것이 아니라는 것**입니다.

예를 들어 개념적으로 디렉터리를 구성하면:

```
~/.academic-research-skills/
│
├── deep-research/
├── academic-paper/
├── academic-paper-reviewer/
└── academic-pipeline/
        ↑
        │ 호출
        │
~/.omh/...
└── integrations/
    └── omh-ars/
        └── SKILL.md
```

`omh-ars/[SKILL.md](http://SKILL.md)`에는 새로운 논문 작성 기능을 잔뜩 넣는 게 아니라 **통합 규칙**을 넣습니다.

예를 들면:

```
# OMH-ARS Integration

## 역할
Academic research 요청은 ARS academic-pipeline을 사용한다.

## Ownership

ARS owns:
- Research methodology
- Academic pipeline
- Citation integrity
- Material Passport
- Peer review
- Revision state

OMH owns:
- Model routing
- Parallel execution
- Tool execution
- Sandbox
- Long-term memory
- Runtime verification

## Rules

1. ARS academic-pipeline을 authoritative workflow로 사용한다.
2. ARS integrity gate를 우회하지 않는다.
3. OMH ulw-research로 ARS deep-research를 대체하지 않는다.
4. ARS가 만든 독립 research task는 OMH로 병렬화할 수 있다.
5. 모델 routing은 OMH가 담당한다.
6. ARS provenance와 Material Passport는 보존한다.
7. 최종 검증된 연구지식만 OMH memory candidate로 전달한다.
```

이것이 제가 말한 **`omh-ars Integration Skill`**의 핵심입니다.

### 그러면 실제 요청은 어떻게 흘러가나?

사용자가 Hermes에서:

> “CTI-KG 기반 AI Agent 보안에 관한 SCI 논문 연구를 시작해줘.”

라고 하면,

```
사용자
 ↓
Hermes
 ↓
OMH
 ↓
omh-ars
 ↓
"Academic Research 요청"
 ↓
ARS academic-pipeline
 ↓
Stage 1 Research
 ↓
ARS가 research task 생성
 ↓
OMH
 ├─ Task A → Model A
 ├─ Task B → Model B
 ├─ Task C → Model C
 └─ Task D → Model D
 ↓
ARS가 결과 통합
 ↓
Stage 2 Writing
 ↓
Stage 2.5 Integrity
 ↓
Stage 3 Review
 ↓
Revision
 ↓
Final Integrity
 ↓
SCI Paper
```

즉 재미있는 부분은 **제어권이 왕복한다는 것**입니다.

```
OMH
 ↓
ARS                ← 무엇을 연구할지 결정
 ↓
OMH                ← 어떻게 효율적으로 실행할지
 ↓
ARS                ← 연구 결과를 어떻게 논문화할지
 ↓
OMH                ← 모델/도구/병렬실행
 ↓
ARS                ← Integrity / Review
 ↓
OMH Memory          ← 검증된 지식 축적
```

### 왜 그냥 ARS를 OMH에 설치하는 것보다 좋은가?

가장 큰 이유는 **업데이트와 충돌 관리**입니다.

ARS가 업데이트되어 `academic-pipeline`이나 integrity 규칙이 변경되어도 **ARS 원본을 그대로 업데이트**할 수 있습니다. OMH가 업데이트되어 model routing이나 `ulw-*` workflow가 변경되어도 OMH 역시 독립적으로 업데이트할 수 있습니다.

그 사이의 `omh-ars`만 우리가 관리합니다.

```
OMH 업데이트 ──┐
               │
          [ omh-ars ]
               │
ARS 업데이트 ──┘
```

소프트웨어 구조로 비유하면:

**OMH = Operating/Orchestration Framework**

**ARS = Academic Research Application**

**omh-ars = Adapter / Integration Layer**

라고 생각하시면 가장 정확합니다.

그리고 여기서 한 단계 더 발전시키는 것을 추천합니다. `omh-ars`를 단순 호출용 Skill 하나가 아니라 **ARS 단계별 OMH capability mapping**까지 가진 integration package로 설계하는 것입니다.

예를 들어:


| ARS             | OMH 적용                 | 실행 정책 |
| --------------- | ---------------------- | ----- |
| Research        | Parallel + Deep models | 적극 적용 |
| Writing         | Writing model routing  | 적용    |
| Integrity       | Verification           | 보조만   |
| Review          | Multi-model            | 적극 적용 |
| Revision        | Parallel work          | 조건부   |
| Final Integrity | Verification           | 보조만   |
| Finalize        | Sandbox                | 적극 적용 |
| Summary         | Memory                 | 적극 적용 |


이렇게 만들어 놓으면 이후에는 사용자가 OMH에게 그냥 **“ARS로 이 주제 논문 연구 시작해줘”**라고 해도 integration skill이 자동으로 **ARS workflow + OMH 기능의 역할 분담 규칙**을 적용하는 구조를 목표로 할 수 있습니다.

원하시면 다음 단계로 **실제로 OMH에 설치할 수 있는** `omh-ars` **Integration Skill의 디렉터리 구조 +** [`SKILL.md`](http://SKILL.md) **+ 설치/설정 방법까지 구현 가능한 수준으로 설계**해드릴 수 있습니다.



# Installed Architecture



설치 구조                                                                                                                          

                                                                                                                                       

    ARS 원본과 OMH Adapter를 분리했습니다.                                                                                             

                                                                                                                                        

      ─ text                                                                                                                            

      /home/ainsdev/.academic-research-skills/                                                                                         

      ├── deep-research/                                                                                                               

      ├── academic-paper/                                                                                                              

      ├── academic-paper-reviewer/                                                                                                     

      └── academic-pipeline/                                                                                                           

      /home/ainsdev/.omh-integrations/                                                                                                 

      └── omh-ars/                                                                                                                     

          ├── [SKILL.md](http://SKILL.md)                                                                                                                 

          ├── references/                                                                                                              

          │   ├── [capability-mapping.md](http://capability-mapping.md)                                                                                                

          │   └── [compatibility.md](http://compatibility.md)                                                                                                     

          └── scripts/                                                                                                                 

              └── install_ars_[adapter.sh](http://adapter.sh)                                                                                               

                                                                                                                                       

    OMH managed catalog인 /home/ainsdev/.omh/skills에는 ARS 원본이나 Adapter를 복사하지 않았습니다.                                    

                                                                                                                                       

    Hermes 설정                                                                                                                        

                                                                                                                                       

    skills.external_dirs는 다음 세 경로를 유지하도록 설정했습니다.                                                                     

                                                                                                                                       

      ─ json                                                                                                                           

      [                                                                                                                                

        "/home/ainsdev/.omh/skills",                                                                                                   

        "/home/ainsdev/.academic-research-skills",                                                                                     

        "/home/ainsdev/.omh-integrations"                                                                                              

      ]                                                                                                                                

                                                                                                                                       

    따라서 역할이 다음처럼 분리됩니다.                                                                                                 

                                                                                                                                       

    • /home/ainsdev/.omh/skills: OMH managed skills                                                                                    

    • /home/ainsdev/.academic-research-skills: ARS upstream checkout                                                                   

    • /home/ainsdev/.omh-integrations: 사용자 관리 Integration Adapter                                                                 

                                                                                                                                       

    설치된 버전                                                                                                                        

                                                                                                                                       

    • ARS repository version: 3.21.2                                                                                                   

    • Git revision: c7af8b9017954c745ed7ad4afed4dba460a6c247                                                                           

    • deep-research: 2.12.1                                                                                                            

    • academic-paper: 3.3.1                                        

    • academic-paper-reviewer: 1.11.1                                                                                                  

    • academic-pipeline: 3.21.2                                                                                                        

    • omh-ars: 1.0.0                                                                                                                   

                                                                                                                                       

    omh-ars 적용 규칙                                                                                                                  

                                                                                                                                       

    Adapter에는 요청하신 경계를 반영했습니다.                                                                                          

                                                                                                                                       

    1. ARS가 연구 방법론과 pipeline state를 소유합니다.                                                                                

    2. ARS integrity gate를 OMH verification으로 대체하거나 약화하지 않습니다.                                                         

    3. ulw-research로 ARS deep-research를 대체하지 않습니다.       

    4. ARS가 먼저 분리한 독립 subtask만 OMH가 병렬화합니다.                                                                            

    5. Material Passport와 provenance를 보존합니다.                                                                                    

    6. ARS_MODEL_TIERING을 사용하지 않고 OMH가 모델 라우팅을 담당합니다.                                                               

    7. 검토된 최종 연구지식만 memory candidate로 취급합니다.                                                                           

    8. Claude Code 전용 hook, slash command, Task 동작이 Hermes에서 실행됐다고 허위로 간주하지 않습니다.                               

                                                                                                                                       

    검증 결과                                                                                                                           

                                                                                                                                       

    실제 설치 및 반복 실행 검증 결과:                                                                                                  

                                                                                                                                        

      ─ text                                                                                                                            

      OMH_ARS_INSTALL=PASS                                                                                                             

      ars_root=/home/ainsdev/.academic-research-skills                                                                                  

      ars_version=3.21.2

      adapter_skill=/home/ainsdev/.omh-integrations/omh-ars                                                                            

      ars_model_tiering=unset                                                                                                          

      loader_skills=omh-ars,deep-research,academic-paper,academic-paper-reviewer,academic-pipeline                                     

      omh_doctor=Status: ok                                                                                                            

                                                                                                                                       

    추가 확인 사항:                                                                                                                    

                                                                                                                                       

    • 독립된 새 hermes skills list 프로세스에서 5개 스킬 모두 발견                                                                     

    • skill_view로 4개 ARS 스킬 모두 원본 checkout 경로에서 로드됨                                                                     

    • omh-ars는 /home/ainsdev/.omh-integrations/omh-ars에서 로드됨                                                                     

    • Adapter updater 반복 실행 테스트 통과                                                                                            

    • omh doctor: 48/48 checks passing                                                                                                 

    • Blocking issue: 0                                                                                                                

    • 현재 ARS_MODEL_TIERING: unset                                                                                                    

                                                                                                                                       

    Doctor의 기존 경고 2건은 ARS 설치 문제가 아닙니다.                                                                                  

                                                                                                                                       

    • cronalytics와 OMH plugin 사이의 on_session_end hook 이름 충돌                                                                    

    • Hermes memory consolidation 권고                                                                                                 

                                                                                                                                       

    업데이트 방법                                                                                                                      

                                                                                                                                       

    향후 ARS upstream과 설정을 안전하게 갱신하려면 다음 updater를 실행하면 됩니다.                                                     

                                                                                                                                       

      ─ bash                                                                                                                           

      bash /home/ainsdev/.omh-integrations/omh-ars/scripts/install_ars_[adapter.sh](http://adapter.sh)                                                      

                                                                                                                                       

    Updater는:                                                                                                                         

                                                                                                                                       

    • clean checkout일 때만 fast-forward update                                                                                        

    • 로컬 변경이 있으면 중단하고 변경을 보존                                                                                          

    • 네 개 ARS 스킬 존재 여부 확인                                                                                                    

    • external directory 설정 보존 및 재검증                                                                                           

    • Hermes loader와 omh doctor 재검증                                                                                                

                                                                                                                                       

    을 수행합니다.                                                                                                                     

                                                                                                                                       

    현재 대화에서도 external skill 로딩은 확인됐지만, 새로운 skill catalog와 routing 설명이 시스템 프롬프트에 완전히 반영되도록        

    Hermes 세션을 한 번 재시작하거나 reload하는 것을 권장합니다. 이후에는 다음처럼 요청할 수 있습니다.                                 

                                                                                                                                       

      ─ text                                                                                                                           

      ARS로 CTI-KG 기반 AI Agent 보안 SCI 논문 연구를 시작해줘.                                                                        

                                                                                                                                       

    이 요청은 omh-ars → academic-pipeline 경로로 처리됩니다. 

