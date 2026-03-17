# Shorts Producer -- 초보자 UX 동선 분석 및 개선 제안서

> 작성: UI/UX Engineer Agent | 2026-02-15
> 분석 대상: 코드베이스 전체 (frontend/app/ 구조 기반)

---

## 1. 초보자 동선 분석: "앱을 여는 순간부터 영상 1개 완성까지"

### 전체 여정 맵

```
[Step 1]           [Step 2]           [Step 3]           [Step 4]
 Home              Studio/Kanban      Script Tab          Stage Tab
 (Video Gallery)   (프로젝트 목록)    (스크립트 작성)      (에셋 사전 준비)
     |                  |                  |                  |
     v                  v                  v                  v
 Showcase +         + New Shorts      Topic 입력 +       이미지/TTS/BGM
 Quick Actions      버튼 클릭          Generate Script    사전 생성
                                                              |
                                          [Step 5]       [Step 6]       [Step 7]
                                          Direct Tab     Publish Tab    완성 영상 확인
                                          (씬 편집)      (렌더 설정)     (Home Gallery)
                                              |              |
                                              v              v
                                          씬별 프롬프트   Voice/BGM 설정
                                          + 이미지 수정   + Render 버튼
```

### 단계별 상세 분석

#### Step 1: Home 진입 (`/`)

**사용자가 보는 것**: Video Gallery (빈 상태이면 "Your Showcase Awaits" + "Start Creating" CTA) + Quick Actions (New Project, Create Character, Browse Styles, Browse Voices) + Quick Stats.

**초보자 마찰 지점**:
- **(낮음)** Quick Actions에 "New Project"가 있는데, 이것은 Studio의 Kanban으로 이동한다. "Project"라는 용어가 "하나의 영상 프로젝트"인지 "채널/브랜드 단위 프로젝트"인지 모호하다.
- **(낮음)** "Create Character"와 "Browse Styles"는 영상을 만들기 전에 해야 하는 전제 조건인지, 선택 사항인지 알기 어렵다. 순서 가이드가 없다.

**좋은 점**: 빈 상태의 "Start Creating" CTA가 명확하다. 처음 진입 시 바로 다음 행동을 알 수 있다.

---

#### Step 2: Studio 진입 -- Kanban View (`/studio`, 스토리보드 미선택 시)

**사용자가 보는 것**: "Projects" 헤더 + 4열 Kanban (draft / in_prod / rendered / published) + "+ New Shorts" 버튼. 우측에 HomeSecondaryPanel(통계).

**초보자 마찰 지점**:
- **(높음)** **"Select a project to view storyboards"** -- 프로젝트가 선택되지 않은 경우 이 메시지만 나온다. PersistentContextBar에서 프로젝트를 먼저 선택해야 하는데, 이 Context Bar는 높이 32px(`h-8`)의 매우 작은 영역이다. 초보자가 여기서 프로젝트를 만들어야 한다는 것을 인지하기 어렵다.
- **(높음)** **프로젝트/그룹 계층 구조의 진입 장벽**: "Project" > "Group" > "Storyboard"의 3계층 구조를 이해해야 한다. 처음 사용하는 사람에게 "왜 그룹이 필요한지"가 설명되지 않는다.
- **(중간)** Kanban 열 이름 "draft / in_prod / rendered / published"가 영어 약어(in_prod)와 전문 용어 혼재이다.

**"다음에 뭘 해야 하지?" 모멘트**:
- 프로젝트가 없을 때: 화면 중앙에 "Select a project"만 있고, 프로젝트 생성 유도가 약하다.
- 프로젝트는 있지만 그룹이 없을 때: Studio 내부에서 "Create a group to start saving storyboards" 배너가 나오지만, Kanban에서는 이 배너가 보이지 않는다 (스토리보드 선택 후에만 나온다).

---

#### Step 3: Script Tab (새 스토리보드 생성)

