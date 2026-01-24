# Trouble Shooting Guide

개발 중 자주 발생하는 문제와 해결 방법을 기록합니다.

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
