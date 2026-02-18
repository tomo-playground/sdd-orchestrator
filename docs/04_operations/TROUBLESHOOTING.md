# Trouble Shooting Guide

개발 중 자주 발생하는 문제와 해결 방법을 기록합니다.

## 🔧 환경 설정 및 데이터 동기화

### 환경 설정 진단 (`check_env.py`)
*   **증상**: 서버가 실행되지 않거나, SD/DB 연결 오류 발생.
*   **해결**: 진단 스크립트를 실행하여 문제 원인 파악.
    ```bash
    uv run backend/check_env.py
    ```
    *   **주요 점검 항목**: `.env` 파일 존재 여부, `DATABASE_URL` 설정, SD WebUI 연결 상태, 필수 에셋(폰트, 오디오) 존재 여부.

### 태그/카테고리 불일치 (Tag Sync)
*   **증상**: 프론트엔드에서 태그가 검색되지 않거나, 프롬프트 순서가 이상함.
*   **원인**: 코드(`CATEGORY_PATTERNS`)와 DB(`tags` 테이블) 간의 데이터 불일치.
*   **해결**: 동기화 API를 호출하여 DB를 최신 상태로 강제 업데이트.
    ```bash
    # 1. 카테고리 및 우선순위 동기화 (기존 태그 업데이트 포함)
    curl -X POST "http://localhost:8000/keywords/sync-category-patterns?update_existing=true"
    
    # 2. LoRA 트리거 워드 동기화
    curl -X POST "http://localhost:8000/keywords/sync-lora-triggers"
    ```

## 🎨 Frontend (UI)

### `X is not defined` (Icon Error)
*   **증상**: 모달이나 사이드바 열 때 화면이 하얗게 변함.
*   **원인**: `lucide-react` 아이콘 임포트 누락 또는 이름 충돌.
*   **해결**: 상단 `import { X as XIcon ... }` 처럼 별칭(Alias)을 사용하여 충돌 방지.

### `handle... is not defined` (Reference Error)
*   **증상**: 버튼 클릭 시 아무 반응 없음 (콘솔 에러).
*   **원인**: 함수가 `return` 문(JSX)보다 아래에 정의됨 (호이스팅 문제) 또는 코드 삭제 시 누락됨.
*   **해결**: 모든 핸들러 함수를 컴포넌트 상단(`useState` 아래)으로 이동.

## ⚙️ Backend (API & Logic)

### 영상 생성 시 오디오 없음
*   **원인**: FFmpeg `acrossfade` 필터 충돌 또는 TTS 생성 실패.
*   **해결**:
    1. `backend/logs/backend.log` 로그 확인.
    2. `backend/services/video/` 디렉토리의 관련 파이프라인 코드 점검.
    3. TTS 모델 로딩 상태 확인 (`Qwen3-TTS model loaded successfully` 로그).

### 키워드/태그 관련 오류
*   **증상**: `Apply Missing Tags` 눌러도 로그가 안 뜸.
*   **원인**: `Network Error` 또는 DB 연결 오류.
*   **해결**:
    1. 백엔드 재시작
    2. PostgreSQL 연결 확인 (`DATABASE_URL` 환경변수)
    3. `tags` 테이블에 데이터 존재 확인

## 🎬 Render Timeout (20분 제한)

### 증상
*   **증상**: 복잡한 영상(Full Layout, 많은 씬, 고화질) 렌더링 시 20분이 지나면 `Render timeout after 20 minutes` 에러와 함께 실패함.
*   **원인**: `API_TIMEOUT.VIDEO_RENDER` (Frontend) 및 `FFMPEG_TIMEOUT_SECONDS` (Backend) 제한 시간 초과.
*   **해결**:
    1. **단기 해결**: 씬 개수를 줄이거나 해상도를 낮춰 재생성 시도.
    2. **설정 변경**: `frontend/app/constants/index.ts` 및 `backend/config.py`의 타임아웃 값 증가 (배포 필요).

## 🎬 Post Layout 자막(Scene Text) 미표시

### 증상
Post layout 영상에서 이미지 상단(scene_text_area)에 자막이 나타나지 않음. Full layout은 정상.

### 원인
`compose_post_frame()`에 `subtitle_text` 파라미터는 있으나, scene_text_area에 실제 렌더링하는 코드 누락.

**원래 흐름 (버그):**
1. `compose_post_frame(subtitle_text="")` ← 빈 문자열 전달
2. 자막을 별도 FFmpeg overlay로 처리 시도 → 실패

**원인 체인:**
- `_process_post_layout_image()`에서 `subtitle_text=""`로 호출
- `subtitle_lines`가 Post layout 처리 **이후**에 생성됨 (순서 문제)
- `compose_post_frame` 내부에 scene_text_area 렌더링 코드 자체가 없었음

### 해결 (2026-01-31)

1. **rendering.py** - `compose_post_frame`에 scene_text_area 렌더링 코드 추가
2. **video.py** - `subtitle_lines`를 Post layout 처리 **전**에 생성
3. **video.py** - `_process_post_layout_image`에서 실제 자막 텍스트 전달
4. **video.py** - Post layout은 FFmpeg subtitle overlay 비활성화 (카드에 직접 포함)

