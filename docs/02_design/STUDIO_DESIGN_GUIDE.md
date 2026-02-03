# Studio UI & Asset Management Guide

## 1. Studio UI Architecture (v3.0)

현재 스튜디오는 **Storyboard-Centric** 구조로 재구성되어, 하나의 스토리보드 내에서 모든 씬과 영상 설정을 통합 관리합니다.

### 주요 컴포넌트 구조
- **Storyboard Header**: 영상 제목, 설명, 대표 캐릭터 및 스타일 프로필 설정.
- **Scene Editor (Grid/List)**: 
    - 각 씬의 스크립트, 프롬프트, 이미지 미리보기 관리.
    - **Image Generation Panel**: 개별 또는 배치 이미지 생성 요청.
    - **Vision Validation**: 생성된 이미지의 품질 및 태그 일치도 실시간 확인.
- **Render Settings Panel (Right Sidebar)**:
    - **Layout**: Full, SNS Overlay, Post Card 선택.
    - **AI Voice Style**: Qwen-Audio 기반 음성 프롬프트 설정.
    - **BGM/Fonts**: 에셋 라이브러리 연동.

## 2. 에셋 관리 시스템 (Asset Management)

사용자는 'Manage' 탭 및 각 에셋 전용 패널을 통해 프로젝트에 사용되는 다양한 미디어를 관리합니다.

### 에셋 유형 및 관리 방법
1. **Characters**:
    - 캐릭터별 고유 태그, LoRA, IP-Adapter 레퍼런스 이미지 관리.
2. **LoRAs**: 
    - Civitai 연동을 통한 신규 모델 다운로드 및 가중치 캘리브레이션.
3. **Media Assets (Images/Videos)**:
    - 생성된 모든 결과물은 `MediaAsset` 테이블에 등록되어 정합성이 유지됩니다.
    - **Cleanup Utility**: 미사용(고아) 에셋이나 만료된 임시 파일을 환경 설정에 따라 정리할 수 있습니다.

## 3. 디자인 가이드라인 (Aesthetics)
- **Colors**: Deep Dark Theme (#121212) 기반, Vibrant Purple/Blue 포인트 컬러 사용.
- **Typography**: Pretendard / Inter (Sans-serif) 기반의 가독성 높은 레이아웃.
- **Micro-interactions**: Framer Motion을 활용한 씬 전환 및 버튼 호버 효과.
- **Glassmorphism**: 패널 및 모달 배경에 절제된 블러 효과 적용.
