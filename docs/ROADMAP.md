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
| Project DB (PostgreSQL) | 프로젝트 설정 및 히스토리 관리 (Phase 6-1 통합) | [x] |

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
- **Model**: `anythingV3_fp16.safetensors` (SD 1.5 애니메)
- **LoRA**: `eureka_v9`, `chibi-laugh`, `blindbox_v1_mix`, `mha_midoriya-10`
- **Negative Embeddings**: `verybadimagenegative_v1.3`, `easynegative`
- **Presets**: Eureka, Eureka Chibi, Eureka Blindbox, Chibi, Blindbox, Midoriya, Midoriya Chibi

### 6-1. Data Foundation - **COMPLETE**
| 작업 | 설명 | 상태 |
|------|------|------|
| DB 스키마 설정 | PostgreSQL + SQLAlchemy + Alembic | [x] |
| 태그 마이그레이션 | 262개 태그 (identity, clothing, scene, meta) | [x] |
| Backend CRUD API | /tags, /loras, /characters, /sd-models 엔드포인트 | [x] |

### 6-2. Studio Integration - **COMPLETE**
| 작업 | 설명 | 상태 |
|------|------|------|
| Character Preset UI | 드롭다운 → Identity + Clothing + LoRA + Negative 자동 적용 | [x] |
| Multi-LoRA 지원 | 캐릭터당 여러 LoRA 조합 (eureka + chibi) | [x] |
| Style Profile 통합 | Character Preset으로 단일화, UI 제거 | [x] |

**Character Preset 구조**:
```
Character Preset
├── Identity Tags (1girl, aqua_hair, purple_eyes, short_hair)
├── Clothing Tags (t-shirt, hairclip)
├── LoRAs[] (eureka_v9:1.0, chibi-laugh:0.6)
└── Recommended Negative (easynegative)
```

### 6-3. Multi-Character & Scene (🟡 확장)
| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 8 | Character Gender Field | Character 모델에 gender 추가, Actor gender 자동 동기화 | [x] |
| 8.1 | LoRA Gender Locked | LoRA에 gender_locked 메타데이터 추가 (female/male/null) | [x] |
| 8.2 | Gender 읽기전용 UI | Character Preset 선택 시 Gender 필드 잠금 | [x] |
| 8.3 | Style Preset 네이밍 | Chibi Style → Chibi, Blindbox Style → Blindbox | [x] |
| 8.4 | Male Style Presets | 1boy + 스타일 LoRA 품질 테스트 → 성별 구분 불명확으로 탈락 | [-] |
| 8.5 | Gender 기반 Preset 필터링 | 선택된 성별에 맞는 프리셋만 드롭다운에 표시 | [x] |
| 8.6 | Character Preview UI 개선 | 별도 행 레이아웃 + 클릭 시 확대 모달 | [x] |
| 9 | Multi-Character 지원 | A, B, C... 다중 캐릭터 구조 | [ ] |
| 10 | Scene Builder UI | 장면별 가변 컨텍스트 태그 선택 (priority 5-6) | [ ] |
| 11 | Tag Autocomplete | Danbooru 스타일 태그 자동완성 | [ ] |
| 12 | Character Preview | 캐릭터 설정 시 미리보기 표시 (64px 썸네일) | [x] |

### 6-4. Advanced Features (🔵 고급)
| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 13 | Civitai 연동 | LoRA 메타데이터 자동 가져오기 (MCP 활용) | [x] |
| 14 | Visual Tag Browser | 태그별 예시 이미지 표시 | [ ] |
| 15 | Tag Usage Analytics | 사용 빈도, 성공/실패 패턴 추적 | [ ] |
| 16 | Prompt History | 성공한 프롬프트 저장/재사용 | [ ] |
| 17 | Feedback Loop | 사용자 태그 제안 시스템 | [ ] |
| 18 | Profile Export/Import | Style Profile 공유 | [ ] |
| 19 | Character Builder UI | 조합형 캐릭터 생성 (Gender + Appearance + LoRA) | [ ] |
| 20 | Scene Clothing Override | 장면별 의상 변경 기능 | [ ] |

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

---

## 📊 Current Status

**Last Updated**: 2026-01-24

| Phase | 상태 | 진행률 |
|-------|------|--------|
| 1-4 | ARCHIVED | 100% |
| 5 | IN PROGRESS | 73% |
| 6-1 | COMPLETE | 100% |
| 6-2 | COMPLETE | 100% |
| 6-3 | IN PROGRESS | 70% |
| 6-4 | IN PROGRESS | 12% |
| 7 | NOT STARTED | 0% |

**다음 우선순위**:
1. Phase 6-3: Multi-Character, Scene Builder, Tag Autocomplete
2. Phase 5 잔여: Ken Burns Effect
3. Phase 7: IP-Adapter (ControlNet 의존)