**사용자가 보는 것**: 3-column 레이아웃. 좌측 "Scene Outline" (비어있음), 중앙 ManualScriptEditor (Topic 입력 + Generate Script), 우측 ScriptSidePanel (Status + Tips).

**초보자 마찰 지점**:
- **(중간)** **Quick vs Full 모드 선택**: 토글이 있지만 차이점에 대한 설명이 부족하다. Quick은 바로 생성, Full은 AI가 컨셉 토론 후 생성하는 차이인데, 초보자는 "어떤 것을 골라야 하지?"에서 멈춘다. 우측 Tips 영역에 모드별 도움말이 있지만, 눈에 잘 띄지 않는다.
- **(중간)** **Structure/Duration/Language 설정**: StoryboardGeneratorPanel 안에 이 설정들이 있다. "Narrated Monologue"와 "Narrated Dialogue" 같은 구조 옵션이 무엇인지 초보자에게 불명확하다.
- **(낮음)** Character 선택 섹션이 같은 카드 안에 있어서 정보 밀도가 높다. 캐릭터를 먼저 만들어야 하는지, 나중에 해도 되는지 명확하지 않다.
- **(낮음)** Full 모드의 "Preset" 드롭다운 ("풀 오토 -- AI 자동 생성 후 승인" / "크리에이터 -- AI 초안 + 사용자 결정")은 한국어인 반면, 나머지 UI는 영어 혼재이다.

**좋은 점**: Generate Script 버튼이 명확하고, Progress bar로 생성 진행도를 보여준다. Full 모드의 ReviewApprovalPanel은 AI 협업 투명성이 잘 구현되어 있다.

---

#### Step 4: Direct Tab (씬별 편집)

**사용자가 보는 것**: 3-column 레이아웃. 좌측 SceneListPanel(씬 리스트), 중앙 SceneCard(현재 씬 편집), 우측 Image/Tools/Insight 3개 서브탭.

**초보자 마찰 지점**:
- **(높음)** **정보 과부하 -- SceneCard의 복잡도**: SceneCard 하나에 이미지 패널, 스크립트 텍스트, 프롬프트 필드, 태그, 화자 선택, 배경 선택, 품질 배지, 액션 바(Generate Image, Validate, Gemini Edit, Mark Success/Fail, Save Prompt 등)가 모두 들어있다. 30개 이상의 props가 이 복잡도를 반영한다.
- **(높음)** **우측 패널의 3개 서브탭이 역할 구분이 불명확하다**:
  - "Image" 탭: Style Profile 선택 + 프롬프트 설정 + 옵션 토글(Auto Compose, Auto Rewrite, Safe Tags, Hi-Res, Veo) -- 이미지 "설정"이지만 탭 이름이 "Image"
  - "Tools" 탭: Validate/Fix All + 3x Candidates/ControlNet/IP-Adapter 설정 -- 전문 도구
  - "Insight" 탭: 이미지 검증 결과 요약
  - 초보자는 "Image" 탭에서 이미지를 볼 수 있다고 기대하지만 설정 패널이 나온다.
- **(높음)** **"Auto Compose", "Auto Rewrite", "Safe Tags", "Hi-Res", "Veo"** 토글의 의미를 초보자가 이해하기 어렵다. 도움말이 없다.
- **(중간)** **씬 상태 배지 해독**: 각 씬에 script/image/validation/action 상태가 색상 코딩되어 있지만, 색상만으로 의미를 파악하기 어렵다. 특히 SceneListPanel의 작은 인디케이터(dot)로는 정보 전달이 부족하다.
- **(중간)** **ControlNet, IP-Adapter, LoRA** 같은 SD 전문 용어가 설명 없이 Tools 탭에 노출된다. 디자인 철학 문서에서 "초보자에게 전문 용어를 설명 없이 노출하지 않는다"고 명시했지만, 현재 이 원칙이 지켜지지 않고 있다.
- **(낮음)** SceneNavHeader의 좌/우 화살표로 씬 간 이동이 가능하지만, 키보드 단축키(좌/우 화살표)가 지원되는지 불명확하다.

