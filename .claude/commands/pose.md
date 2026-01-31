# /pose Command

포즈 에셋 분석, 동기화, 카테고리 재분류를 수행하는 원자적 명령입니다.

## 사용법

```
/pose [action]
```

### Actions

| Action | 설명 |
|--------|------|
| (없음) | 현재 등록된 전체 포즈 목록 및 상태 조회 |
| `audit` | DB 내 실제 프롬프트를 분석하여 지원되지 않는 포즈(Gap) 식별 |
| `sync` | 로컬 포즈 에셋을 S3(Minio) 저장소로 일괄 동기화 |
| `reclassify` | 태그 카테고리가 잘못 지정된 항목(예: scene -> pose)을 자동 재분류 |
| `doc` | 포즈 관리 실무 가이드(`docs/POSE_MAINTENANCE.md`) 표시 |

## 실행 내용

### 조회 (기본)
1. `backend/services/controlnet.py`의 `POSE_MAPPING` 읽기
2. `backend/assets/poses/` 내 실제 파일 존재 여부 확인
3. 상태 요약 출력 (지원 개수, 누락 파일 등)

### audit
1. `scripts/final_audit.py` 실행
2. 유저가 가장 많이 요청했지만 현재 시스템에 없는 포즈 10종 출력
3. 보충이 필요한 포즈 제안

### sync
1. `scripts/sync_poses.py` 실행
2. 로컬 <-> S3 동기화 결과 출력

### reclassify
1. `scripts/reclassify_tags.py` 실행
2. 카테고리가 변경된 태그 수와 최종 분포 출력

## 관련 파일
- `backend/services/controlnet.py` (매핑 소스)
- `backend/assets/poses/` (에셋 위치)
- `docs/POSE_MAINTENANCE.md` (상세 가이드)
- `scripts/final_audit.py`
- `scripts/sync_poses.py`
- `scripts/reclassify_tags.py`
