# Shorts Factory Master Roadmap (Strategic Fidelity Guard)

이 로드맵은 **안정성 → 리팩토링 → 안정성 → 신규 개발** 사이클을 따릅니다.
리팩토링 및 기능 추가 시 **영상 품질의 100% 일관성(Zero Variance)**을 유지하는 것을 최우선 목표로 합니다.

---

## 📦 Phase 1-4: Foundation & Refactoring - **ARCHIVED**

완료된 주요 성과:
- **Phase 1**: 기본 기능 구현 (FastAPI + Next.js + FFmpeg + WD14/Gemini 검증)
- **Phase 2**: VRT 안정성 기반 구축 (Golden Master + SSIM 95% 검증)
- **Phase 3**: Backend/Frontend 리팩토링
  - Backend: `logic.py` 2,300줄 → 279줄 (88% 감소), 8개 서비스 모듈 추출
  - Frontend: `page.tsx` 4,222줄 → 1,832줄 (57% 감소), 20개 컴포넌트 추출
- **Phase 4**: 안정성 검증 완료 (VRT 36/36 통과, PRD DoD 4개 항목 충족)

> 상세 이력: `git log --oneline docs/ROADMAP.md` 참조

---

## 🚀 Phase 5: 신규 개발 (High-End Production)
검증된 안정적인 기반 위에서 새로운 기능을 추가합니다.

### 5-1. 운영 효율화
| 작업 | 설명 | 상태 |
|------|------|------|
| Resume/Checkpoint | 중단된 작업 이어하기 | [x] |
| Storage Cleanup | outputs/ 자동 정리 로직 | [x] |
| Project DB (SQLite) | 프로젝트 설정 및 히스토리 관리 | [ ] |

### 5-2. 영상 품질 강화
| 작업 | 설명 | 상태 |
|------|------|------|
| Pixel-based Subtitle Wrapping | 폰트 기반 자막 줄바꿈 및 동적 크기 조절 | [x] |
| Professional Audio Ducking | 내레이션-BGM 볼륨 자동 조절 (sidechaincompress) | [x] |
| Ken Burns Effect | 정지 이미지에 줌/팬 효과 | [ ] |
| Character Consistency | → Phase 6 (LoRA 기반) → Phase 7 (IP-Adapter) | [-] |

### 5-3. 콘텐츠 확장
| 작업 | 설명 | 상태 |
|------|------|------|
| Preset System | 구조별 템플릿 및 샘플 토픽 시스템 | [x] |
| Sample Topics UI | Structure별 샘플 토픽 선택 UI | [x] |
| Japanese Language Course | 일본어 강좌 전용 템플릿 | [x] |
| Math Lesson Course | 초/중/고 수학 공식 강좌 템플릿 | [x] |

### 5-4. 확장 기능 (v1.x Backlog)
| 작업 | 설명 | 상태 |
|------|------|------|
| VEO Clip | Video Generation 통합 | [ ] |
| 정량적 품질 지표 | Match Rate 자동화 | [ ] |

### 5-5. UI/UX 개선
| 작업 | 설명 | 상태 |
|------|------|------|
| SetupPanel 제거 | 간소화 진입점 제거, Custom Start로 통합 | [x] |
| SD 파라미터 Advanced 이동 | steps, cfg_scale 등 고급 설정화 | [x] |
| 간소화 진입점 재설계 | Phase 6 완료 후 Quick Start 재정의 | [ ] |

---

## 🎭 Phase 6: Character & Prompt System (v2.0)
다중 캐릭터 지원 및 프롬프트 빌더 시스템 구축.

**현재 사용 환경**:
- **Model**: `animagine-xl.safetensors` (SDXL 애니메)
- **LoRA**: `eureka_v9` (캐릭터), `chibi-laugh` (스타일)
- **Negative Embeddings**: `verybadimagenegative_v1.3`, `easynegative`

**의존성 구조**:
```
keywords.json v2.0 구조 개편 → DB 마이그레이션
        ↓
Character Builder → Style Profile → Multi-Character
        ↓
Scene Builder → Tag Autocomplete
        ↓
Civitai 연동, Analytics (고급 기능)
```

### 6-1. Data Foundation (🔴 필수 선행)
| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 0 | DB 스키마 설정 | PostgreSQL + SQLAlchemy + Alembic | [x] |
| 1 | keywords.json v2.0 구조 설계 | 아래 스펙 참조 | [x] |
| 2 | 기존 데이터 마이그레이션 | v1 → v2 변환 + 신규 태그 추가 | [x] |
| 3 | Danbooru Identity 태그 수집 | hair_color, eye_color, hair_style | [x] |
| 4 | Backend CRUD API | /tags, /loras, /characters 엔드포인트 | [x] |

