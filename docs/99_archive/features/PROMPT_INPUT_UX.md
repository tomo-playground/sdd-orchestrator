# Prompt Input UX 고도화

> 상태: 완료 (Phase A-0~A-3 + B, 02-23~02-24)
> 우선순위: P1
> 선행 관계: ✅ [Visual Tag Browser](VISUAL_TAG_BROWSER.md) 완료

---

## 용어 정의

### 프롬프트란

**프롬프트 = AI 모델이 인식하는 명령어**. 이 프로젝트에서는 4종의 AI 역할이 각각 다른 형식의 프롬프트를 소비한다.

### Target Role (프롬프트 소비자)

Target은 특정 모델이 아니라 **역할(Role)**로 정의한다. 구현체는 교체 가능.

| Target Role | 현재 구현체 | 프롬프트 형식 | 교체 후보 |
|-------------|-----------|-------------|----------|
| **이미지 생성 (Image Gen)** | Stable Diffusion | Danbooru 태그 조합 | SDXL, Imagen, DALL-E 3, Midjourney |
| **언어 추론 (LLM)** | Gemini | 자연어 지시문 | Claude, GPT, Llama |
| **음성 합성 (TTS)** | Qwen3-TTS | 음성 설계문 | ElevenLabs, OpenAI TTS |
| **음악 생성 (Music Gen)** | MusicGen | 음악 설계문 | Suno, Udio, Stable Audio |

### Prompt Format (현재: Tag-based)

현재 Image Gen(SD)은 **Danbooru 태그 조합 + weight 문법 `(tag:1.2)` + LoRA `<lora:name:0.8>`** 형식을 사용한다. 본 문서의 모든 Phase는 이 Tag-based Format 기준.

### 프롬프트 유형

| 유형 | Target Role | 정의 | 예시 |
|------|-------------|------|------|
| **이미지 프롬프트** | Image Gen | 태그들의 쉼표 구분 조합. 씬 단위로 사용자가 편집 | `brown_hair, smile, cowboy_shot` |
| **네거티브 프롬프트** | Image Gen | 이미지 생성 시 제외할 태그 조합 | `worst quality, blurry` |
| **조합 프롬프트** | Image Gen | 12-Layer Builder가 이미지 프롬프트 + 캐릭터 + 스타일을 병합한 **최종 결과** | `(best quality:1.2), 1girl, ...` |
| **스토리 지시문** | LLM | 영상 주제와 설명. Agentic Pipeline 입력 | "남자친구가 선물 받는 장면" |
| **장면 묘사** | LLM | 한글 시각 설명. LLM이 이미지 프롬프트로 변환 | "교실에서 웃고 있는 소녀" |
| **편집 지시문** | LLM | LLM에게 요청하는 자연어 수정 요청 | "밝게 웃으면서 정면 보기" |
| **음성 설계문** | TTS | 음색/감정/속도 지시 | "따뜻한 톤, 약간 느린 속도" |
| **음악 설계문** | Music Gen | 음악 생성 지시 | `"ambient lo-fi, soft piano"` |

### 보조 용어

| 용어 | 정의 |
|------|------|
| **태그 (Tag)** | Danbooru 형식의 개별 키워드 (`brown_hair`, `cowboy_shot`) |
| **구조화 태그 선택** | 사전 정의된 태그를 버튼/칩으로 선택하는 UI (context_tags, appearance) |

### 분류 체계

```
프롬프트 (AI가 인식하는 명령어)
│
├── Image Gen 프롬프트 (이미지 생성 모델 소비)
│   ├── 이미지 프롬프트 — 사용자 편집 입력 (태그 조합)
│   ├── 네거티브 프롬프트 — 제외 지시 (태그 조합)
│   ├── 구조화 태그 선택 — 버튼/칩 UI
│   └── 조합 프롬프트 — 12-Layer Builder 최종 출력
│
├── LLM 프롬프트 (언어 모델 소비)
│   ├── 스토리 지시문 — Agentic Pipeline 전체 구동
│   ├── 장면 묘사 — 한글 → LLM → 이미지 프롬프트 변환
│   └── 편집 지시문 — LLM이 기존 이미지 프롬프트 수정
│
├── TTS 프롬프트 (음성 합성 모델 소비)
│   └── 음성 설계문
│
└── Music Gen 프롬프트 (음악 생성 모델 소비)
    └── 음악 설계문
```

