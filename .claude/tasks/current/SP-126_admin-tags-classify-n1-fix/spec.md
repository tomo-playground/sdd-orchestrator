# SP-126: Admin tags/classify N+1 쿼리 최적화

- **branch**: feat/SP-126_admin-tags-classify-n1-fix
- **priority**: P3
- **scope**: backend
- **assignee**: AI
- **created**: 2026-03-31
- **issue**: #307

## 배경

`/api/admin/tags/classify`에서 N+1 쿼리 발생 (Sentry #307, info 레벨, 2회).
`TagClassifier.classify_batch()`가 태그마다 `_save_classification()`, `_lookup_db()`를 개별 호출.

### 영향

- Admin 전용 API, 사용 빈도 낮음
- 최대 50개 태그 → 최대 50회 개별 쿼리

## DoD (Definition of Done)

- [ ] `_lookup_db()` → 배치 쿼리로 변환 (WHERE name IN (...))
- [ ] `_save_classification()` → bulk insert/update로 변환
- [ ] 기존 테스트 통과 + N+1 회귀 테스트 추가

## 수정 대상 파일

- `backend/services/tag_classifier.py` — classify_batch, _lookup_db, _save_classification