### 이미지 합성 순서 (확정)

**Post layout:**
```
1. subtitle_lines 생성 (wrap_scene_text)
2. compose_post_frame(subtitle_text=실제자막) → scene_X.png (카드에 자막 포함)
3. Ken Burns 효과 → [v{i}_kb]
4. [v{i}_kb]null[v{i}_base] (FFmpeg overlay 없음)
5. Trim → [v{i}_raw]
```

**Full layout:**
```
1. 원본 이미지 저장 → scene_X.png
2. subtitle 투명 PNG 생성 → subtitle_X.png
3. Ken Burns 효과 → [v{i}_kb]
4. FFmpeg overlay: [v{i}_kb] + [sub{i}] → [v{i}_base]
5. Trim → [v{i}_raw]
```

### 교훈
- `subtitles` → `scene_text` rename 시, 관련 렌더링 로직도 함께 검증 필요
- Post/Full layout의 자막 처리 방식이 다름을 인지
- 함수 파라미터만 있고 실제 사용 코드가 없는 경우 주의

---

## 🔤 Font Issue
*   **증상**: 자막 폰트가 기본 고딕체로 나옴.
*   **원인**: 맥북(NFD)과 윈도우(NFC)의 한글 자모 분리 현상으로 파일명 불일치.
*   **해결**: `backend/services/rendering.py` 또는 관련 렌더링 코드의 폰트 경로 정규화(Normalization) 로직 확인. 폰트 파일은 `backend/assets/fonts/`에 위치.

## 🎯 프롬프트 품질 개선 (Phase 6-4.21 Track 2)

### 문제: Gemini가 0% Effectiveness 태그 생성

**증상**: Gemini가 Danbooru에 없거나 WD14가 검출하지 못하는 태그를 생성합니다.
- `medium shot` (Danbooru 0건, 321회 사용)
- `surprised`, `confused`, `laughing` (WD14 미검출, 100+ 회 사용)
- `anime`, `day`, `bright` (낮은 effectiveness)

**원인**: Gemini가 Allowed Keywords 리스트를 완벽하게 따르지 않음 (LLM hallucination).

**해결**: 자동 필터링 시스템 (2026-01-27 구현)

#### 1. Effectiveness 기반 필터링
`filter_prompt_tokens()`가 자동으로:
- effectiveness < 30% 태그 감지
- RISKY_TAG_REPLACEMENTS 매핑이 있으면 → 교체
- 매핑 없으면 → 제거

**예시**:
```
Input:  "smile, medium_shot, surprised, classroom"
Filter: ❌ medium_shot (0%) → cowboy_shot
Filter: ❌ surprised (0%) → 제거
Output: "smile, cowboy_shot, classroom"
```

#### 2. 템플릿 강화
3개 Gemini 템플릿에 "⚠️ CRITICAL TAG SELECTION RULES" 추가:
- 리스트 외 태그 사용 금지 명시
- 잘못된 태그 사용 시 결과 예시 제공
- Recommended Tags 우선 사용 강조

#### 3. 로그 확인
생성 로그에서 필터링 확인:
```bash
grep "Filter" backend/logs/backend.log
```

**결과**:
- ✅ 0% effectiveness 태그 자동 제거
- ✅ 안전한 대체 태그 자동 적용
- ✅ Match Rate 향상 기대

---

## 🎨 SD 모델 변경 시 주의사항

### 태그 vs 모델 의존성

| 항목 | 모델 의존성 | 설명 |
|------|------------|------|
| **Danbooru 태그** | ❌ 낮음 | 표준화된 태그 체계. 대부분의 애니메 SD 모델이 공유 |
| **LoRA** | ✅ 높음 | SD 1.5용 ↔ SDXL용 호환 안됨 |
| **태그 효과** | ⚠️ 중간 | 같은 태그라도 모델마다 반응 다를 수 있음 |

### 모델 변경 체크리스트

1. **태그 DB** → 그대로 사용 가능 (Danbooru 태그는 범용)
2. **LoRA 라이브러리** → 전부 교체 필요 (SD 1.5 → SDXL 등)
3. **캐릭터 트리거** → LoRA에 따라 달라짐, DB 업데이트 필요
4. **Style Profile** → LoRA 참조 업데이트 필요
5. **일부 태그 효과** → 주요 태그 테스트 권장

### 권장 절차

```bash
# 1. 새 모델용 LoRA 파일 준비 (SD WebUI models/Lora 폴더)

# 2. DB의 LoRA 정보 업데이트
#    - Manage > Style > LoRAs 에서 새 LoRA 등록
#    - 기존 캐릭터의 LoRA 매핑 수정

# 3. Style Profile 업데이트
#    - 사용 중인 프로필의 LoRA 참조 확인

# 4. 테스트 이미지 생성
#    - 주요 캐릭터/태그 조합 검증
```

> **참고**: 태그 자체는 모델에 독립적이지만, 실제 이미지 품질/효과는 모델의 학습 데이터에 따라 달라집니다.
