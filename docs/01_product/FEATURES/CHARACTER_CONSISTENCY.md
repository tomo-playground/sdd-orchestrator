
# IP-Adapter 캐릭터 유사도 고도화

**상태**: 완료 (Phase 1~5 완료, SDXL 전환은 GPU 서버 확보 시 별도 Phase)
**우선순위**: 미정
**관련**: Phase 8 (Multi-Style)
**최종 갱신**: 2026-02-28 (소스 코드 기준 최신화)

---

## 현재 상황 요약

SD1.5 환경에서 IP-Adapter + Seed Anchoring + 포즈별 Weight 제한까지 구현 완료. 기본 모델이 `clip_face` (애니메이션 최적화)로 운용 중. SDXL 전환은 로컬 환경(M4 Pro 24GB) 성능 한계로 **보류**.

### 잔존 문제

1. **씬 간 얼굴 불일치** — Seed Anchoring으로 완화했으나, 각 씬 독립 생성의 근본 한계 존재
2. **체크포인트 최적화 여지** — 현재 체크포인트의 Danbooru 태그 반응성 검증 필요 (MeinaMix, Counterfeit-V3 등 후보)

---

## 구현 완료

### Phase 1: 레퍼런스 품질 개선
| # | 항목 | 상태 | 소스 위치 |
|---|------|------|----------|
| 1-A | 실사 사진 업로드 + 얼굴 크롭 (1.8x 확장) + 512×512 리사이즈 | ✅ | `services/ip_adapter.py:120-189` |
| 1-B | 레퍼런스 품질 검증 (얼굴 감지, 해상도 ≥256, 얼굴 비율 ≥10%) | ✅ | `services/ip_adapter.py:46-103` |

- 얼굴 감지: OpenCV Haar Cascade (anime → standard 2단계 fallback)
- 복수 얼굴 경고, 최대 얼굴 기준 primary 선택

### Phase 2: 멀티앵글 레퍼런스
| # | 항목 | 상태 | 소스 위치 |
|---|------|------|----------|
| 2-A | Multi-angle reference images (front/side_left/side_right/three_quarter/back) | ✅ | `models/character.py:92-94` (JSONB) |
| 2-B | Dual IP-Adapter units (primary 70% + secondary 30%) | ✅ | `services/ip_adapter.py:266-305` |

- 앵글 자동 선택: 프롬프트 태그 매칭 → front fallback → first available
- Dual 모드: `IP_ADAPTER_DUAL_ENABLED = False` (opt-in, 기본 비활성)

### Phase 3: 튜닝 고도화
| # | 항목 | 상태 | 소스 위치 |
|---|------|------|----------|
| 3-A | Per-character guidance_start/end 오버라이드 | ✅ | `models/character.py:88-90` |
| 3-B | FaceID face tag suppression (~17개 태그 → weight 0.3) | ✅ | `services/generation_prompt.py:481-526` |

- Suppression 대상: hair color 13종 + eye color 9종 + face feature 4종
- `faceid` 모델일 때만 작동 (clip/clip_face는 미적용)

### Phase 4: Seed Anchoring
| # | 항목 | 상태 | 소스 위치 |
|---|------|------|----------|
| 4-1 | Storyboard `base_seed` + scene_order 기반 결정론적 seed | ✅ | `services/seed_anchoring.py:31-63` |
| 4-2 | Image generation cache (deterministic seed only) | ✅ | `services/image_cache.py` |
| 4-3 | ~~Scene last_seed DB 저장~~ | ❌ DROP | 02-28 마이그레이션에서 제거 |

- **수식**: `(base_seed + scene_order × 1000) mod 2^31`
- **Seed 우선순위**: 명시적 seed > Anchored seed > Random (-1)
- **캐시**: `SD_IMAGE_CACHE_ENABLED=false` (기본 비활성), deterministic seed만 캐시
- **자동 생성**: 스토리보드 생성 시 `base_seed` 자동 할당
- **API**: `POST /{storyboard_id}/seed` (설정/해제/자동생성)

### Phase 5: 포즈별 IP-Adapter Weight 제한 (추가 발견)
| # | 항목 | 상태 | 소스 위치 |
|---|------|------|----------|
| 5-1 | 포즈 방향 감지 (front/side/back) | ✅ | `services/controlnet.py:100-123` |
| 5-2 | 방향별 weight 클램핑 (back=0.2, side=0.5, front=1.0) | ✅ | `services/controlnet.py:110-112` |

- `from_behind` → back (max 0.2), `profile_standing/walking` → side (max 0.5)
- 포즈-레퍼런스 충돌 방지 목적

---

## 보류 — SDXL 전환

