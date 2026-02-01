# Render Pipeline Specification

## Abstract
본 문서는 `backend/services/video.py`의 `VideoBuilder` 클래스를 통해 수행되는 영상 렌더링 파이프라인의 명세를 다룹니다. FFmpeg 필터 구성, Ken Burns 효과, 자막 렌더링 및 레이아웃 관리 로직을 포함합니다.

## 1. Pipeline Overview
영상 생성은 다음과 같은 단계별 프로세스를 따릅니다.

1.  **환경 준비 (Setup)**: 프로젝트 ID 생성, 임시 디렉토리 설정, 아바타 및 폰트 경로 확인.
2.  **씬 프로세싱 (Scene Processing)**:
    *   이미지 로드 (MinIO/S3 또는 로컬 스토리지).
    *   자막 텍스트 래핑 (가독성을 위한 동적 폰트 크기 조절 포함).
    *   Post Layout 이미지 합성 (Pillow 사용).
    *   TTS 오디오 생성 (Edge TTS 사용).
3.  **타이밍 계산 (Timing)**: TTS 길이와 사용자 설정 속도를 고려하여 각 씬의 최종 재생 시간 결정.
4.  **FFmpeg 필터 빌드 (Filter Construction)**:
    *   **이미지 변환**: Scale & Crop (Full Layout: 9:16 최적화 크롭 적용).
    *   **모션 효과**: Ken Burns (Zoom/Pan) 프리셋 적용.
    *   **자막 합성**: Ken Burns 효과 후에 자막을 오버레이하여 자막의 선명도와 고정 위치 유지.
    *   **오디오 합성**: TTS와 BGM 병합, Sidechain Compression(Ducking) 적용.
    *   **전환 효과**: 씬 간 xfade/acrossfade 적용.
5.  **인코딩 및 등록 (Encoding & Registration)**: FFmpeg 실행 후 생성된 파일을 미디어 에셋으로 DB에 등록.

## 2. FFmpeg 필터 체인 (Filter Chain)
각 씬의 비디오 트랙은 다음과 같은 순서로 필터링됩니다.
`[Input] -> scale/crop (scaled) -> zoompan (kb) -> overlay subtitle (base) -> trim (raw)`

-   **Full Layout 크롭 전략**: 2:3 해상도 이미지를 9:16으로 변환 시, 캐릭터의 머리 부분을 보존하기 위해 상단에서 30% 지점을 기준으로 크롭합니다 (`ih-oh)*0.3`).
-   **자막 오버레이**: 자막은 0.3초의 Fade In/Out 애니메이션을 포함하며, 영상 모션과 독립적으로 유지하기 위해 Ken Burns 효과 이후에 합성됩니다.

## 3. 레이아웃 관리 (Layout Styles)
### Post Layout
-   Instagram/YouTube 포스트 스타일.
-   중앙에 이미지가 배치되고 상/하단에 사용자 정보 및 캡션이 포함된 카드가 Pillow를 통해 사전 합성됩니다.
-   자막이 카드 내부에 직접 렌더링됩니다.

### Full Layout
-   YouTube Shorts 표준 (9:16 전체 화면).
-   이미지가 전체 화면을 채우며, 자막은 화면 하단(또는 이미지 복잡도에 따른 최적 위치)에 FFmpeg 오버레이로 레이어링됩니다.

## 4. Ken Burns 효과 구현
-   `services/motion.py`에 정의된 프리셋(`zoom_in_center`, `pan_up_vertical` 등)을 사용합니다.
-   `zoompan` 필터를 사용하여 부드러운 줌과 패닝을 구현하며, 씬 재생 시간에 맞춰 프레임 수를 동적으로 계산합니다.

## 5. 오디오 렌더링 (Audio & Ducking)
-   **Audio Ducking**: 내레이션(TTS)이 나올 때 BGM 볼륨을 자동으로 25% 수준으로 낮추는 `sidechaincompress` 필터를 적용합니다.
-   **Transitions**: `acrossfade`를 사용하여 씬 간 오디오를 자연스럽게 연결합니다.
