# SP-074 상세 설계: Frontend 하드코딩 SSOT 전환

## 설계 요약

| DoD | 대상 | 조치 | 변경 파일 |
|-----|------|------|----------|
| A-1 | EMOTION_PRESETS | /presets 응답 확장 | Backend 3 + Frontend 1 |
| A-2 | BGM_MOOD_PRESETS | /presets 응답 확장 | (A-1과 공유) |
| A-3 | IP_ADAPTER_MODELS | 기존 API 활용 | Frontend 1 |
| A-4 | CATEGORY_DESCRIPTIONS | config.py + tags API | Backend 2 + Frontend 1 |
| A-5 | OVERLAY_STYLES | /presets 응답 + Backend 불일치 해소 | Backend 2 + Frontend 1 |
| A-6 | AUTO_RUN_STEPS | 정당성 문서화 (Frontend 유지) | 0 |
| A-7 | COLUMN_ORDER | 정당성 문서화 (Frontend 유지) | 0 |
| B-1 | CLOTHING_PRESETS 등 B군 | 판단 기록 | 0 |
| FIX-1 | preflight.ts stepOrder | 버그 수정 | Frontend 1 |

**변경 파일 총 8개** (Backend 4 + Frontend 4)

---

## DoD-A1/A2: EMOTION_PRESETS + BGM_MOOD_PRESETS → /presets 응답

### 구현 방법

**Backend:**
- `config.py`에 `EMOTION_PRESETS`, `BGM_MOOD_PRESETS` 상수 정의 (기존 `TONE_METADATA` 패턴)
- `schemas.py`에 `EmotionPresetOption`, `BgmMoodPresetOption` Pydantic 모델 추가
- `PresetListResponse`에 `emotion_presets: list[EmotionPresetOption]`, `bgm_mood_presets: list[BgmMoodPresetOption]` 필드 추가
- `services/presets.py` → `build_preset_response()`에서 config.py 상수를 응답에 포함

```python
# config.py
EMOTION_PRESETS = [
    {"id": "excited", "label": "밝게", "emotion": "excited"},
    {"id": "calm", "label": "차분", "emotion": "calm"},
    {"id": "tense", "label": "긴장", "emotion": "tense"},
    {"id": "nostalgic", "label": "감성", "emotion": "nostalgic"},
]

BGM_MOOD_PRESETS = [
    {"id": "upbeat", "label": "경쾌", "mood": "upbeat", "prompt": "bright upbeat cheerful background music"},
    {"id": "calm", "label": "잔잔", "mood": "calm", "prompt": "calm peaceful relaxing ambient music"},
    {"id": "tense", "label": "긴박", "mood": "tense", "prompt": "tense dramatic suspenseful cinematic music"},
    {"id": "romantic", "label": "로맨틱", "mood": "romantic", "prompt": "romantic warm emotional piano background music"},
]
```

```python
# schemas.py
class EmotionPresetOption(BaseModel):
    id: str
    label: str
    emotion: str

class BgmMoodPresetOption(BaseModel):
    id: str
    label: str
    mood: str
    prompt: str
```

**Frontend:**
- `DirectorControlPanel.tsx`에서 하드코딩된 `EMOTION_PRESETS`, `BGM_MOOD_PRESETS` 제거
- `/presets` 응답에서 받은 데이터를 store (또는 props)로 전달
- `useStudioInitialization.ts`에서 이미 `/presets` 호출 중 → 응답의 새 필드를 store에 저장

### 동작 정의
- Before: `DirectorControlPanel.tsx`에 4+4종 하드코딩 → Backend 변경 시 Frontend 배포 필요
- After: `/presets` 응답에서 동적 로드 → Backend `config.py`만 수정하면 반영

### 엣지 케이스
- `/presets` 응답 실패 시: store의 초기값(빈 배열)으로 버튼 미표시 — 기능 장애 아닌 graceful degradation
- `emotion` 값은 Backend `EMOTION_VOCAB`(30종)의 서브셋 — 주석 명시

### 영향 범위
- `DirectorControlPanel.tsx` 내부에서만 사용 (다른 파일 import 없음) → 영향 최소

### 테스트 전략
- Backend: `GET /presets` 응답에 `emotion_presets`, `bgm_mood_presets` 필드 존재 검증
- Frontend: DirectorControlPanel 렌더 → emotion/bgm 버튼 표시 검증

### Out of Scope
- `EMOTION_VOCAB` 전체를 /presets로 내보내지 않음 (UI 프리셋 4종만)
- DirectorControlPanel의 다른 로직 변경 없음

---

## DoD-A3: IP_ADAPTER_MODELS → 기존 API 활용