**"다음에 뭘 해야 하지?" 모멘트**:
- 스크립트 생성 후 Direct 탭으로 전환되었는데, 이미지가 아직 없다. "Generate Image" 버튼이 SceneCard 안에 있지만, 모든 씬의 이미지를 한 번에 생성하는 것이 "Auto Run"이라는 것을 모른다.
- 이미지 생성 후 검증이 필요한지, 바로 Publish로 가도 되는지 판단이 어렵다.

---

#### Step 5: Publish Tab (렌더링)

**사용자가 보는 것**: 3-column 레이아웃. 좌측 PublishVideosSection(렌더 결과 목록), 중앙 RenderMediaPanel(미디어 설정), 우측 RenderSidePanel(레이아웃/렌더 버튼) + PublishCaptionLikes.

**초보자 마찰 지점**:
- **(중간)** **설정 항목이 많다**: Scene Text, Font, Ken Burns, Transition, Speed, Voice, BGM Mode, BGM Volume, Audio Ducking 등. 초보자는 기본값 그대로 렌더해도 되는지 불안해한다.
- **(중간)** **"Full" vs "Post" 레이아웃**: 우측 패널에서 선택하는데, 차이점에 대한 시각적 미리보기가 없다. "Full = YouTube Shorts", "Post = Instagram Post 카드" 라는 매핑이 명시되지 않는다.
- **(낮음)** 렌더 전 사전 조건 실패 시 한국어 메시지("스토리보드를 먼저 생성하세요", "프로젝트를 먼저 선택하세요")가 나오지만, 해결 방법(어디로 가야 하는지)의 링크가 없다.
- **(낮음)** "Ken Burns Preset", "Audio Ducking" 같은 전문 용어에 설명이 없다.

**좋은 점**: 렌더 진행률이 표시되고, 렌더 완료 시 토스트 피드백이 즉각적이다.

---

#### Step 6: 완성 영상 확인

**사용자가 보는 것**: Publish 탭 좌측에 렌더 결과가 나타나고, Home의 Video Gallery에서도 확인 가능.

**초보자 마찰 지점**:
- **(낮음)** 렌더 완료 후 "영상을 어디서 확인하지?" -- Publish 탭 좌측에 나타나지만, Home으로 가야 Gallery에서 볼 수 있다는 것이 직관적이지 않다.
- **(낮음)** 영상 다운로드 기능에 접근하는 방법이 명확하지 않다.

---

### 전체 여정 요약: 초보자의 최소 클릭 경로

| 단계 | 액션 | 클릭/입력 수 | 마찰 수준 |
|------|------|-------------|-----------|
| 1. Home 진입 | "Start Creating" 클릭 | 1 | 낮음 |
| 2. 프로젝트 생성 | Context Bar에서 프로젝트 드롭다운 > + New | 3 | **높음** |
| 3. 그룹 생성 | 배너의 "Create Group" 또는 Context Bar | 2 | **높음** |
| 4. Script 작성 | Topic 입력 + Generate Script | 2 | 낮음 |
| 5. 씬 승인/편집 | Approve & Edit → Direct 탭 전환 | 1-2 | 중간 |
| 6. 이미지 생성 | Auto Run 또는 개별 Generate Image | 1-N | 중간 |
| 7. 렌더 설정 | Publish 탭 이동 + 설정 확인 | 2 | 중간 |
| 8. 렌더 실행 | Render 버튼 클릭 | 1 | 낮음 |

**총 최소 12-15 클릭/입력** (프로젝트/그룹이 없는 경우). 프로젝트/그룹이 이미 있으면 8-10클릭.

---

## 2. 핵심 문제점 (우선순위순)

### P0 (Critical): 프로젝트/그룹 온보딩 장벽

