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
    1. `uv run main.py` 로그 확인.
    2. `backend/logic.py` (또는 main.py)의 `acrossfade` 파라미터 간소화.

### 키워드/태그 관련 오류
*   **증상**: `Apply Missing Tags` 눌러도 로그가 안 뜸.
*   **원인**: `Network Error` 또는 DB 연결 오류.
*   **해결**:
    1. 백엔드 재시작
    2. PostgreSQL 연결 확인 (`DATABASE_URL` 환경변수)
    3. `tags` 테이블에 데이터 존재 확인

## 🔤 Font Issue
*   **증상**: 자막 폰트가 기본 고딕체로 나옴.
*   **원인**: 맥북(NFD)과 윈도우(NFC)의 한글 자모 분리 현상으로 파일명 불일치.
*   **해결**: `main.py`의 `resolve_subtitle_font_path` 함수 내 정규화(Normalization) 로직 확인.

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