### 구현 방법
- `CharacterDetailSections.tsx`에서 하드코딩 `["clip_face", "clip"]` 제거
- 기존 `GET /api/v1/controlnet/ip-adapter/status` 응답의 `supported_models` 필드 사용
- 캐릭터 상세 페이지 진입 시 호출 or store 캐싱

### 동작 정의
- Before: Frontend에 2종 하드코딩 → SD 환경 변경 시 불일치
- After: Backend `IP_ADAPTER_MODELS` dict에서 동적 로드

### 엣지 케이스
- API 실패 시: fallback으로 `["clip"]` 사용 (DEFAULT_IP_ADAPTER_MODEL)

### 영향 범위
- `CharacterDetailSections.tsx` 내부만 (다른 파일 import 없음)

### 테스트 전략
- IpAdapterSection 렌더 → 모델 버튼이 API 응답 기반으로 표시되는지 검증

### Out of Scope
- IP-Adapter 로직 자체 변경 없음

---

## DoD-A4: CATEGORY_DESCRIPTIONS → config.py + tags API

### 구현 방법

**Backend:**
- `config.py`에 `TAG_GROUP_DESCRIPTIONS: dict[str, str]` 정의 (15종)
- `routers/tags.py`의 `GET /tags/groups` 응답에 `description` 필드 추가
- `TagGroupItem` 스키마에 `description: str | None` 추가

```python
# config.py
TAG_GROUP_DESCRIPTIONS = {
    "quality": "품질 (masterpiece, best_quality)",
    "subject": "대상 (1girl, 1boy, solo)",
    "identity": "신원/캐릭터 (LoRA 트리거)",
    "hair_color": "머리 색 (blue_hair, blonde)",
    # ... 15종
}
```

**Frontend:**
- `constants/index.ts`에서 `CATEGORY_DESCRIPTIONS` 제거
- tags API 응답에서 `description` 사용

### 동작 정의
- Before: Frontend에 15종 한국어 설명 하드코딩
- After: Backend `config.py` SSOT → tags API 응답으로 제공

### 엣지 케이스
- 새 tag group 추가 시 config.py에 description 미등록 → `None` 반환 (UI에서 빈 값 허용)

### 영향 범위
- `CATEGORY_DESCRIPTIONS` 사용처 확인 후 import 교체

### 테스트 전략
- `GET /tags/groups` 응답에 `description` 필드 포함 검증
- description이 없는 group은 `None` 반환 검증

### Out of Scope
- DB에 description 컬럼 추가하지 않음 (config.py 상수로 충분)

---

## DoD-A5: OVERLAY_STYLES → /presets + Backend 불일치 해소

### 구현 방법

**Backend:**
- `config.py`에 `OVERLAY_STYLES` 상수 정의 (Backend `rendering.py`의 `known_styles` 3종과 통일)
- `rendering.py`의 `known_styles` 하드코딩 → `config.py` 참조로 변경
- `PresetListResponse`에 `overlay_styles: list[IdLabelOption]` 추가

```python
# config.py
OVERLAY_STYLES = [
    {"id": "overlay_minimal.png", "label": "Minimal"},
    {"id": "overlay_clean.png", "label": "Clean"},
    {"id": "overlay_bold.png", "label": "Bold"},
]
```

**Frontend:**
- `constants/index.ts`에서 `OVERLAY_STYLES` 제거
- `/presets` 응답에서 소비

### 동작 정의
- Before: Frontend 1종, Backend 3종 — **불일치 상태**
- After: config.py SSOT 3종 → 양쪽 동일

### 엣지 케이스
- 오버레이 PNG 파일이 실제로 존재하는지 검증은 렌더링 시점에서 수행 (기존 동작 유지)

### 영향 범위
- `rendering.py` 내 `known_styles` 참조 변경

### 테스트 전략
- `GET /presets` 응답에 `overlay_styles` 3종 포함 검증
- `rendering.py`가 config.py 상수를 참조하는지 검증

### Out of Scope
- 오버레이 에셋 파일 자체 추가/삭제 없음

---

## DoD-A6: AUTO_RUN_STEPS — 정당성 문서화 (Frontend 유지)

### 판단 근거
- 파이프라인 단계(stage→images→tts→render)는 Backend 코드 구조에 강결합
- Frontend 7개 파일에서 step ID 기반 로직 수행 (실행 순서, 진행률 계산, resume)
- `AutoRunStepId` 타입이 리터럴 유니온으로 정의 → API 동적 로드 시 타입 안전성 상실
- 단계가 변경되려면 아키텍처 자체가 바뀌어야 함 → 동적 변경 시나리오 비현실적
- 7개 파일 리팩토링 대비 실익 없음