**문제**: 처음 사용하는 사용자가 영상을 만들기 위해 "프로젝트 > 그룹 > 스토리보드" 3계층 구조를 이해하고 생성해야 한다. PersistentContextBar(h-8, 32px)라는 매우 작은 영역에서 이 작업을 수행해야 한다.

**영향**: 첫 번째 영상을 만들기까지의 시간이 비정상적으로 길어진다. 사용자가 "프로젝트가 뭐고 그룹이 뭔데?"에서 이탈할 수 있다.

**현재 코드 위치**: `/home/tomo/Workspace/shorts-producer/frontend/app/components/context/PersistentContextBar.tsx` (L100-160), `/home/tomo/Workspace/shorts-producer/frontend/app/components/studio/StudioKanbanView.tsx` (L27-33).

**근거**: StudioKanbanView는 `projectId`가 없으면 "Select a project to view storyboards." 한 줄만 보여준다. 프로젝트 생성으로의 유도가 전무하다.

---

### P1 (High): Direct 탭의 정보 과부하

**문제**: SceneCard(30+ props)에 이미지, 스크립트, 프롬프트, 태그, 검증 결과, 액션 버튼이 모두 밀집되어 있다. 우측 패널의 Image/Tools/Insight 탭 분류가 직관적이지 않다.

**영향**: 초보자가 "지금 뭘 수정해야 하는지" 판단하기 어렵고, 전문 용어(ControlNet, IP-Adapter, LoRA)가 설명 없이 노출된다.

**현재 코드 위치**: `/home/tomo/Workspace/shorts-producer/frontend/app/components/storyboard/SceneCard.tsx` (30-82줄의 props 정의).

---

### P2 (Medium): 전문 용어 노출 & 도움말 부재

**문제**: 다음 용어들이 설명 없이 UI에 노출된다:
- Auto Compose / Auto Rewrite / Safe Tags / Hi-Res / Veo (이미지 설정 영역)
- ControlNet / IP-Adapter / 3x Candidates (SceneToolsContent)
- Ken Burns / Audio Ducking / Transition Type (PublishTab)
- Quick vs Full 모드 (ScriptTab)

**영향**: 디자인 철학 원칙 1(점진적 공개)의 "Don't" 조항 -- "초보자에게 Danbooru 태그, LoRA weight, CFG Scale 같은 용어를 설명 없이 노출하지 않는다"를 위반한다.

**현재 코드 위치**: `/home/tomo/Workspace/shorts-producer/frontend/app/components/studio/SceneToolsContent.tsx` (L101-205).

---

### P3 (Medium): 탭 간 컨텍스트 전환 비용

**문제**: Script > Stage > Direct > Publish 탭 전환 시 사용자가 현재 상태를 파악하는 데 시간이 걸린다. PipelineStatusDots(4개의 2px 점)는 정보 전달이 미약하다.

**영향**: 사용자가 "이미지 생성이 끝났는데 다음에 뭘 해야 하지?"를 반복적으로 느낀다.

**현재 코드 위치**: `/home/tomo/Workspace/shorts-producer/frontend/app/components/studio/PipelineStatusDots.tsx` (L65-89: 2px dot 크기).

---

### P4 (Low): 히든 기능 -- 발견하기 어려운 중요 기능들

| 기능 | 위치 | 문제 |
|------|------|------|
| MaterialsPopover | Studio 헤더의 "3/5" 배지 | 배지의 의미를 초보자가 추측하기 어렵다 |
| Command Palette (Cmd+K) | 헤더 우측 kbd 힌트 | 작은 크기(12px)로 눈에 띄지 않는다 |
| Auto Run | Studio 헤더 우측 | "Auto Run"이 무엇을 하는지 라벨만으로 불명확하다 |
| Preflight Check | Auto Run 클릭 시 모달 | 유용한 기능이지만 Auto Run을 클릭해야만 발견된다 |
| Keyboard Shortcuts (Cmd+S, Cmd+Enter) | 코드에만 존재 | UI에 단축키 가이드가 없다 |
| Prompt Helper Sidebar | Direct 탭 Image 설정 내 | 접근 경로가 깊다 |