---

## 배경

사용자 입력 포인트가 **19곳** 존재하지만, 태그 자동완성(TagAutocomplete)이 적용된 곳은 **2곳뿐**. 나머지는 순수 textarea로, 사용자가 Danbooru 태그를 외워서 타이핑해야 한다.

더 근본적인 문제로, 사용자가 편집한 이미지 프롬프트와 **실제 Image Gen에 전달되는 조합 프롬프트** 사이에 갭이 있는데, 이 갭을 보여주지 않고 바로 실행한다.

---

## 쇼츠 생성 생애주기와 입력 출현 시점

```
① 사전 준비          ② 기획           ③ AI 생성        ④ 씬 편집         ⑤ 이미지 생성        ⑥ 렌더링
캐릭터/스타일 설정 → 스토리 지시문 → 파이프라인 자동 → 사용자 수정 → 조합 → Image Gen 전달 → 영상 조립
```

### ① 사전 준비 (캐릭터 + 스타일)

| 시점 | 입력 | 분류 | 입력자 | 미리보기 |
|------|------|------|--------|:---:|
| 캐릭터 외형 | `hair_color`, `eye_color` 등 | 구조화 태그 선택 | 사용자 | O (칩) |
| 캐릭터 커스텀 | `scene_positive_prompt` | 이미지 프롬프트 | 사용자 | X |
| 캐릭터 레퍼런스 | `reference_positive_prompt` | 이미지 프롬프트 | 사용자 | X |
| 스타일 기본값 | `default_positive/negative` | 이미지 프롬프트 | 사용자 | X |
| 음성 | `voice_design_prompt` | 음성 설계문 | 사용자 | 미리듣기만 |

> ① 단계의 이미지 프롬프트/태그는 **이후 모든 씬의 조합 프롬프트에 자동 주입**된다.

### ② 기획 (스토리보드 생성 요청)

| 시점 | 입력 | 분류 | 입력자 | 미리보기 |
|------|------|------|--------|:---:|
| Topic | "남자친구가 선물 받는 장면" | 스토리 지시문 | 사용자 | X |
| Description | "감동적인 표정 강조" | 스토리 지시문 | 사용자 | X |

### ③ AI 파이프라인 (자동 생성) — SSE 스트림

| 노드 | 생성물 | 분류 | Target Role | 사용자에게 보이나? |
|------|--------|------|------------|:---:|
| Research | research_brief | (내부) | LLM | X |
| Critic | 3개 컨셉 | (내부) | LLM | O (선택 UI) |
| Writer | `script` (대사) | (내부) | LLM | O (씬 카드) |
| **Cinematographer** | **씬별 이미지 프롬프트** | **이미지 프롬프트** | **LLM** | **부분적** |
| TTS Designer | 씬별 음성 설계문 | 음성 설계문 | LLM | X |
| Sound Designer | 음악 설계문 | 음악 설계문 | LLM | O (BgmSection) |

> **핵심 갭**: Cinematographer가 생성한 이미지 프롬프트는 보이지만, 12-Layer 조합 후 **실제 Image Gen에 전달되는 조합 프롬프트**는 보이지 않는다.

### ④ 씬 편집 (사용자 수정)

