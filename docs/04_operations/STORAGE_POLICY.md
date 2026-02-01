# Asset Storage & Management Specification (V3.1)

이 문서는 Shorts Producer V3에 도입된 계층적 에셋 관리 시스템과 스토리지 추상화 계층에 대한 상세 사양 및 사용법을 정의합니다.

**Last Updated:** 2026-01-31 (Phase 6-4.31 완료)

---

## 1. 아키텍처 개요

V3의 에셋 관리는 **물리적 저장(Storage)**과 **논리적 데이터베이스 등록(Asset Service)**을 분리하여 관리합니다.

### 1.1 계층 구조
모든 에셋은 프로젝트 및 그룹 단위로 조직화되어 관리됩니다.

**프로젝트 기반 에셋** (`projects/{p_id}/groups/{g_id}/storyboards/{s_id}/`):
- `images/{file}`: 씬별 생성 이미지
- `videos/{file}`: 렌더링된 영상

**공유 에셋** (`shared/{type}/`):
- `audio/`: BGM 파일
- `fonts/`: 자막 폰트
- `overlay/`: 프레임 오버레이 이미지
- `references/`: IP-Adapter 참조 이미지
- `poses/`: ControlNet 포즈 가이드
- `avatars/`: 채널 아바타

**모델 기반 에셋**:
- `characters/{id}/preview/{file}`: 캐릭터 미리보기
- `loras/{id}/preview/{file}`: LoRA 미리보기
- `sdmodels/{id}/preview/{file}`: SD 모델 미리보기

### 1.2 스토리지 추상화 (Storage Layer)
`StorageService`를 통해 물리적 저장공간에 투명하게 접근합니다.
- **LocalStorage**: 로컬 파일 시스템 사용 (`outputs/` 폴더)
- **S3Storage**: MinIO 또는 AWS S3 호환 스토리지 사용

---

## 2. 설정 (Configuration)

`.env` 파일을 통해 스토리지 모드를 설정할 수 있습니다.

```env
# Storage Mode: 's3' or 'local'
STORAGE_MODE=s3

# S3/MinIO Configuration
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=your_access_key
MINIO_SECRET_KEY=your_secret_key
MINIO_BUCKET=shorts-producer
STORAGE_PUBLIC_URL=http://localhost:9000
```

---

## 3. 백엔드 사용법 (Backend Usage)

### 3.1 AssetService 사용 (권장)
데이터베이스 등록과 파일 저장을 동시에 수행할 때 사용합니다.

```python
from services.asset_service import AssetService
from database import SessionLocal

db = SessionLocal()
service = AssetService(db)

# 이미지 저장 및 DB 등록
asset = service.save_scene_image(
    image_bytes=img_bytes,
    project_id=1,
    group_id=1,
    storyboard_id=10,
    scene_id=5,
    file_name="scene_5.png"
)

# 자산의 공개 URL 획득
url = service.get_asset_url(asset.storage_key)
```

### 3.2 StorageService 직접 사용
공통 리소스(아바타 등)나 단순 파일 조작 시 사용합니다.

**✅ 올바른 패턴** (Phase 6-4.31):
```python
from services.storage import get_storage

# 함수 내에서 storage 인스턴스 획득
storage = get_storage()

# 파일 존재 여부 확인
exists = storage.exists("shared/avatars/default.png")

# 로컬 캐시 경로 획득 (FFmpeg 처리용)
local_path = storage.get_local_path("shared/avatars/default.png")

# 파일 삭제
storage.delete("temp/garbage.tmp")

# 공개 URL 생성
url = storage.get_url("shared/audio/bgm.mp3")
```

**❌ 잘못된 패턴** (전역 import):
```python
from services.storage import storage  # NameError 발생 가능!
storage.exists("...")  # 초기화 안 됨
```

---

## 4. 프론트엔드 연동 (Frontend Usage)

프론트엔드에서는 `projectId`와 `groupId`를 상태에서 관리하며, API 호출 시 이를 포함해야 합니다.