---

## 3. 외부 좋은 사례 참고

### Canva -- 온보딩 & 템플릿 퍼스트

| 패턴 | Canva 구현 | Shorts Producer 적용 가능성 |
|------|-----------|---------------------------|
| **Zero-config Start** | "What will you design today?" + 템플릿 그리드 | "어떤 영상을 만들까요?" + 토픽 예시 카드로 바로 시작 |
| **Template Gallery** | 인기 템플릿 클릭 한 번으로 에디터 진입 | 인기 토픽/구조 조합 프리셋으로 3클릭 이내 진입 |
| **Brand Kit = Style Profile** | 한 번 설정하면 모든 디자인에 자동 적용 | Style Profile 자동 적용은 이미 잘 구현됨 |
| **사이드바 에셋 브라우저** | 좌측 사이드바에서 에셋 검색/삽입 | Library 접근이 탭 이동 없이 인라인으로 가능하면 좋겠음 |

### CapCut -- 타임라인 & 미리보기

| 패턴 | CapCut 구현 | Shorts Producer 적용 가능성 |
|------|-----------|---------------------------|
| **타임라인 뷰** | 하단 타임라인에서 전체 영상 구조를 한눈에 | SceneListPanel을 타임라인 형태로 시각화 (시간축 기반) |
| **실시간 미리보기** | 편집 중 우측에 영상 미리보기 | Direct 탭에서 씬 이미지가 어떻게 영상에 합성될지 프리뷰 |
| **원클릭 내보내기** | 우상단 Export 버튼 하나 | Publish 설정을 줄이고 "기본값으로 빠른 렌더" 옵션 |

### Midjourney -- AI 생성 UX

| 패턴 | Midjourney 구현 | Shorts Producer 적용 가능성 |
|------|---------------|---------------------------|
| **4-up Grid** | 하나의 프롬프트로 4개 후보 | 이미 3x Candidates로 구현. UI에서 후보 비교가 더 직관적이면 좋겠음 |
| **Variation/Upscale** | 후보 선택 후 변형/고해상화 | Gemini Edit + Hi-Res 조합으로 유사하게 구현됨 |
| **Simple Prompt** | 자연어 프롬프트 한 줄 | Auto Compose가 이 역할. 더 전면에 노출 필요 |

### Runway ML -- AI 영상 생성

| 패턴 | Runway 구현 | Shorts Producer 적용 가능성 |
|------|-----------|---------------------------|
| **단계별 마법사(Wizard)** | 이미지 업로드 > 모션 설정 > 생성 | Script > Image > Render의 선형 흐름은 유사. 더 가이드가 강화되면 좋겠음 |
| **실시간 비용 표시** | 크레딧 소비량 사전 표시 | Preflight에서 예상 시간은 표시하지만, 더 눈에 띄게 |

### Gamma (AI 프레젠테이션) -- 점진적 세부화

| 패턴 | Gamma 구현 | Shorts Producer 적용 가능성 |
|------|-----------|---------------------------|
| **Topic > Outline > Full** | 주제 입력 > AI 아웃라인 생성 > 사용자 수정 > 전체 생성 | 현재 Full 모드의 Review/Approve 흐름이 이와 유사. Quick 모드에도 적용 검토 |
| **블록 단위 편집** | 생성 결과를 블록 단위로 교체/수정 | 씬 단위 편집이 이 패턴과 일치 |

---

## 4. 구체적 개선 제안

### 단기 (1-2주) -- 코드 수준 개선

#### S1. 프로젝트 미선택 시 온보딩 유도 강화

**현재**: StudioKanbanView에서 `projectId`가 없으면 "Select a project" 한 줄 텍스트.

**개선안**: 빈 상태에 프로젝트 생성 위자드 인라인 카드를 배치한다.

