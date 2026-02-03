# Pose Asset Maintenance Guide

이 문서는 시스템의 ControlNet 포즈 라이브러리를 데이터 기반으로 추출하고 신규 포즈를 보강하는 방법을 설명합니다.

## 1. 데이터 기반 포즈 추출 (Audit)

사용자들이 프롬프트에서 실제로 어떤 포즈를 요구하는지 분석하기 위해 다음 스크립트를 실행합니다.

```bash
# DB 내 상위 포즈 관련 태그 및 커버리지 확인
python scripts/final_audit.py
```

이 스크립트는 다음을 수행합니다:
- `Scene` 이미지 프롬프트 및 `ActivityLog` 실행 기록 분석
- 가장 빈번하게 사용되는 액션/포즈 키워드 도출
- 현재 `services/controlnet.py`의 `POSE_MAPPING`에서 지원하는지 여부(✅/❌) 표시

## 2. 신규 포즈 추가 절차

### Step 1: 레퍼런스 이미지 생성
Gemini 또는 외부 툴을 사용하여 신규 포즈 이미지를 생성합니다.
- **포맷**: 512x512 또는 768x768 PNG (흰색 배경 권장)
- **위치**: `backend/assets/poses/[pose_name].png`

### Step 2: 시스템 매핑 등록
`backend/services/controlnet.py` 파일을 수정합니다.

1.  **`POSE_MAPPING` 추가**:
    ```python
    POSE_MAPPING = {
        "new pose": "new_pose_file.png",
    }
    ```
2.  **`pose_priority` 업데이트**: 새로 추가된 포즈가 감지되도록 우선순위 리스트에 추가합니다.
3.  **`pose_synonyms` 등록**: 사용자가 입력할 수 있는 다양한 동의어(undercore 포함 등)를 매핑합니다.

### Step 3: 스토리지 동기화 (S3/MinIO)
로컬에 추가된 파일을 클라우드 저장소에 반영합니다.

```bash
# 모든 포즈 에셋을 S3(Minio)로 일괄 동기화
python scripts/sync_poses.py
```

## 3. 유의 사항
- **해부학적 정확도**: 레퍼런스 이미지의 관절 위치가 명확해야 ControlNet(OpenPose/Depth)이 정확하게 인식합니다.
- **가중치 처리**: 시스템은 `(standing:1.2)`와 같은 가중치 태그를 자동으로 정규화하여 처리하므로, 매핑 키에는 가중치를 포함할 필요가 없습니다.

---

## 관련 가이드
- **캐릭터 제어 전략**: 포즈 정보가 부족할 때의 IP-Adapter 활용법 등은 [Character Control Guide](CHARACTER_CONTROL_GUIDE.md)를 참조하세요.
