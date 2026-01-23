# Shorts Factory Master Roadmap (Strategic Re-ordered)

이 로드맵은 프로젝트의 안정성과 영상 품질을 최우선으로 하여 관리됩니다.

## 🏗️ Phase 1: Foundation & Stability (기반 및 안정성) - **COMPLETE**
*   [x] **Environment Diagnostic Tool**: `backend/check_env.py` 구축 완료.
*   [x] **Configuration Externalization**: `.env` 기반 환경 변수 분리 완료.
*   [x] **Foundation Setup (Linting & Tooling)**: Ruff, Prettier 적용 완료.
*   [x] **TDD Environment Setup**: Unit Test 환경 구축 완료.

## 🛠️ Phase 2: Refactoring & Architecture (구조 개선) - **RE-EVALUATING**
시스템의 거대 로직을 분리하려 했으나, 서비스 안정성 이슈로 인해 잠정 중단 및 재설계 중입니다.

### 2-1. Backend Modernization (Rollback Status)
*   [ ] **Service Layer Extraction (FAILED/ROLLBACKED)**:
    *   `logic.py`를 `services/`와 `routers/`로 분리 시도했으나, 오토파일럿 상태 머신 연동 오류 및 FFmpeg 렌더링 좌표 유실(Fidelity Issue) 발생.
    *   **Decision**: 2026-01-23, 안정성이 검증된 `208dab1` 시점으로 전체 롤백 수행.
*   [ ] **New Strategy**:
    *   거대 분리 대신, 기능을 하나씩(예: 키워드 조회만 먼저) 아주 작게 분리하는 '마이크로 리팩토링'으로 선회 예정.
    *   리팩토링 전, 영상 렌더링 결과물을 픽셀 단위로 비교하는 시각적 회귀 테스트(Visual Regression Test) 구축 선행 필수.

### 2-2. Frontend Componentization
*   [ ] **Step 1: Custom Hooks**: `page.tsx`에서 오토파일럿 로직 추출 (진행 예정).
*   [ ] **Step 2: Component Split**: UI 파편화 방지를 위한 아토믹 디자인 적용.

## 🎥 Phase 3: High-End Production (영상 품질 대격변)
*   [ ] **ControlNet Integration**: 캐릭터 일관성 확보.
*   [ ] **Professional Audio Ducking**: BGM 볼륨 자동 조절.

---
**Core Principle**: "Stabilize First, Quality Second, Automate Third"
**Latest Status**: 리팩토링 실패 후 롤백 완료. 현재 안정 모드에서 오토파일럿 정상 작동 여부 집중 모니터링 중.