```
[변경 전]
  "Select a project to view storyboards."

[변경 후]
  ┌────────────────────────────────────────┐
  │  시작하기                               │
  │                                        │
  │  영상을 만들려면 프로젝트가 필요합니다.     │
  │  프로젝트는 채널이나 브랜드 단위로          │
  │  영상을 묶어서 관리하는 폴더입니다.         │
  │                                        │
  │  [+ 첫 프로젝트 만들기]                    │
  └────────────────────────────────────────┘
```

**대상 파일**: `/home/tomo/Workspace/shorts-producer/frontend/app/components/studio/StudioKanbanView.tsx` (L27-33)

---

#### S2. PipelineStatusDots를 텍스트 라벨 포함 형태로 확장

**현재**: 4개의 2px 점(dot)으로 상태를 표시. 호버해야 의미를 알 수 있다.

**개선안**: 점 옆에 축약 라벨을 추가하여 호버 없이도 파악 가능하게 한다.

```
[변경 전]
  ● ● ○ ○    (2px dots, 호버 시 툴팁)

[변경 후]
  ● Script  ● Images  ○ Render  ○ Video
  (8px dots + 라벨, 진행 중인 항목은 pulse 애니메이션)
```

**대상 파일**: `/home/tomo/Workspace/shorts-producer/frontend/app/components/studio/PipelineStatusDots.tsx`

---

#### S3. 우측 패널 탭 이름 변경 (Direct Tab)

**현재**: Image / Tools / Insight

**개선안**:
- "Image" -> "Style" (실제 내용이 Style Profile + 프롬프트 설정이므로)
- "Tools" -> "Advanced" (전문 도구라는 것을 명시)
- "Insight" -> "Quality" (품질 검증 결과라는 것을 명시)

**대상 파일**: Direct 탭의 우측 패널 서브탭 컴포넌트

---

#### S4. 전문 용어에 인라인 도움말(Tooltip) 추가

**대상**: 이미지 설정 영역의 토글 옵션 + SceneToolsContent의 설정.

```
[변경 전]
  Auto Compose    [토글]

[변경 후]
  Auto Compose (?) [토글]
  (?) 호버 시: "AI가 씬 태그와 캐릭터 정보를 자동으로 프롬프트에 합성합니다"
```

**적용 대상 목록**:
| 용어 | 설명 |
|------|------|
| Auto Compose | AI가 씬 태그와 캐릭터 정보를 자동으로 프롬프트에 합성 |
| Auto Rewrite | AI가 프롬프트를 SD에 최적화된 형태로 재작성 |
| Safe Tags | 위험한(불일치하기 쉬운) 태그를 안전한 대안으로 자동 교체 |
| Hi-Res | 2단계 고해상도 업스케일링 활성화 |
| Veo | Google Veo를 사용한 비디오 클립 생성 활성화 |
| 3x Candidates | 한 번에 3장의 후보 이미지를 생성하여 선택 |
| ControlNet | 포즈/구도를 레퍼런스 이미지에 맞춰 제어 |
| IP-Adapter | 캐릭터 얼굴/스타일을 레퍼런스와 일치시킴 |
| Ken Burns | 정지 이미지에 줌/팬 모션 효과 적용 |
| Audio Ducking | 나레이션 시 배경 음악 볼륨을 자동 감소 |

**대상 파일**: `/home/tomo/Workspace/shorts-producer/frontend/app/components/studio/SceneToolsContent.tsx` 및 이미지 설정 관련 컴포넌트

---

#### S5. Quick/Full 모드 설명 강화

**현재**: 버튼만 있고 차이점 설명이 없다.

**개선안**: 모드 선택 영역 아래에 한 줄 설명을 추가한다.

```
  [Quick]  [Full]
  Quick: 토픽 입력 -> AI가 즉시 스크립트 생성
  Full: AI가 컨셉을 먼저 토론한 후, 사용자 승인을 거쳐 생성
```