#### keywords.json v2.0 스펙

**SD 프롬프트 권장 순서** (앞쪽 태그가 더 중요):
| Priority | Category | 설명 | 고정/가변 |
|----------|----------|------|-----------|
| 1 | Quality | masterpiece, best quality | Meta |
| 2 | Subject | 1girl, solo | Character |
| 3 | Identity | hair_color, eye_color, hair_style | Character 고정 |
| 4 | Clothing | outfit, accessories | Character 고정 |
| 5 | Pose/Camera | action, expression, shot_type, angle | Scene 가변 |
| 6 | Environment | location, time, weather, lighting | Scene 가변 |
| 7 | Style | anime style (보통 모델/LoRA가 처리) | Meta |
| 99 | LoRA | `<lora:name:weight>` | 항상 마지막 |

**구조 개요**:
```json
{
  "version": "2.0",
  "prompt_order": ["quality", "subject", "identity", "clothing", "pose", "camera", "environment", "mood", "style", "lora"],
  "character": {
    "subject": { "priority": 2, "tags": ["1girl", "1boy", "solo", ...] },
    "identity": {
      "priority": 3,
      "groups": {
        "hair_color": { "exclusive": true, "tags": ["black hair", "blonde hair", ...] },
        "eye_color": { "exclusive": true, "tags": ["blue eyes", "brown eyes", ...] },
        "hair_style": { "tags": ["long hair", "short hair", "ponytail", ...] }
      }
    },
    "clothing": { "priority": 4, "groups": { "outfit": {...}, "accessories": {...} } }
  },
  "scene": {
    "pose": { "priority": 5, "groups": { "action": {...}, "expression": {...}, "gaze": {...} } },
    "camera": { "priority": 5, "groups": { "shot_type": {...}, "angle": {...} } },
    "environment": { "priority": 6, "groups": { "location": {...}, "time": {...}, "weather": {...}, "lighting": {...} } },
    "mood": { "priority": 6, "tags": [...] }
  },
  "meta": {
    "quality": { "priority": 1, "tags": ["masterpiece", "best quality", ...] },
    "style": { "priority": 7, "tags": ["anime style", ...] }
  },
  "lora": [
    {
      "name": "eureka_v9",
      "display_name": "Eureka",
      "trigger_words": ["eureka"],
      "default_weight": 1.0,
      "weight_range": [0.5, 1.5],
      "base_models": ["animagine-xl"],
      "character_defaults": { "hair_color": "aqua hair", "eye_color": "purple eyes", "hair_style": "short hair" },
      "recommended_tags": ["hairclip", "glasses"],
      "recommended_negative": "verybadimagenegative_v1.3"
    },
    {
      "name": "chibi-laugh",
      "display_name": "Chibi Laugh",
      "trigger_words": ["chibi", "eyebrow", "laughing", "eyebrow down"],
      "default_weight": 0.6,
      "weight_range": [0.3, 0.8],
      "base_models": ["*"],
      "recommended_negative": "easynegative"
    }
  ],
  "embeddings": {
    "negative": [
      { "name": "verybadimagenegative_v1.3", "type": "quality" },
      { "name": "easynegative", "type": "quality" }
    ]
  },
  "rules": {
    "conflicts": [["long hair", "short hair", "medium hair"], ["day", "night"]],
    "requires": { "twintails": ["long hair"], "ponytail": ["long hair", "medium hair"] },
    "weight_defaults": { "hair_color": 1.0, "outfit": 1.2 }
  },
  "synonyms": {...},
  "ignore": [...],
  "_legacy_categories": {...}
}
```

**핵심 설계 원칙**:
- `priority`: 프롬프트 조합 시 자동 정렬 순서
- `exclusive`: true면 그룹 내 하나만 선택 (예: hair_color)
- `conflicts/requires`: 충돌 태그 경고, 의존성 자동 추가
- `lora[].character_defaults`: LoRA 선택 시 캐릭터 태그 자동 설정
- `_legacy_categories`: 하위 호환성 유지

### 6-2. Studio Integration (🔴 핵심)
**목표**: Character Preset 하나로 모든 설정을 통합 관리

| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 4 | Character Builder UI | 고정 아이덴티티 태그 선택 (priority 2-4), Manage/Style 탭 | [x] |
| 5 | ~~Style Profile~~ | ~~SD Model + Embedding 번들~~ → Character Preset으로 통합 | [x] |
| 6 | LoRA 메타데이터 관리 | Weight Range, 호환 모델, Trigger Words, Civitai 연동 | [x] |
| 7 | Character 선택 UI | Actor A에 캐릭터 프리셋 적용, 태그 자동 주입 | [x] |
| 8 | Character Multi-LoRA | 캐릭터당 여러 LoRA 조합 지원 (eureka + chibi) | [x] |
| 9 | Character Negative | 캐릭터별 검증된 recommended_negative 설정 | [x] |
| 10 | Insert Sample 제거 | Character Preset으로 대체, 하드코딩 제거 | [x] |
| **11** | **Style Profile UI 제거** | Reapply 버튼 제거, Character Preset으로 단순화 | [x] |