| 시점 | 입력 | 분류 | 미리보기 |
|------|------|------|:---:|
| image_prompt (EN) 수정 | 태그 직접 편집 | 이미지 프롬프트 | 토큰 수만 |
| image_prompt_ko 수정 | 한글 시각 설명 | 장면 묘사 | X |
| context_tags 선택 | expression, pose, camera | 구조화 태그 선택 | O (칩) |
| clothing 오버라이드 | 의상 태그 변경 | 이미지 프롬프트 | X |
| character_actions | 액션 태그 추가 | 이미지 프롬프트 | X |
| negative_prompt 수정 | 네거티브 태그 | 네거티브 프롬프트 | 소스 칩만 |
| LLM 편집 | "정면 보게 바꿔줘" | 편집 지시문 | X |

### ⑤ 이미지 생성 (조합 → Image Gen 전달)

| 시점 | 데이터 | 분류 | 미리보기 |
|------|--------|------|:---:|
| **12-Layer 조합** | 이미지 프롬프트 + 캐릭터 + 스타일 + context 병합 | **조합 프롬프트** | **X** |
| **Image Gen 전달** | `(best quality:1.2), 1girl, brown_hair, ...` | 조합 프롬프트 | **X** |
| **Negative 전달** | `worst quality, low quality, ...` | 네거티브 프롬프트 | **X** |

> **가장 큰 문제**: ④에서 편집한 이미지 프롬프트와 ⑤에서 Image Gen에 전달되는 조합 프롬프트가 다를 수 있는데, 조합 프롬프트를 보여주지 않는다.

### ⑥ 렌더링 (영상 조립)

| 시점 | 데이터 | 분류 | 미리보기 |
|------|--------|------|:---:|
| script → Scene Text 오버레이 | 대사 텍스트 | (내부) | O |
| voice_design_prompt → TTS Role | 음성 스타일 | 음성 설계문 | X |
| bgm_prompt → Music Gen Role | BGM 생성 | 음악 설계문 | O (Preview) |

### 미리보기 갭 요약

```
① 사전준비: 이미지 프롬프트 설정     → [조합 프롬프트에 어떻게 반영되는지 안 보임]
② 기획:     스토리 지시문 입력       → [AI가 어떻게 해석했는지 안 보임]
③ AI 생성:  이미지 프롬프트 자동 생성 → [부분적으로 보임]
④ 씬 편집:  이미지 프롬프트 수정     → [수정 결과의 조합 프롬프트 안 보임] ← 핵심 갭
⑤ 이미지:   12-Layer 조합           → [조합 프롬프트 안 보임] ← 가장 큰 갭
⑥ 렌더링:   음성/음악 설계문        → [음악만 Preview 가능]
```

---

## 현재 입력 포인트 전수 맵

### 태그 기반 (10곳) — TagAutocomplete + 조합 미리보기 대상

| # | 영역 | 컴포넌트 | 분류 | AutoComplete | 조합 미리보기 |
|---|------|---------|------|:---:|:---:|
| S1 | Scene | ScenePromptFields (EN) | 이미지 프롬프트 | **O** | 부분적 |
| S3 | Scene | NegativePromptToggle | 네거티브 프롬프트 | X | X |
| S5 | Scene | SceneCharacterActions | 이미지 프롬프트 | X | X |
| S6 | Scene | SceneClothingModal | 이미지 프롬프트 | X | X |
| C2 | Character | PromptsStep — Base | 이미지 프롬프트 | X | X |
| C3 | Character | PromptsStep — Negative | 네거티브 프롬프트 | X | X |
| C4 | Character | PromptsStep — Ref Base | 이미지 프롬프트 | X | X |
| C5 | Character | PromptsStep — Ref Negative | 네거티브 프롬프트 | X | X |
| ST1 | Style | StyleProfileEditor — Positive | 이미지 프롬프트 | X | X |
| ST2 | Style | StyleProfileEditor — Negative | 네거티브 프롬프트 | X | X |

### 구조화 태그 선택 (2곳) — 이미 시각화

| # | 컴포넌트 | 분류 | 미리보기 |
|---|---------|------|:---:|
| S4 | SceneContextTags | 구조화 태그 선택 | O (칩) |
| C1 | AppearanceStep | 구조화 태그 선택 | O (칩 + Popular) |