**대상 파일**: `/home/tomo/Workspace/shorts-producer/frontend/app/components/studio/ScriptTab.tsx` (L84-99)

---

### 중기 (2-4주) -- 구조적 개선

#### M1. "빠른 시작" 워크플로우 (Zero-config Path)

**목표**: 프로젝트/그룹 없이도 첫 영상을 만들 수 있는 경로.

**설계 방향**:
- Home의 "Start Creating" 클릭 시 토픽 입력 모달이 바로 열린다.
- 프로젝트/그룹은 "My First Project" / "Default"로 자동 생성된다.
- 사용자는 나중에 이름을 변경하거나 구조를 재편할 수 있다.
- 이렇게 하면 초보자의 진입 경로가 3클릭(Home > 토픽 입력 > Generate)으로 줄어든다.

**UI 와이어프레임**:

```
┌─ Home (빈 상태) ──────────────────────┐
│                                       │
│   Your Showcase Awaits                │
│                                       │
│   ┌────────────────────────────────┐  │
│   │  어떤 영상을 만들까요?           │  │
│   │                                │  │
│   │  [토픽을 입력하세요...]          │  │
│   │                                │  │
│   │  [+ 시작하기]                   │  │
│   └────────────────────────────────┘  │
│                                       │
│   또는: [기존 프로젝트에서 시작]       │
│                                       │
└───────────────────────────────────────┘
```

---

#### M2. Direct 탭 점진적 공개 강화

**목표**: SceneCard의 복잡도를 2-tier로 나눈다.

**Tier 1 (기본 노출)**:
- 이미지 미리보기 + Generate Image 버튼
- 스크립트 텍스트 (읽기 전용, 클릭 시 편집)
- 품질 배지 (Match Rate)

**Tier 2 (확장 시 노출)**:
- 프롬프트 편집 필드
- 태그 편집
- 화자 선택
- 배경 설정
- Gemini Edit / Validate / Mark 등 고급 액션

**현재 참고**: SceneCard에 이미 CollapsibleSection과 "Advanced Settings" 토글 개념이 존재한다(`showAdvancedSettings` 상태). 이를 더 적극적으로 활용하여, 기본 뷰에서는 이미지와 스크립트만 보이고, "Edit Details"를 클릭하면 전체 편집 UI가 펼쳐지는 구조로 전환한다.

---

#### M3. 렌더 프리셋 ("Quick Render")

**목표**: Publish 탭의 설정 항목을 줄인다.

**설계 방향**:
- "Quick Render" 버튼: 모든 설정을 기본값으로 하고 바로 렌더.
- "Custom Render" 경로: 현재와 동일한 상세 설정.
- Full/Post 레이아웃 선택 시 각각의 미리보기 썸네일을 표시.

```
┌─ Publish Tab ──────────────────────┐
│                                    │
│  ┌──────────┐  ┌──────────┐       │
│  │ Full     │  │ Post     │       │
│  │ (9:16)   │  │ (카드)   │       │
│  │ [미리보기]│  │ [미리보기]│       │
│  └──────────┘  └──────────┘       │
│                                    │
│  [Quick Render]  [Custom Settings] │
│                                    │
└────────────────────────────────────┘
```

---

#### M4. 가이드 배너 시스템 (Next Step Hint)

**목표**: 각 탭에서 "다음에 해야 할 일"을 상단 배너로 안내한다.

**규칙**:
- Script 탭 + 씬 0개: "토픽을 입력하고 Generate Script를 클릭하세요"
- Direct 탭 + 이미지 0개: "Auto Run으로 모든 씬의 이미지를 한 번에 생성하세요"
- Direct 탭 + 이미지 완료: "Publish 탭으로 이동하여 영상을 렌더링하세요"
- Publish 탭 + 렌더 미완료: "레이아웃을 선택하고 Render 버튼을 클릭하세요"

