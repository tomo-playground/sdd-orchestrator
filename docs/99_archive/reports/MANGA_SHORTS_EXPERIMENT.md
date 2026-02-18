# 4컷만화 쇼츠 레이아웃 실험 보고서

> 실험일: 2026-02-18
> 스크립트: `scripts/manga_animated_shorts.py`

## 1. 실험 목적

SD WebUI로 생성한 4컷 이미지를 만화 스타일 레이아웃으로 배치하고, 순차 공개 연출의 쇼츠 영상을 자동 생성하는 파이프라인 PoC.

## 2. 시스템 구성

| 구성 요소 | 설정 |
|----------|------|
| 캔버스 | 1080x1920 (9:16) |
| 패널 배치 | 2x2 그리드 (OUTER_PAD=40, GUTTER=18) |
| SD 생성 | 512x768, DPM++ 2M Karras, 28 steps, CFG 7.0 |
| IP-Adapter | ip-adapter-plus_sd15 (CLIP mode) |
| 렌더링 | FFmpeg libx264, CRF 20, 30fps |
| BGM | cute-guitar-music-322164.mp3 (volume 0.35) |

## 3. 캐릭터별 결과

### 3.1 Flat Color Girl (ID: 8)

| 항목 | 설정 | 결과 |
|------|------|------|
| LoRA | flat_color:0.4 | 스타일 LoRA라 캐릭터 일관성 약함 |
| IP-Adapter | 0.45~0.7 | 높은 가중치에서 포즈/시선을 레퍼런스가 지배 |
| looking_at_viewer | (1.4) 강조 | IP-Adapter에 의해 억제됨 |
| 소품 (fried_egg) | (1.4) 강조 | 일부 seed에서만 생성 |

**결론**: 스타일 LoRA + IP-Adapter 조합은 프롬프트 반응성이 낮아 장면 묘사가 어려움. 표정/소품 제어가 제한적.

### 3.2 Midoriya Izuku (ID: 3)

| 항목 | 설정 | 결과 |
|------|------|------|
| LoRA | mha_midoriya-10:0.4 | 캐릭터 인식 가능 + 장면 자유도 높음 |
| IP-Adapter | 0.45 | 보조 역할로 적절 |
| looking_at_viewer | (1.4) 강조 | 대부분 패널에서 정면 시선 확보 |
| 소품 (fried_egg) | (1.4) 강조 | seed 2027에서 접시+계란프라이 명확 |

**결론**: 캐릭터 전용 LoRA가 스타일 LoRA보다 일관성과 프롬프트 반응성 모두 우수.

## 4. LoRA 강도 비교 실험

테스트 조건: Midoriya, seed 2027, IP-Adapter CLIP 0.45, 패널 4 (계란프라이 + smug 표정)

| 강도 | 캐릭터 유사도 | 장면 묘사 (소품/표정) | 평가 |
|------|-------------|-------------------|------|
| **0.2** | 약함 (힌트 수준) | 매우 자유, 소품 과다 생성 | 캐릭터 부족 |
| **0.4** | 인식 가능 | 소품 명확, 표정 잘 반영 | **최적 균형** |
| **0.6** | 확실함 | 소품 OK, 표정 약간 경직 | 캐릭터 중심 시 적합 |
| **0.8** | 매우 강함 | 포즈 제한, 프롬프트 반응성 저하 | 레퍼런스 생성용 |

### 타입별 권장 강도

| LoRA 타입 | 권장 범위 | 비고 |
|----------|---------|------|
| 캐릭터 LoRA | 0.4~0.6 | 장면 묘사 밸런스 |
| 스타일 LoRA | 0.3~0.5 | 너무 높으면 색감/구도 제한 |
| 병용 시 | 각 0.3~0.4 | 총합 0.8 이하 |

> 상세 가이드: `docs/04_operations/CHARACTER_CONTROL_GUIDE.md` 섹션 5 참조

## 5. HOOK 연출 실험

### 5.1 전체 미스터리형 (기존)

```
Stage 0: 4패널 전부 "?" + "3시간 요리의 결말은...?"
Stage 1~4: 패널 1→2→3→4 순차 공개
Stage 5: CTA
```