#### 설계 결정: Character Preset 통합 방식
**결정**: Style Profile과 Character를 분리하지 않고, Character Preset 하나로 통합

**이유**:
- "작동하는 코드" 최우선 - 단순 = 버그 적음
- Zero Variance - 검증된 조합만 사용
- UX 단순화 - 드롭다운 1개로 모든 설정

**Character Preset 구조**:
```
Character Preset (통합)
├── Identity Tags (1girl, aqua_hair, purple_eyes)
├── Clothing Tags (black shirt)
├── LoRAs[] (eureka_v9:1.0, chibi-laugh:0.6)
└── Recommended Negative (easynegative)
```

#### 적용 흐름
```
Character 선택 → Base Prompt (Identity + LoRA) + Base Negative (검증된 값)
                 드롭다운 1개로 모든 설정 완료
```

### 6-3. Multi-Character & Scene (🟡 확장)
| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 9 | Multi-Character 지원 | A, B, C... 다중 캐릭터 구조 | [ ] |
| 10 | Scene Builder UI | 장면별 가변 컨텍스트 태그 선택 (priority 5-6) | [ ] |
| 11 | Tag Autocomplete | Danbooru 스타일 태그 자동완성 | [ ] |
| 12 | Character Preview | 캐릭터 설정 시 미리보기 생성 | [ ] |

### 6-4. Advanced Features (🔵 고급)
| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 13 | Civitai 연동 | LoRA 메타데이터 자동 가져오기 (MCP 활용) | [x] |
| 14 | Visual Tag Browser | 태그별 예시 이미지 표시 | [ ] |
| 15 | Tag Usage Analytics | 사용 빈도, 성공/실패 패턴 추적 | [ ] |
| 16 | Prompt History | 성공한 프롬프트 저장/재사용 | [ ] |
| 17 | Feedback Loop | 사용자 태그 제안 시스템 | [ ] |
| 18 | Profile Export/Import | Style Profile 공유 | [ ] |

---

## 🔮 Phase 7: Advanced Consistency (IP-Adapter)
Phase 6의 LoRA 기반 시스템 안정화 후 진행.

**전제 조건**:
- ControlNet 확장 설치
- IP-Adapter 모델 (anime 전용)
- VRAM 8GB+

| 작업 | 설명 | 상태 |
|------|------|------|
| ControlNet 연동 | SD WebUI ControlNet API 통합 | [ ] |
| IP-Adapter 지원 | 참조 이미지 기반 캐릭터 일관성 | [ ] |
| LoRA + IP 조합 | LoRA 베이스 + IP-Adapter 포즈/표정 | [ ] |
| Reference Image Manager | 참조 이미지 관리 UI | [ ] |

---

## 📋 Development Cycle

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   안정성      │ ──▶ │   리팩토링    │ ──▶ │   안정성      │ ──▶ │   신규 개발   │
│   구축       │     │   (VRT 통과)  │     │   검증       │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                      │
                     ◀──────────────────────────────────────────────────
                                    (반복)