### 자연어 기반 (3곳) — 변환 결과 미리보기 대상

| # | 컴포넌트 | 분류 | 미리보기 |
|---|---------|------|:---:|
| S2 | ScenePromptFields (KO) | 장면 묘사 | X |
| S7 | GeminiEditModal (씬) | 편집 지시문 | X |
| C6 | GeminiEditModal (캐릭터) | 편집 지시문 | X |

### 설계문 (4곳) — 도메인 특화

| # | 컴포넌트 | 분류 | 미리보기 |
|---|---------|------|:---:|
| V1 | VoicesPage | 음성 설계문 | 미리듣기 |
| M1 | Music Presets Page | 음악 설계문 | O (Preview) |
| M2 | BgmSection (Auto) | 음악 설계문 | O (Preview) |
| G1 | GeneratorPanel — Topic | 스토리 지시문 | SSE 결과 |

---

## 핵심 원칙: 미리보기 → 확인 → 실행

**모든 입력은 사용자에게 최종 결과를 보여준 후 실행해야 한다.**

| 분류 | 현재 | 목표 |
|------|------|------|
| **이미지 프롬프트** | 입력 → 12-Layer 조합 → 바로 생성 | 입력 → **조합 프롬프트 표시** → 확인 → 생성 |
| **장면 묘사** | 한글 → LLM 변환 → 자동 적용 | 한글 → 변환 → **변환 결과 diff** → 승인 → 적용 |
| **편집 지시문** | 지시 → LLM 처리 → 자동 적용 | 지시 → 처리 → **Before/After diff** → 승인 → 적용 |
| **구조화 태그** | 선택 → 저장 → 조합 결과 안 보임 | 선택 → **조합 프롬프트에 반영** 표시 |
| **음성 설계문** | 입력 → 바로 TTS 생성 | 입력 → **미리듣기** → 확인 → 저장 |
| **음악 설계문** | 비교적 양호 (Preview 있음) | 유지 |
| **스토리 지시문** | 비교적 양호 (SSE 결과 노출) | 유지 |

---

## 설계 원칙: Target Role

**프롬프트 개선은 특정 모델이 아니라 Target Role에 대해 설계한다.** 모델 교체 시 UI/미리보기 계층은 변경 없이 작동해야 한다.

| 원칙 | 설명 | 예시 |
|------|------|------|
| **Role 기반 인터페이스** | API와 UI는 모델명이 아닌 역할 단위로 설계 | `POST /prompt/compose` → Image Gen Role용 |
| **미리보기 계층 분리** | 미리보기 컴포넌트는 조합 결과만 표시, 모델 호출은 별도 | `ComposedPromptPreview`는 조합 결과 렌더링만 담당 |
| **검증 규칙 교체 가능** | 태그 검증 규칙은 Image Gen 구현체에 종속 | SD 교체 시 검증 규칙만 교체, UI 불변 |
| **설계문 포맷 유연성** | 음성/음악 설계문 형식은 TTS/Music Gen 변경에 따라 달라질 수 있음 | 설계문 입력 UI는 포맷 힌트만 변경 |

### 에러 처리

| 시나리오 | 처리 |
|---------|------|
| compose API 실패 | 마지막 성공 결과 유지 + 재시도 버튼 + 토스트 경고 |
| 태그 검증 API 실패 | 검증 배지를 "미검증" 상태로 표시. 생성은 차단하지 않음 |
| LLM 변환/편집 실패 | 원본 프롬프트 보존 + "다시 시도" 버튼 + 수동 입력 폴백 |

### 기타 Role 교체 시나리오

```
LLM 교체 (Gemini → Claude/GPT)
├── 변경: Agentic Pipeline 노드 내부 (호출 코드)
├── 변경: 장면 묘사 → 이미지 프롬프트 변환 품질
├── 불변: 변환 결과 diff UI
├── 불변: Before/After 미리보기
└── 불변: 편집 지시문 입력 UI

TTS 교체 (Qwen3-TTS → ElevenLabs)
├── 변경: 음성 설계문 포맷 힌트 (placeholder)
├── 변경: 미리듣기 API 엔드포인트
├── 불변: 음성 설계문 입력 UI
└── 불변: 미리듣기 → 확인 → 저장 플로우
```