- 장점: 미스터리 분위기
- 단점: 첫 프레임에서 콘텐츠 장르 파악 불가, 후킹 파워 약함

### 5.2 결말 선공개형 (개선)

```
Stage 0: 패널4(계란프라이)만 공개 + "이게 대체 어떻게...?"
Stage 1: 패널1(기) 추가
Stage 2: 패널2(승) 추가
Stage 3: 패널3(전) 추가 → 전체 완성
Stage 4: CTA
```

- 장점: 결말 → "왜?" 호기심 유발, 캐릭터 즉시 인지, 장르 파악 가능
- 단점: 스토리 순서가 역전되므로 일부 스토리 유형에 부적합
- **추천**: 반전/유머 스토리에 최적

### 5.3 기타 제안된 패턴 (미실험)

| 패턴 | 순서 | 적합 스토리 |
|------|------|------------|
| 대비형 | 패널1+4 → 2 → 3 | 기대-현실 갭 유머 |
| 역순 | 4→3→2→1 | "어떻게 이렇게 됐을까?" |
| 2+2 블록 | (1,2) → (3,4) | 빠른 페이스 |

## 6. 기술적 발견사항

### 6.1 SD 이미지 해상도

- **512x512 (정사각형)**: 세로 패널(~500x870)로 크롭 시 양옆 잘림 심함 → **부적합**
- **512x768 (세로)**: 패널 비율과 유사, 크롭 최소화 → **권장**

### 6.2 IP-Adapter + LoRA 상호작용

- IP-Adapter가 레퍼런스 이미지의 **포즈/시선**까지 전이시켜 프롬프트를 억제
- `(looking_at_viewer:1.4)` 같은 강조만으로는 극복 불가한 경우 있음
- **해결**: IP-Adapter 0.35~0.45 + 캐릭터 LoRA 0.4~0.6 조합이 최적
- 총 가중치(LoRA + IP-Adapter) **1.0 이하** 유지 권장

### 6.3 FFmpeg 파이프라인

- zoompan(미세 줌) + dissolve xfade 조합이 자연스러움
- 누적 offset 계산이 핵심: `acc += durations[i] - TRANS_DUR`
- 5스테이지 기준 ~8초, 6스테이지 기준 ~10초

## 7. 제품화 방향 (PM/작가 합의사항)

### PM 평가

- **제품 가치**: Full/Post 대비 "순차 공개 서스펜스" + "4장면 동시 가시성"이 차별점
- **타겟**: 유머/밈, 팬아트/2차창작, 에듀테인먼트
- **우선순위**: Tier 2 (중기). 프로토타입 존재로 PoC 비용 0
- **통합 방안**: `layout_style: "manga"` 추가, `MangaLayout` 상수, `compose_manga_frame()` 신규

### 스토리보드 작가 평가

- **서사 구조**: 기승전결 x 쇼츠 = 구조적 최적 매칭
- **텍스트 가이드**: 한 줄 10자, 총 20자 이내, 2줄 이하
- **caption vs script 분리** 권장 (말풍선 텍스트 ≠ TTS 내레이션)
- **Gemini 연동**: `manga_4koma` preset + 전용 Jinja2 템플릿 + `panel_role` 필드

### 제품화 체크리스트

- [ ] `docs/01_product/FEATURES/MANGA_LAYOUT.md` 명세 작성
- [ ] `backend/constants/layout.py`에 `MangaLayout` dataclass 추가
- [ ] `backend/services/presets.py`에 `manga_4koma` preset 등록
- [ ] `backend/templates/create_storyboard_manga4koma.j2` 작성
- [ ] `backend/services/image.py`에 `compose_manga_frame()` 구현
- [ ] `backend/services/video/builder.py` 3-way 분기 (full/post/manga)
- [ ] Frontend Publish 탭 Layout 선택 UI 확장
- [ ] 테스트 + VRT 베이스라인

## 8. 관련 파일

| 파일 | 설명 |
|------|------|
| `scripts/manga_animated_shorts.py` | 프로토타입 스크립트 |
| `docs/04_operations/CHARACTER_CONTROL_GUIDE.md` | LoRA 강도 가이드 (섹션 5) |
| `backend/constants/layout.py` | 기존 Full/Post 레이아웃 상수 |