### 4.1 storeSceneImage 호출
```typescript
import { storeSceneImage } from '@/store/actions/imageActions';

const storedUrl = await storeSceneImage(
  base64Image,
  projectId,
  groupId,
  storyboardId,
  sceneId
);
```

### 4.2 State Management (`useStudioStore`)
- `MetaSlice`에 `projectId`, `groupId`가 포함되어 관리됩니다.
- 각 스튜디오 진입 시 해당 ID들이 서버로부터 로드되어 설정됩니다.

### 4.3 Video Rendering (Phase 6-4.31)
영상 렌더링 시 **반드시** `project_id`와 `group_id`를 payload에 포함해야 MediaAsset이 생성됩니다.

```typescript
const payload = {
  project_id: 1,  // 필수!
  group_id: 1,    // 필수!
  storyboard_id: store.storyboardId,
  scenes: [...],
  // ... 기타 설정
};

const res = await axios.post(`${API_BASE}/video/create`, payload);
```

**결과**:
- ✅ MediaAsset 생성 → `video_asset_id` 설정 → MinIO URL 저장
- ❌ 누락 시 → 로컬 경로(`/outputs/videos/...`) 반환 → DB 불일치

---

## 5. 관리 및 정리 (Maintenance)

### 5.1 Cleanup Service
`CleanupService`는 새로운 계층 구조를 인식하여 프로젝트 단위 정리를 지원합니다.

- **지원 기능**:
  - 만료된 임시 파일 삭제
  - 업로드 후 사용되지 않는 고립된 에셋(Orphan assets) 정리
  - 통계 수집 (`get_storage_stats`)

### 5.2 DB 마이그레이션 (`projects`, `groups`, `media_assets`)
에셋 관리를 위해 SQLAlchemy 모델이 추가되었으며, Alembic을 통해 마이그레이션이 관리됩니다.
```bash
alembic upgrade head
```

---

## 6. Phase 6-4.31 완료 내용 (2026-01-31)

### 6.1 Storage 초기화 일관성
**문제**: 일부 파일에서 `from services.storage import storage` 전역 import 사용 → `NameError` 발생
**해결**: 모든 파일을 `get_storage()` 패턴으로 통일

**수정 파일** (7개):
- `services/rendering.py`, `video.py`, `controlnet.py`
- `routers/avatar.py`, `characters.py`, `storyboard.py`
- `routers/assets.py`

### 6.2 Video MediaAsset 생성 활성화
**문제**: Frontend에서 `project_id`/`group_id` 누락 → MediaAsset 생성 실패 → 로컬 경로 저장
**해결**: Frontend payload에 기본값 추가

```typescript
// Before
const payload = {
  storyboard_id: store.storyboardId,
  scenes: [...],
};

// After
const payload = {
  project_id: 1,  // 추가
  group_id: 1,    // 추가
  storyboard_id: store.storyboardId,
  scenes: [...],
};
```

**결과**:
- `VideoBuilder.build()` → AssetService.save_rendered_video() 실행
- `storyboard.video_asset_id` 자동 설정
- `recent_videos_json`에 MinIO URL 저장

### 6.3 DB 무결성 정리
- storage_key에서 중복 bucket prefix 제거 (4건)
- 고아 media_assets 레코드 삭제 (2건)
- URL 파싱 로직 개선 (`storyboard.py`)

### 6.4 Assets API 테스트
- `test_router_assets.py` 10개 테스트 추가
- `/fonts/list`, `/audio/list`, `/overlay/list` 엔드포인트 검증
- S3/Local 모드 모두 커버

---

**주의사항**:
- 직접적인 파일 시스템 조작 (`os.remove`, `open`) 대신 항상 `get_storage()` 또는 `AssetService`를 통해 에셋을 관리해야 데이터 일관성이 유지됩니다.
- **storage_key는 버킷명을 포함하지 않습니다.** `get_url()`이 자동으로 버킷명을 추가합니다.