### 조치
- `constants/index.ts`의 `AUTO_RUN_STEPS` 위에 정당성 주석 추가:
```typescript
/**
 * 파이프라인 실행 단계 (Frontend 유지 정당성: SP-074)
 * - step ID에 AutoRunStepId 타입 + autopilot 로직이 강결합
 * - 단계 변경 = 아키텍처 변경이므로 동적 로드 불필요
 * - Backend 대응: services/agent/nodes/ 노드 구조
 */
```

## DoD-A7: COLUMN_ORDER — 정당성 문서화 (Frontend 유지)

### 판단 근거
- 칸반 상태는 Backend `_derive_kanban_status()`가 계산하는 파생 값
- Frontend의 `COLUMN_ORDER`는 **UI 컬럼 표시 순서** — 프레젠테이션 관심사
- 상태 추가 가능성 극히 낮음 (draft/in_prod/rendered/published가 영상 라이프사이클 전체)

### 조치
- `useStudioKanban.ts`의 `COLUMN_ORDER` 위에 정당성 주석 추가

---

## DoD-B1: B군 판단 기록

| 상수 | 판단 | 후속 |
|------|------|------|
| `CLOTHING_PRESETS` | 도메인 데이터이나 현재 Frontend 유지 | Tag Intelligence 태스크에서 DB 기반 추천으로 전환 |
| `EDIT_PRESETS` | UX 편의 텍스트 — Frontend 유지 | 변경 불필요 |
| `EXAMPLES` (GeminiEditModal) | UX 편의 텍스트 — Frontend 유지 | 변경 불필요 |
| `GLOSSARY` | UI 도움말 텍스트 — Frontend 유지 | 변경 불필요 |

---

## DoD-FIX1: preflight.ts stepOrder 하드코딩 버그

### 구현 방법
- `preflight.ts:218`의 `const stepOrder: AutoRunStepId[] = ["stage", "images", "tts", "render"]` 제거
- `AUTO_RUN_STEPS`에서 파생: `const stepOrder = AUTO_RUN_STEPS.map(s => s.id)`

### 동작 정의
- Before: `AUTO_RUN_STEPS`와 별도로 하드코딩 → 불일치 위험
- After: 단일 소스에서 파생

### 테스트 전략
- preflight 관련 기존 테스트가 통과하는지 확인

---

## 변경 파일 요약

### Backend (4개)
| 파일 | 변경 |
|------|------|
| `config.py` | `EMOTION_PRESETS`, `BGM_MOOD_PRESETS`, `TAG_GROUP_DESCRIPTIONS`, `OVERLAY_STYLES` 상수 추가 |
| `schemas.py` | `EmotionPresetOption`, `BgmMoodPresetOption`, `IdLabelOption` 스키마 + `PresetListResponse` 확장 |
| `services/presets.py` | `build_preset_response()`에 신규 필드 포함 |
| `routers/tags.py` | `GET /tags/groups` 응답에 `description` 필드 추가 |

### Frontend (4개)
| 파일 | 변경 |
|------|------|
| `constants/index.ts` | `CATEGORY_DESCRIPTIONS`, `OVERLAY_STYLES` 제거. `AUTO_RUN_STEPS` 정당성 주석 추가 |
| `components/studio/DirectorControlPanel.tsx` | 하드코딩 제거 → /presets 응답 소비 |
| `(service)/library/characters/[id]/CharacterDetailSections.tsx` | 하드코딩 제거 → /ip-adapter/status API 소비 |
| `utils/preflight.ts` | stepOrder 하드코딩 → `AUTO_RUN_STEPS`에서 파생 |

### 변경 없음 (정당성 문서화)
- `useStudioKanban.ts` — 주석만 추가
- `rendering.py` — `known_styles` → config.py 참조로 교체 (Backend 5번째 파일로 카운트 가능하나 1줄 변경)

---

## 에이전트 설계 리뷰 결과

| 리뷰어 | 판정 | 주요 피드백 | 반영 |
|--------|------|------------|------|
| Frontend Dev | WARNING → 반영 완료 | AUTO_RUN_STEPS/COLUMN_ORDER 전환 ROI 낮음, OVERLAY_STYLES 불일치 발견, preflight.ts 버그 | 정당성 문서화로 전환, 불일치 해소 추가, 버그 수정 추가 |
| Backend Dev | PASS | /presets 확장 적절, Pydantic 스키마 필수, config.py 패턴 일관 | 스키마 설계 반영 |
| Tech Lead | WARNING → 반영 완료 | 전체 /presets 투입 말고 성격별 분리, CLOTHING_PRESETS 재검토 | 4건만 전환 + 3건 문서화로 축소, B군 판단 기록 |