**구현**: 조건 기반 배너 컴포넌트를 StudioWorkspace 상단에 배치. 닫기(dismiss) 가능.

---

### 장기 (1-2개월) -- 아키텍처 수준 개선

#### L1. 통합 타임라인 뷰

Direct 탭의 좌측 SceneListPanel을 타임라인 형태로 재설계한다. 각 씬의 duration을 시간축에 매핑하여, 전체 영상의 구조를 한눈에 파악할 수 있게 한다. CapCut의 타임라인 UX를 참조한다.

#### L2. 실시간 합성 미리보기

Direct 탭에서 현재 씬의 이미지가 실제 영상 프레임에 어떻게 배치되는지(Scene Text 위치, Full/Post 레이아웃)를 미리 보여준다. 렌더 전에 결과물을 예측할 수 있게 한다.

#### L3. 인터랙티브 온보딩 투어

첫 방문 시 5-6단계의 가이드 투어를 제공한다. 각 단계에서 해당 UI 요소를 하이라이트하고, 다음 단계로의 전환을 유도한다. 스킵 가능.

#### L4. AI 어시스턴트 챗

편집 중 막히는 부분에서 "도움이 필요하세요?" 플로팅 버튼을 통해 상황 인식형 도움말을 제공한다. 현재 Prompt Helper Sidebar의 확장 개념이다.

---

## 5. 개선 우선순위 매트릭스

| 개선안 | 영향도 | 구현 난이도 | 우선순위 |
|--------|--------|-----------|---------|
| S1. 프로젝트 온보딩 유도 | 높음 | 낮음 | **즉시** |
| S2. PipelineStatusDots 라벨 | 중간 | 낮음 | **즉시** |
| S3. 우측 패널 탭 이름 변경 | 중간 | 낮음 | **즉시** |
| S4. 전문 용어 Tooltip | 높음 | 낮음 | **1주 내** |
| S5. Quick/Full 모드 설명 | 중간 | 낮음 | **1주 내** |
| M1. Zero-config 빠른 시작 | 매우 높음 | 중간 | **2주 내** |
| M2. SceneCard 점진적 공개 | 높음 | 중간 | **3주 내** |
| M3. Quick Render 프리셋 | 중간 | 중간 | **3주 내** |
| M4. 가이드 배너 시스템 | 높음 | 낮음 | **2주 내** |
| L1. 타임라인 뷰 | 높음 | 높음 | 1-2개월 |
| L2. 합성 미리보기 | 중간 | 높음 | 1-2개월 |
| L3. 온보딩 투어 | 중간 | 중간 | 1-2개월 |
| L4. AI 어시스턴트 | 낮음 | 높음 | 2개월+ |

---

## 6. Frontend Dev 핸드오프 체크리스트

### S1-S5 (단기 개선) 구현 시 참고사항

**컴포넌트 구조**:
- 신규 컴포넌트 불필요. 기존 컴포넌트 내부 수정으로 충분.
- S4의 Tooltip은 이미 존재하는 `Tooltip` 컴포넌트(`/home/tomo/Workspace/shorts-producer/frontend/app/components/ui/`) 재사용.

**상태 관리**:
- 추가 상태 불필요. 기존 Zustand 스토어로 충분.

**반응형**:
- S2(PipelineStatusDots 라벨): 768px 이하에서는 라벨을 숨기고 dot만 표시.

**접근성**:
- S4(Tooltip): `aria-describedby`로 도움말 텍스트 연결.
- S1(온보딩 카드): 포커스 가능한 카드 + 키보드로 버튼 접근 가능.

**i18n**:
- 도움말 텍스트는 한국어 우선 (현재 프로젝트의 대상 사용자 기준).
- 버튼 라벨과 탭 이름은 영어 유지 (기존 패턴).

---

*이 문서는 코드베이스 분석에 기반한 초기 제안이며, 실제 사용자 테스트와 피드백을 통해 반복 개선이 필요합니다.*
