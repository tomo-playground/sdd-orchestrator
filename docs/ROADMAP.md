# Shorts Factory Master Roadmap (Strategic Re-ordered)

이 로드맵은 실질적인 개발 효용성과 영상 품질 향상을 최우선으로 하여 재정렬되었습니다.

## 🏗️ Phase 1: Foundation & Stability (기반 및 안정성) - **URGENT**
본격적인 기능 추가 전, 개발 속도를 늦추는 장애물을 제거하고 협업/개발 환경을 정비합니다.

*   [ ] **Environment Diagnostic Tool (1순위)**:
    *   **Why**: "왜 안 되지?" 하는 디버깅 시간을 90% 단축.
    *   **Tech**: `backend/check_env.py` - FFmpeg, WebUI 연결, API Key, 폰트 유무 자동 진단.
*   [ ] **Foundation Setup (Linting & Tooling)**:
    *   **Why**: 코드 스타일 통일 및 자동 정렬.
    *   **Tech**: Absolute Import Path 설정, ESLint/Prettier Strict 규칙 적용.
*   [ ] **TDD Environment Setup (Unit Testing)**:
    *   **Why**: 리팩토링 시 기능 파괴 방지.
    *   **Tech**: `pytest` & `Vitest` 기반의 빠른 피드백 루프 구축.
*   [ ] **Frontend Refactoring (Component & Zustand)**:
    *   **Why**: 비대한 `page.tsx` 분해 및 전역 상태 관리 도입.

## 🎥 Phase 2: High-End Production (영상 품질 대격변)
영상의 시각적/청각적 완성도를 결정짓는 핵심 AI 기술을 도입합니다.

*   [ ] **ControlNet (IP-Adapter) Integration**:
    *   **Why**: **(품질 최우선)** 캐릭터 얼굴 일관성(Identity Locking)의 최종 해결책.
*   [ ] **VEO Clip (Short Motion)**:
    *   **Why**: 정지 이미지를 생동감 넘치는 AI 비디오로 전환.
*   [ ] **Dynamic Camera & Parallax**:
    *   **Why**: FFmpeg를 활용한 2.5D 입체 효과 및 정교한 줌/팬 연출.
*   [ ] **Professional Audio Ducking**:
    *   **Why**: 내레이션 시 BGM 볼륨 자동 조절로 전달력 극대화.

## 🤖 Phase 3: Intelligent Automation & Data (지능화 및 데이터)
시스템이 스스로 학습하고, 데이터가 안전하게 보존됩니다.

*   [ ] **SQLite Database Integration**:
    *   **Why**: 브라우저 캐시 사고 방지 및 고유 프로젝트 DB화.
*   [ ] **Self-Learning Keyword Dictionary**:
    *   **Why**: 사용자의 피드백을 통해 사전이 점점 풍부해짐.
*   [ ] **Resume/Checkpoint System**:
    *   **Why**: 중단된 오토파일럿을 마지막 지점부터 다시 시작.

## 🛠️ Phase 4: Reliability & Ops (확장 및 운영)
*   [ ] **Docker Containerization**:
    *   **Why**: 고사양 클라우드 서버(RunPod 등)로의 즉시 이사 및 배포 용이성.
*   [ ] **Automated Type Sync (OpenAPI)**:
    *   **Why**: 백엔드와 프론트엔드 간의 데이터 필드명 불일치 에러 원천 차단.
*   [ ] **E2E Test Automation**:
    *   **Why**: 최종 릴리즈 전 전수 자동 점검.

---
**Core Principle**: "Stabilize First, Quality Second, Automate Third" (안정성 위에 품질을 쌓고, 그 후에 자동화한다)