```

---

## 🤖 Agent Evolution Guidelines

현재 에이전트 구성이 충분하지 않은 시점을 정의합니다.

### Test Engineer Agent 추가 시점

**트리거 조건** (하나 이상 충족 시 추가 검토):
| 조건 | 설명 | 현재 상태 |
|------|------|----------|
| Unit Test 구축 | Backend/Frontend unit test 30개 이상 | ❌ 미구축 |
| E2E Test 구축 | Playwright E2E 시나리오 10개 이상 | ❌ 미구축 |
| CI/CD 도입 | GitHub Actions 테스트 파이프라인 | ❌ 미구축 |
| 테스트 복잡도 | 테스트 파일 총 1,000줄 초과 | ❌ 해당없음 |

**역할 정의** (추가 시):
- 테스트 코드 작성/유지보수
- 테스트 커버리지 관리 (목표: 80%+)
- CI/CD 파이프라인 테스트 설정
- 테스트 관련 commands 관리 (`/test`, `/coverage`)

**현재 대안**:
- VRT: `/vrt` command + qa-validator
- 이미지 품질: qa-validator
- 수동 테스트: 일반 개발 과정에서 처리

### 기타 Agent 추가 고려

| Agent | 트리거 조건 | 현재 필요성 |
|-------|------------|------------|
| **DevOps Engineer** | Docker/K8s 배포, 모니터링 시스템 구축 시 | ❌ 불필요 |
| **Security Auditor** | 외부 사용자 접근, 인증 시스템 도입 시 | ❌ 불필요 |
| **Data Engineer** | 대용량 데이터 파이프라인, 분석 시스템 구축 시 | ❌ 불필요 |

### Claude Squad 도입 시점

**Claude Squad**: 여러 Claude Code 인스턴스를 병렬로 관리하는 도구 (tmux + git worktree 기반)

**트리거 조건** (하나 이상 충족 시 도입 검토):
| 조건 | 설명 | 현재 상태 |
|------|------|----------|
| 팀 확장 | 2명 이상 동시 개발 | ❌ 솔로 |
| 독립 작업 | Backend/Frontend 완전 분리 작업 필요 | ❌ 순차 진행 |
| 대규모 리팩토링 | 10+ 파일 동시 수정 필요 | ❌ 해당없음 |
| 긴급 핫픽스 | 메인 작업 중 별도 브랜치 작업 빈번 | ❌ 해당없음 |
| Phase 병렬화 | 의존성 없는 Phase 동시 진행 | ❌ 순차 의존성 |

**도입 시 이점**:
- 여러 작업 병렬 실행 (대기 시간 감소)
- git worktree로 브랜치 충돌 방지
- 백그라운드 자동 완료 (yolo 모드)

**현재 대안**:
- Sub Agents: 전문성 분리 (단일 세션 내)
- 순차 작업: 의존성 있는 Phase는 순서대로

**설치** (도입 시):
```bash
brew install claude-squad  # 명령어: cs
```

**참조**: https://github.com/smtg-ai/claude-squad

---

**Core Mandate**: "No changes in output without explicit intention."
(의도하지 않은 결과물의 변화는 허용하지 않는다.)

**Latest Status**: 2026-01-24
- **Phase 6-1 완료**: PostgreSQL + SQLAlchemy + Alembic, 262개 태그 마이그레이션
- **Phase 6-2 완료**: Studio Integration 전체 완료
  - Style Profile 연동 (SD Model, Quality prompts)
  - Character 선택 UI (드롭다운 → 프롬프트 자동 적용)
  - Multi-LoRA 지원 (eureka + chibi 조합)
  - recommended_negative (캐릭터별 검증된 네거티브)
  - Insert Sample 제거 (Character Preset으로 대체)
- **등록된 LoRA**: eureka_v9, chibi-laugh, blindbox_v1_mix
- **등록된 프리셋**: Eureka, Eureka Chibi, Eureka Blindbox, Chibi Style, Blindbox Style
- **다음 작업**: Phase 6-3 Multi-Character & Scene
- Storage Cleanup 기능 구현 완료 (`/storage/stats`, `/storage/cleanup` API)
- Pixel-based Subtitle Wrapping 구현 완료 (폰트 기반 줄바꿈, 균형 맞추기, 동적 폰트 크기 조절)
- Preset System 구현 완료 (`/presets` API, 9개 프리셋)
- 일본어 강좌 및 수학 공식 강좌 템플릿 추가
- Frontend: Structure 선택 메뉴 확장 (7개 옵션) + 샘플 토픽 선택 UI 추가
- VRT Golden Master 업데이트 완료 (36/36 테스트 통과)
- Audio Ducking 구현 완료 (FFmpeg sidechaincompress, BGM Volume 조절 UI)
- **Phase 6 로드맵 재조정**: Data → **Integration** → Multi-Character → Scene 순서
- **SetupPanel 제거**: 간소화 진입점 제거, Custom Start (Working Mode)로 직접 진입
- **SD 파라미터 Advanced 이동**: Steps, CFG, Sampler 등 기본 숨김, 토글로 펼침
- **VEO "Coming Soon"**: 비활성화 + 라벨 추가
- **Character Consistency 전략 수립**: LoRA 기반 (Phase 6) → IP-Adapter (Phase 7) 단계적 접근
- **Phase 7 추가**: IP-Adapter 기반 Advanced Consistency
- **keywords.json v2.0 스펙 정의**: SD 프롬프트 최적화 구조 설계
  - Priority 기반 태그 정렬 (Quality → Subject → Identity → Clothing → Pose → Environment → LoRA)
  - Character/Scene 태그 분리, exclusive 그룹, conflicts/requires 규칙
  - LoRA 메타데이터 (trigger_words, weight_range, character_defaults, recommended_negative)
  - 현재 환경 최적화: animagine-xl + eureka_v9 + chibi-laugh
