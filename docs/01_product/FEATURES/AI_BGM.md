# AI BGM Generation (Stable Audio Open)

**상태**: 완료 (2026-02-07)

## 배경

기존 BGM은 정적 파일(File 모드)만 지원하여 콘텐츠 분위기에 맞는 배경음악을 매번 수동으로 찾아야 하는 반복 작업이 발생. Stable Audio Open 모델을 활용하면 텍스트 프롬프트로 분위기에 맞는 BGM을 자동 생성할 수 있다.

## 목표

- 텍스트 프롬프트 기반 배경음악 자동 생성
- Music Preset으로 재사용 가능한 BGM 설정 관리
- 기존 파일 BGM과 AI BGM을 렌더 설정에서 자유롭게 전환
- SHA256 캐시로 동일 프롬프트 중복 생성 방지

## 결정 사항

| 항목 | 결정 |
|------|------|
| AI 모델 | Stable Audio Open (stabilityai/stable-audio-open-1.0) |
| 스케줄러 | DPMSolverMultistepScheduler (재귀 제한 회피) |
| 디바이스 | MPS 자동 감지, CPU 폴백 (`config.py` SAO_DEVICE) |
| 모델 로딩 | Lazy load (첫 사용 시) + asyncio.Lock 스레드 안전 |
| 캐시 전략 | SHA256 해시(prompt+duration+seed+steps) 기반 파일 캐시 |
| BGM 모드 | File (기존 정적 파일) / AI (프리셋 기반 생성) |
| 시스템 프리셋 | 10종 기본 제공 |

## 주요 구성요소

### 1. Music Presets CRUD (Manage 탭)

- 프리셋 목록 조회/생성/수정/삭제
- 프리셋 필드: name, description, prompt, duration, seed
- 시스템 프리셋(is_system=true)은 삭제 불가
- 삭제 시 연결된 MediaAsset + Storage 파일 함께 정리

### 2. Preview 생성 + Play/Stop

- 프리셋 설정으로 미리듣기 오디오 생성 (POST `/music-presets/preview`)
- 임시 MediaAsset(is_temp=true)으로 저장
- 확정 시 프리셋에 연결 (POST `/music-presets/{id}/attach-preview`)
- 브라우저 내 재생/정지 제어

### 3. Render Settings BGM Mode 토글

- File 모드: 기존 정적 BGM 파일 선택 (변경 없음)
- AI 모드: Music Preset 드롭다운에서 프리셋 선택
- RenderSettingsPanel에서 토글 UI 제공

### 4. Video Pipeline 연동

- 렌더링 시 bgm_mode=ai이면 music_preset_id로 BGM 생성
- 생성된 WAV를 FFmpeg 파이프라인에 믹싱

### 5. 시스템 프리셋 10종

| # | 프리셋 이름 | 용도 |
|---|------------|------|
| 1 | Lo-fi Chill | 일상/브이로그 |
| 2 | Epic Cinematic | 드라마틱/역사 |
| 3 | Dark Ambient | 호러/미스터리 |
| 4 | Upbeat Pop | 밝은/코미디 |
| 5 | Emotional Piano | 감동/스토리 |
| 6 | Action Intense | 액션/스포츠 |
| 7 | Mystery Suspense | 추리/서스펜스 |
| 8 | Fantasy Adventure | 판타지/모험 |
| 9 | Calm Nature | 힐링/자연 |
| 10 | Retro Game | 게임/레트로 |

### 6. SAO 모델 워밍업

- POST `/music-presets/warmup` 으로 수동 사전 로딩
- 첫 요청 시 모델 다운로드/로딩 시간 회피용

## 기술 개요

### API (8 엔드포인트)

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/music-presets` | 전체 프리셋 목록 |
| GET | `/music-presets/{id}` | 단건 조회 |
| POST | `/music-presets` | 프리셋 생성 |
| PUT | `/music-presets/{id}` | 프리셋 수정 |
| DELETE | `/music-presets/{id}` | 프리셋 삭제 (+ Storage 정리) |
| POST | `/music-presets/preview` | 미리듣기 오디오 생성 |
| POST | `/music-presets/{id}/attach-preview` | 미리듣기를 프리셋에 연결 |
| POST | `/music-presets/warmup` | SAO 모델 수동 워밍업 |

### DB 변경

**신규 테이블**: `music_presets`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | Integer PK | |
| name | String(200) | 프리셋 이름 |
| description | Text | 설명 (nullable) |
| prompt | Text | Stable Audio Open 프롬프트 (nullable) |
| duration | Float | 생성 길이 초 (nullable) |
| seed | Integer | 시드값, -1이면 랜덤 (nullable) |
| audio_asset_id | FK(media_assets) | 생성된 오디오 에셋 (ON DELETE SET NULL) |
| is_system | Boolean | 시스템 프리셋 여부 (default: false) |
| created_at, updated_at | DateTime | 타임스탬프 |

**확장**: `render_presets`
- `bgm_mode` (String(20), nullable) -- "file" | "ai"
- `music_preset_id` (FK → music_presets, ON DELETE SET NULL)

### Backend 구조

```
services/audio/
├── __init__.py
└── music_generator.py    # SAO 파이프라인 로딩, generate_music(), 파일 캐시
routers/
└── music_presets.py      # CRUD + preview + attach + warmup
models/
└── music_preset.py       # MusicPreset ORM
```

### Frontend 구조

```
manage/tabs/MusicPresetsTab.tsx       # 프리셋 관리 UI
manage/hooks/useMusicPresetsTab.ts    # 프리셋 탭 로직
components/video/RenderSettingsPanel.tsx  # BGM 모드 토글 (File/AI)
components/studio/RenderTab.tsx       # 렌더 탭 BGM 연동
store/slices/outputSlice.ts           # bgmMode 상태 ("file" | "ai")
```

## 수락 기준

| # | 기준 | 상태 |
|---|------|------|
| 1 | Music Preset CRUD가 정상 동작 (생성/조회/수정/삭제) | 완료 |
| 2 | 미리듣기로 프롬프트 기반 BGM 샘플 생성 및 재생 가능 | 완료 |
| 3 | 렌더 설정에서 File/AI BGM 모드 전환 가능 | 완료 |
| 4 | AI 모드 렌더링 시 BGM이 자동 생성되어 영상에 포함 | 완료 |
| 5 | 동일 프롬프트 재요청 시 캐시에서 반환 (중복 생성 없음) | 완료 |
| 6 | 시스템 프리셋 10종이 초기 데이터로 제공 | 완료 |
| 7 | 기존 File 모드 BGM 기능이 정상 유지 (하위 호환) | 완료 |

## 관련 파일

| 파일 | 역할 |
|------|------|
| `backend/services/audio/music_generator.py` | SAO 모델 로딩/생성/캐시 엔진 |
| `backend/routers/music_presets.py` | API 엔드포인트 (8개) |
| `backend/models/music_preset.py` | MusicPreset ORM 모델 |
| `backend/models/render_preset.py` | bgm_mode, music_preset_id 컬럼 |
| `backend/alembic/versions/e7500a9de34b_*.py` | 마이그레이션 |
| `frontend/app/(app)/manage/tabs/MusicPresetsTab.tsx` | 프리셋 관리 UI |
| `frontend/app/(app)/manage/hooks/useMusicPresetsTab.ts` | 프리셋 탭 로직 |
| `frontend/app/components/video/RenderSettingsPanel.tsx` | BGM 모드 토글 |
| `frontend/app/components/studio/RenderTab.tsx` | 렌더 탭 연동 |
| `frontend/app/store/slices/outputSlice.ts` | bgmMode 상태 관리 |
