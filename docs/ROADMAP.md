# Shorts Factory Master Roadmap (Strategic Fidelity Guard)

이 로드맵은 리팩토링 및 기능 추가 시 **영상 품질의 100% 일관성(Zero Variance)**을 유지하는 것을 최우선 목표로 합니다.

## 🏗️ Phase 1: Foundation & Stability - **COMPLETE**

## 🛠️ Phase 2: Visual Fidelity Guard (영상 품질 보전 및 회귀 방지) - **CURRENT**
영상 생성 코드가 수정되어도 결과물이 변하지 않도록 하는 근본적인 안전 장치를 구축합니다.

### 2-1. Deterministic Render Engine (결정론적 렌더링 환경)
*   [ ] **Fixed Seed Testing**: 테스트 시 모든 AI 생성(이미지, 음성)의 시드를 고정하여 동일한 인풋 데이터를 보장.
*   [ ] **Layout Spec Extraction**: Pillow/FFmpeg 코드에 하드코딩된 좌표와 비율을 `LayoutSchema` 파일로 완전히 분리. (로직과 데이터의 분리)

### 2-2. Automated Visual Regression Test (자동 비주얼 회귀 테스트)
*   [ ] **Golden Master Storage**: 현재 가장 안정적인 `logic.py`가 생성한 영상의 특정 프레임들을 `tests/references/`에 '표준'으로 저장.
*   [ ] **Pixel-by-Pixel Comparison Engine**:
    *   **Tool**: `OpenCV` 및 `SSIM(Structural Similarity Index)` 도입.
    *   **Task**: 코드가 바뀌면 자동으로 영상을 생성하고, 표준 프레임과 픽셀 단위로 대조하여 99.9% 일치하지 않으면 빌드 실패 처리.
*   [ ] **Diff Reporting**: 일치하지 않을 경우, 어느 좌표의 픽셀이 어떻게 변했는지 시각적으로 보여주는 Diff 이미지 자동 생성.

## 🛠️ Phase 3: Incremental Refactoring (안전 장치 기반 리팩토링)
Phase 2의 자동 검증 도구가 완성된 후, 이를 통과하는 것을 전제로 하나씩 분리합니다.

*   [ ] **Keyword/Asset Separation**: 영향도가 적은 조회 로직부터 분리.
*   [ ] **Core Rendering Migration**: FFmpeg 조립 로직을 서비스로 이관하며 **매 커밋마다 비주얼 테스트 실행**.

## 🎥 Phase 4: High-End Production (검증된 기반 위 품질 강화)
*   [ ] **Professional Audio Ducking**: 내레이션-BGM 볼륨 자동 조절.
*   [ ] **Ken Burns Effect**: 정지 이미지에 생동감 있는 줌/팬 효과 부여.
*   [ ] **Character Consistency (ControlNet)**: 주인공 얼굴 고정 기술 적용.

## 🤖 Phase 5: Intelligent Ops (운영 효율화)
*   [ ] **Resume/Checkpoint System**: 중단된 작업 이어하기.
*   [ ] **Project DB (SQLite)**: 모든 프로젝트 설정 및 생성 히스토리 관리.

---
**Core Mandate**: "No changes in output without explicit intention." (의도하지 않은 결과물의 변화는 허용하지 않는다.)
**Latest Status**: 2026-01-23 전체 롤백 완료. 영상 품질 보전을 위한 비주얼 회귀 테스트(VRT) 엔진 설계 착수.