---

## 목표

1. **미리보기 → 확인 → 실행** 원칙을 전체 입력에 적용
2. **Target Role** — 모델 교체 시 UI/미리보기 계층 불변
3. **TagAutocomplete 품질 개선** — 기존 2곳의 UX를 먼저 높인다
4. **TagAutocomplete 확산** — 태그 기반 입력 10곳에 확산
5. **태그 검증 확산** — 캐릭터/스타일 입력에도 검증 시스템 적용

---

## Phase A-0: 조합 프롬프트 미리보기

사용자가 편집한 이미지 프롬프트가 최종적으로 어떻게 조합되는지 보여준다.

> **Target Role 설계**: 기존 `POST /prompt/compose` 엔드포인트를 확장하여 레이어별 분해 정보(`layers`)를 응답에 추가한다. API 인터페이스와 UI 컴포넌트는 Image Gen 구현체에 의존하지 않는다.

### A-0-1. 조합 프롬프트 미리보기 (Image Gen용)

이미지 생성 전, 12-Layer Builder가 조합한 최종 결과를 보여주는 패널.

| 항목 | 설명 |
|------|------|
| 위치 | SceneCard 하단 또는 Generate 버튼 옆 |
| 내용 | 레이어별 태그 분해 + 조합 프롬프트 + 네거티브 프롬프트 |
| 트리거 | 입력 변경 시 자동 갱신 (디바운스) |
| API | `POST /prompt/compose` (기존 엔드포인트 확장, `layers` 필드 추가) |

```
[Quality]  masterpiece, best quality, highres
[Style]    anime_coloring, flat_color
[LoRA]     <lora:ghibli:0.8>
[Char]     1girl, brown_hair, blue_eyes
[Cloth]    school_uniform, white_shirt     ← 의상 오버라이드 반영
[Pose]     sitting, hands_on_lap
[Camera]   cowboy_shot, from_side
[Env]      classroom, window, sunlight
[Action]   looking_at_viewer, smile
[User]     (사용자 추가 태그)
───────────────────────────────
[조합 결과] masterpiece, best quality, ...  ← 실제 Image Gen 전달
[네거티브]  worst quality, low quality, ...
```

### A-0-2. 변환 결과 미리보기 (LLM 변환)

장면 묘사(한글) → 이미지 프롬프트(EN) 변환 결과를 자동 적용하지 않고 diff로 보여준다.

| 항목 | 설명 |
|------|------|
| 위치 | ScenePromptFields KO 하단 |
| 내용 | 한글 입력 → LLM이 변환한 이미지 프롬프트 표시 → 승인 버튼 |

> **Target Role 설계**: diff UI는 LLM 구현체(Gemini/Claude)에 무관하게 "변환 전 ↔ 변환 후"만 표시. LLM 교체 시 변환 품질만 달라지고 UI는 불변.

### A-0-3. 편집 결과 미리보기 (LLM 편집)

편집 지시문 처리 결과를 자동 적용하지 않고 Before/After diff로 보여준다.

| 항목 | 설명 |
|------|------|
| 위치 | GeminiEditModal 내부 |
| 내용 | 현재 이미지 프롬프트 vs LLM이 변경한 이미지 프롬프트 diff |
| 액션 | "적용" / "취소" 버튼 |

> **Target Role 설계**: 모달 이름은 `GeminiEditModal`이지만 (기존 코드 호환), 내부 API 호출은 LLM Role 인터페이스를 통한다. 향후 컴포넌트명 리팩토링 대상 (`LLMEditModal`).

### 수락 기준 (A-0)

