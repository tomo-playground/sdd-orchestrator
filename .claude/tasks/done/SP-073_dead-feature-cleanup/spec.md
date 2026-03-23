---
id: SP-073
title: Dead Feature Cleanup — 미사용 컬럼/코드 제거
status: done
priority: P1
scope: backend
labels: ["cleanup", "db-migration"]
assignee: stopper2008
---

## 배경
DB 스키마 전체 점검 결과, 데이터가 0건이고 사용 계획이 없는 기능 4건 확인. 컬럼 + 코드 + 문서 일괄 제거.

## DoD

- [ ] `activity_logs` Gemini 자동편집 4컬럼 DROP (`gemini_edited`, `gemini_cost_usd`, `original_match_rate`, `final_match_rate`) + 관련 코드 제거
- [ ] `loras.optimal_weight`, `calibration_score` DROP + `lora_calibration.py` 서비스 제거 + 참조 코드 정리
- [ ] `loras.civitai_id`, `gender_locked` DROP + Civitai 임포트 라우터/스크립트 제거
- [ ] `tags.thumbnail_asset_id` DROP + `tag_thumbnail.py` 서비스 제거
- [ ] Alembic 마이그레이션 작성 (1개로 통합)
- [ ] DB_SCHEMA.md + SCHEMA_SUMMARY.md 동기화
- [ ] 영향받는 테스트 정리 (삭제 또는 수정)
- [ ] Frontend 타입/참조 정리 (있다면)
- [ ] 빌드 + 테스트 통과
