# Asset Storage & Lifecycle Policy

Shorts Producer 시스템의 파일 저장 구조, 에셋 유형별 보관 정책 및 스토리지 관리 지침을 정의합니다.

## 1. 스토리지 구조 (Directory Hierarchy)

시스템은 `backend/outputs/` 디렉토리를 루트로 하며, `STORAGE_MODE`에 따라 로컬 또는 S3(MinIO)에 분산 저장됩니다.

```text
outputs/
├── images/           # 최종 채택된 장면 이미지 (영구)
├── videos/           # 최종 렌더링된 비디오 파일 (영구)
├── _build/           # 렌더링 과정에서 발생하는 임시 파일 (즉시 삭제)
│   ├── frames/       # FFmpeg 합성을 위한 개별 프레임
│   └── tts/          # 생성된 개별 씬 오디오
├── _prompt_cache/    # API 응답 및 이미지 캐시 (TTL 적용)
├── _s3_cache/        # S3에서 다운로드한 파일 로컬 캐시
└── shared/           # 공용 에셋
    ├── avatars/      # 캐릭터 아바타 이미지
    └── references/   # IP-Adapter용 레퍼런스 이미지
```

## 2. 에셋 수명 주기 (Lifecycle Management)

에셋의 성격에 따라 데이터베이스 연동 및 자동 삭제 정책이 다르게 적용됩니다.

| 에셋 유형 | 저장 경로 | DB 연동 | 보관 정책 (TTL) | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **장면 이미지** | `images/` | `MediaAsset` | **영구** | 채택된 최종 이미지 |
| **최종 비디오** | `videos/` | `MediaAsset` | **영구** | 최종 결과물 |
| **임시 작업 파일** | `_build/` | No | **수행 직후 삭제** | 비디오 빌드 완료 시 자동 제거 |
| **프롬프트 캐시** | `_prompt_cache/` | No | **24시간 (1일)** | `CACHE_TTL_SECONDS` 설정 기반 |
| **미사용 에셋** | `images/` | No | **삭제 권장** | DB에 연결되지 않은 Orphaned 파일 처리 필요 |

## 3. 스토리지 모드 설정 (`.env`)

### [LOCAL Mode]
- **설정**: `STORAGE_MODE=local`
- 모든 파일이 백엔드 내부 `outputs/`에 물리적으로 저장됩니다.
- 단일 서버 운영 환경에 적합합니다.

### [S3/MinIO Mode]
- **설정**: `STORAGE_MODE=s3`
- 파일의 메타데이터는 DB에, 실제 바이너리는 MinIO 버킷에 저장됩니다.
- 분산 서버 환경 및 확장성이 필요한 경우 권장됩니다.
- 에셋 접근 시 `STORAGE_PUBLIC_URL`을 통해 서빙됩니다.

## 4. 백업 및 유지보수

### 데이터베이스 백업
PostgreSQL의 메타데이터는 매일 백업할 것을 권장합니다 (프로젝트 설정, 캐릭터 가중치 등 핵심 데이터 포함).

### 에셋 정리 가이드
스토리지 공간 부족 시, `_prompt_cache` 디렉토리를 수동으로 삭제해도 시스템 정합성에는 문제가 발생하지 않습니다 (단, 첫 로딩 속도가 다시 느려질 수 있음).

### 미사용 에셋 삭제 (Garbage Collection)
주기적으로 DB의 `MediaAsset` 테이블과 실제 파일 목록을 대조하여, DB에 존재하지 않는 파일을 삭제하는 스크립트 실행이 필요합니다 (현재 로드맵 포함 사항).