| # | 기준 |
|---|------|
| 1 | 이미지 생성 전 조합 프롬프트(positive + negative) 확인 가능 |
| 2 | 장면 묘사 → 이미지 프롬프트 변환 결과를 승인 전까지 미적용 |
| 3 | 편집 지시문 결과를 Before/After diff로 표시 후 승인 |
| 4 | context_tags/clothing 변경 시 조합 미리보기에 즉시 반영 |

---

## Phase A-1: TagAutocomplete 품질 개선
현재 ScenePromptFields(S1, S2)에서만 사용 중인 TagAutocomplete의 핵심 문제 해결.

> **Target Role 설계**: TagAutocomplete는 현재 Danbooru 태그(Image Gen: SD 기준)에 특화. 향후 Image Gen이 변경되면 검색 소스(Danbooru → 새 태그 DB)와 검증 규칙만 교체하고, 자동완성 UI 컴포넌트 자체는 재사용한다. 이를 위해 태그 검색 API(`/tags/search`)는 Image Gen 구현체에 독립적인 인터페이스로 유지한다.

| # | 항목 | 현재 | 개선 | 심각도 |
|---|------|------|------|--------|
| 1 | API 디바운스 | 없음 (타이핑마다 즉시 호출) | 300ms 디바운스 적용 | 중간 |
| 2 | 한글 입력 | 정규식 영문만 | 유니코드 지원 추가 | 중간 |
| 3 | 인기도 표시 | 미표시 | `wd14_count` 드롭다운에 표시 | 중간 |
| 4 | 선택 후 구분자 | 쉼표 자동 추가 없음 | 선택 후 `, ` 자동 삽입 | 낮음 |
| 5 | 폐기 태그 표시 | 미표시 | `deprecated_reason` + 대체 태그 표시 | 낮음 |
| 6 | 검증 스키마 동기화 | Frontend-Backend 필드명 불일치 | 응답 스키마 통일 | 높음 |

### 검증 스키마 불일치 상세

```
Frontend 기대         Backend 실제 반환
─────────────        ─────────────
valid: string[]       (없음)
risky: string[]       risky_tags: string[]
unknown: string[]     unknown_in_db: string[]
total_tags: number    total: number
valid_count: number   (없음)
```

### 수락 기준 (A-1)

| # | 기준 |
|---|------|
| 1 | 300ms 디바운스로 불필요한 API 호출 90% 감소 |
| 2 | 한글 2자 이상 입력 시 자동완성 동작 |
| 3 | 드롭다운에 인기도(wd14_count) 표시 |
| 4 | 태그 선택 후 `, ` 자동 삽입 |
| 5 | 폐기된 태그 선택 시 대체 태그 안내 |
| 6 | Frontend TagValidationResult 타입과 Backend 응답 스키마 일치 |

---

## Phase A-2: TagAutocomplete 확산
태그 기반 입력 10곳 중 미적용 8곳에 TagAutocomplete 확산.

### Tier 1 — 빈번한 사용

| 대상 | 컴포넌트 | 분류 | 변경 |
|------|---------|------|------|
| S3 | NegativePromptToggle | 네거티브 프롬프트 | TagAutocomplete 교체 |
| S5 | SceneCharacterActions | 이미지 프롬프트 | TagAutocomplete 교체 |
| S6 | SceneClothingModal | 이미지 프롬프트 | TagAutocomplete 교체 |
| C2 | PromptsStep — Base | 이미지 프롬프트 | TagAutocomplete 교체 |
| C3 | PromptsStep — Negative | 네거티브 프롬프트 | TagAutocomplete 교체 |

### Tier 2 — 중간 빈도

| 대상 | 컴포넌트 | 분류 | 변경 |
|------|---------|------|------|
| C4 | PromptsStep — Ref Base | 이미지 프롬프트 | TagAutocomplete 교체 |
| C5 | PromptsStep — Ref Negative | 네거티브 프롬프트 | TagAutocomplete 교체 |
| ST1 | StyleProfileEditor — Positive | 이미지 프롬프트 | TagAutocomplete 교체 |
| ST2 | StyleProfileEditor — Negative | 네거티브 프롬프트 | TagAutocomplete 교체 |