**보류 사유**: 로컬 환경 (MacBook Pro M4 Pro 24GB) 성능 한계. SDXL 1024×1536 + ControlNet + IP-Adapter 조합 시 씬당 3~8분 예상 (SD1.5 대비 4~5배). 외부 GPU 서버 확보 시 재검토.

| 항목 | 설명 |
|------|------|
| SDXL 체크포인트 전환 | SD1.5 → SDXL 기반 모델 |
| SDXL IP-Adapter 모델 | `ip-adapter-plus-face_sdxl` 등 |
| SDXL ControlNet 모델 | `control_v11p_sd15_openpose` → SDXL 호환 |
| 해상도 변경 | 512×768 → 1024×1536 |

## 검토 가능 — SD1.5 체크포인트 최적화

현재 체크포인트 대비 Danbooru 태그 반응성이 더 좋은 SD1.5 모델 후보:

| 모델 | 스타일 | 강점 | 비고 |
|------|--------|------|------|
| **MeinaMix** | 애니메이션 | 캐릭터+배경 균형, Danbooru 태그 반응 최상급 | CFG 7, Clip Skip 2 |
| **Counterfeit-V3** | 하이퀄리티 애니 | 복잡한 태그 조합 디테일 유지, LoRA 호환성 높음 | CFG 7-8, Clip Skip 2 |
| **DreamShaper** | 다목적 | 자연어+태그 둘 다 반응, 스타일 범위 넓음 | CFG 7, Clip Skip 1-2 |

---

## 현재 구현 상태 (소스 코드 기준)

### IP-Adapter 설정

| 항목 | 값 | 소스 |
|------|-----|------|
| **기본 모델** | `clip_face` (`ip-adapter-plus-face_sd15 [7f7a633a]`) | `config.py:545` |
| **기본 Weight** | 0.35 (POC 30-scene 테스트 최적값) | `config.py:543` |
| **모델 우선순위** | 캐릭터 > StyleProfile > 글로벌 기본값 | `services/character_consistency.py:191-210` |
| **Auto-Enable** | 레퍼런스 이미지 존재 시 자동 활성화 | `services/character_consistency.py:172-184` |

### IP-Adapter 모델 3종

| 키 | 모델명 | 전처리기 | Control Mode | 용도 |
|----|--------|---------|-------------|------|
| `faceid` | `ip-adapter-faceid-plusv2_sd15` | `ip-adapter_face_id_plus` (InsightFace) | ControlNet is more important | 실사 얼굴 |
| `clip` | `ip-adapter-plus_sd15` | `ip-adapter_clip_sd15` | Balanced | 순수 일러스트/스타일 |
| `clip_face` | `ip-adapter-plus-face_sd15` | `ip-adapter_clip_sd15` | Balanced | **애니메이션 캐릭터 (기본값)** |

### Guidance 파라미터

| 파라미터 | 기본값 | 소스 |
|---------|--------|------|
| `guidance_start` | 0.0 | `config.py:549` |
| `guidance_end` (faceid) | 0.85 | `config.py:550` |
| `guidance_end` (clip/clip_face) | 1.0 | `config.py:551` |

### 레퍼런스 품질 기준

| 기준 | 값 | 소스 |
|------|-----|------|
| 최소 해상도 | 256×256 | `config.py:602` |
| 최소 얼굴 비율 | 10% (얼굴 면적/이미지 면적) | `config.py:603` |
| 크롭 확장 비율 | 1.8× (목/어깨 포함) | `services/ip_adapter.py:176` |
| 리사이즈 목표 | 512×512 (Lanczos) | `services/ip_adapter.py:189` |

### SD 환경

| 항목 | 값 | 소스 |
|------|-----|------|
| 체크포인트 | **AnyLoRA bakedVae (SD1.5)** — 프롬프트 표현력 최상, 스타일 중립 | SD WebUI 로컬 |
| 해상도 | 512×768 | `config.py:125-127` |
| Seed Anchor Offset | 1000 | `config.py:559` |
| ControlNet | `control_v11p_sd15_openpose` 등 (SD1.5) | `services/controlnet.py:126-132` |

### ConsistencyStrategy 구조 (`character_consistency.py:28-50`)

```
ConsistencyStrategy (frozen dataclass)
├── style_loras: tuple[dict, ...]     # StyleProfile > character fallback
├── ip_adapter_enabled: bool           # Auto-enable if reference exists
├── ip_adapter_reference: str | None
├── ip_adapter_weight: float = 0.35
├── ip_adapter_model: str | None       # clip_face | faceid | clip
├── ip_adapter_guidance_start/end
├── reference_only_enabled: bool       # IP-Adapter 비활성 시 대안
├── quality_score: str                 # high | medium | low
└── warnings: tuple[str, ...]
```
