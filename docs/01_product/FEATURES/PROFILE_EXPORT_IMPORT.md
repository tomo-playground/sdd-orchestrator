# Profile Export/Import

> 상태: 미착수

## 배경

Style Profile(Model + LoRA + Embeddings 세트)을 다른 환경이나 사용자와 공유할 수 없음.

## 목표

- Style Profile을 JSON 파일로 Export
- JSON 파일에서 Import하여 프로필 복원
- 프로필 공유를 통한 협업 지원

## 범위

| 항목 | 설명 |
|------|------|
| Export | Profile → JSON (Model, LoRA, Embedding 메타데이터) |
| Import | JSON → Profile 생성 (누락 에셋 경고) |
| Validation | Import 시 모델/LoRA 존재 여부 검증 |
| UI | Manage > Style 탭에 Export/Import 버튼 |

## 수락 기준

| # | 기준 |
|---|------|
| 1 | Profile을 JSON으로 Export 가능 |
| 2 | JSON에서 Profile Import 가능 |
| 3 | 누락 에셋(Model, LoRA) 발견 시 경고 표시 |