### 적용 제외

| 대상 | 분류 | 사유 |
|------|------|------|
| S4 SceneContextTags | 구조화 태그 선택 | 이미 버튼 칩으로 완전 시각화 |
| C1 AppearanceStep | 구조화 태그 선택 | 이미 칩 선택 + 검색 UI 완비 |
| S7, C6 GeminiEditModal | 편집 지시문 | 자연어 (태그 아님) |
| V1 VoicesPage | 음성 설계문 | 자연어 (태그 아님) |
| G1 GeneratorPanel | 스토리 지시문 | 자연어 (태그 아님) |
| M1, M2 Music/BGM | 음악 설계문 | 자연어 (태그 아님) |

### 수락 기준 (A-2)

| # | 기준 |
|---|------|
| 1 | Tier 1 (5곳)에서 태그 자동완성 동작 |
| 2 | Tier 2 (4곳)에서 태그 자동완성 동작 |
| 3 | 기존 기능(프리셋 버튼, 디바운스 저장 등) 유지 |
| 4 | TagAutocomplete props로 rows, placeholder, debounce 커스터마이징 가능 |

---

## Phase A-3: 태그 검증 확산
현재 ScenePromptFields에만 적용된 태그 검증(TagValidationWarning + Auto-Replace)을 확산.

> **Target Role 설계**: 검증 규칙(위험 태그, 별칭, DB 존재 여부)은 Image Gen Role의 태그 체계에 종속된다. `useTagValidation` 훅은 검증 규칙을 외부 주입(Provider 또는 설정)으로 받도록 설계하여, Image Gen 교체 시 규칙 셋만 교체한다.

| 대상 | 검증 항목 |
|------|---------|
| C2, C3 캐릭터 Base/Negative | Alias 위험 태그 + DB 미존재 태그 경고 |
| C4, C5 캐릭터 Reference | 동일 |
| ST1, ST2 StyleProfile | 동일 |
| S3 Negative | Alias 위험 태그 경고 |
| S6 ClothingModal | DB 미존재 의상 태그 경고 |

### 수락 기준 (A-3)

| # | 기준 |
|---|------|
| 1 | 캐릭터 이미지 프롬프트 입력 시 위험 태그 경고 표시 |
| 2 | StyleProfile 이미지 프롬프트에서 위험 태그 자동 대체 가능 |
| 3 | Auto-Replace 버튼으로 일괄 수정 |
| 4 | 검증 로직 공통 훅(`useTagValidation`) 재사용 |

---

## Phase B: Visual Tag Browser (다음 단계)
> Phase A 완료 후 진행. 상세는 [VISUAL_TAG_BROWSER.md](VISUAL_TAG_BROWSER.md) 참조.

Phase A에서 개선된 TagAutocomplete 위에 시각적 태그 탐색 기능을 추가한다.

> **Target Role 설계**: 썸네일 소스(Danbooru API)는 현재 Image Gen(SD)의 태그 체계에 종속된다. Image Gen 교체 시 썸네일 소스도 교체가 필요하므로, 이미지 소스를 추상화(Provider 패턴)하여 설계한다.

| 항목 | 설명 |
|------|------|
| Tag Thumbnail | 태그별 대표 이미지 (Image Provider: Danbooru, 자체 생성 등) |
| Category Grid | 카테고리별 그리드 탐색 |
| Inline Preview | TagAutocomplete 드롭다운에 미니 썸네일 |
| Explorer Panel | 독립 태그 탐색 패널 (사이드바 또는 모달) |

---

## 구현 영향 범위

### 주요 변경 파일 요약

| 영역 | 파일 | 핵심 변경 |
|------|------|---------|
| 조합 로직 | `composition.py` | `compose()` 반환값에 레이어별 분해 정보 추가 |
| 입력 UI | `TagAutocomplete.tsx` | 디바운스, 한글, 인기도, 구분자, 폐기 태그 |
| 미리보기 | `ComposedPromptPreview.tsx` | 레이어별 태그 분해 + 조합 결과 표시 |
| 검증 | `/prompt/validate-tags` | 응답 스키마 통일 + `response_model` 추가 |
| AI 생성 | `pipeline/cinematographer` LangFuse 프롬프트 | Danbooru 태그 출력 (변경 없음) |

### Frontend

| 파일 | 변경 내용 |
|------|---------|
| `components/ui/TagAutocomplete.tsx` | 디바운스, 한글, 인기도, 구분자, 폐기 태그 |
| `components/prompt/ComposedPromptPreview.tsx` | 12-Layer 조합 미리보기 확장 (레이어별 분해 표시) |
| `components/storyboard/ScenePromptFields.tsx` | 조합 미리보기 연동 |
| `components/storyboard/NegativePromptToggle.tsx` | TagAutocomplete 적용 |
| `components/storyboard/SceneCharacterActions.tsx` | TagAutocomplete 적용 |
| `components/storyboard/SceneClothingModal.tsx` | TagAutocomplete 적용 |
| `components/storyboard/SceneGeminiModals.tsx` | Before/After diff 추가 |
| `(app)/characters/builder/steps/PromptsStep.tsx` | TagAutocomplete 적용 |
| `(app)/characters/[id]/CharacterDetailSections.tsx` | TagAutocomplete 적용 |
| `(app)/characters/[id]/GeminiEditModal.tsx` | Before/After diff 추가 |
| `(app)/characters/shared/PromptPair.tsx` | TagAutocomplete 적용 |
| `(app)/library/StyleProfileEditor.tsx` | TagAutocomplete 적용 |
| `components/prompt/TagValidationWarning.tsx` | TagValidationResult 타입 정의 수정 |
| `hooks/useTagValidation.ts` | 스키마 동기화 + 범용화 |
| `types/index.ts` | TagValidationResult 타입 수정 |

### Backend

| 파일 | 변경 내용 |
|------|---------|
| `routers/prompt.py` | validate-tags 응답 스키마 통일 + 기존 5개 엔드포인트 `response_model=` 추가 |
| `routers/prompt.py` | 기존 `/compose` 확장 — `layers` 응답 필드 추가 |
| `routers/tags.py` | 검색 응답에 wd14_count/deprecated 포함 확인 |
| `schemas.py` | ValidateTagsResponse 수정, ComposeResponse에 `layers` 필드 추가 |
| `services/prompt/composition.py` | `compose()` 반환값에 레이어별 분해 정보 추가 |

---

## 테스트 계획

| 범위 | 테스트 항목 | 예상 수 |
|------|-----------|--------|
| 조합 미리보기 | 12-Layer 조합 결과 표시, 실시간 갱신 | 6개 |
| 변환/편집 diff | Before/After 표시, 승인/취소 | 4개 |
| TagAutocomplete | 디바운스, 한글, 인기도, 구분자, 폐기 태그 | 8개 |
| 확산 적용 | 각 컴포넌트에서 자동완성 동작 확인 | 9개 |
| 검증 확산 | 캐릭터/스타일 태그 검증 동작 | 6개 |
| 스키마 동기화 | Frontend-Backend 응답 필드 일치 | 3개 |
| 후방 호환성 | 기존 ScenePromptFields 동작 유지 | 4개 |
| **합계** | | **~40개** |

---

## 작업 순서

```
Phase A-0 (조합 프롬프트 미리보기)    ← compose API 확장 + layers 응답
  → Phase A-1 (TagAutocomplete 품질)  ← 기존 입력 UX 개선
    → Phase A-2 (확산 적용)            ← 나머지 8곳 적용
      → Phase A-3 (검증 확산)          ← 검증 시스템 확산
        → Phase B (Visual Tag Browser) ← 시각적 태그 탐색
```

각 Phase는 독립 배포 가능. **A-0이 가장 높은 사용자 가치** — "내가 뭘 만드는지 알고 실행한다."
