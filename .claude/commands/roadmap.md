# /roadmap Command

로드맵 조회, 업데이트, 아카이브를 수행하는 원자적 명령입니다.

## 사용법

```
/roadmap [action]
```

### Actions

| Action | 설명 |
|--------|------|
| (없음) | 현재 Phase 및 진행 상태 조회 |
| `next` | 다음 작업 항목 조회 |
| `update <item>` | 항목 완료 처리 |
| `status` | 전체 진행률 요약 (Phase별 완료율) |
| `archive` | 완료된 Phase를 요약으로 압축 |

## 실행 내용

### 조회 (기본)
1. `docs/ROADMAP.md` 읽기
2. 현재 Phase 파싱
3. 완료/진행중/대기 항목 요약

### next
1. 로드맵에서 첫 번째 미완료 항목 찾기
2. 해당 항목의 상세 내용 출력

### update
1. 지정된 항목을 `[x]`로 변경
2. 날짜 추가 (완료일)

### status
1. 각 Phase별 `[x]` / `[ ]` 개수 집계
2. 완료율 계산 (완료/전체)
3. 요약 테이블 출력

**출력 예시:**
```markdown
## Roadmap Status

| Phase | 완료 | 전체 | 진행률 | 상태 |
|-------|------|------|--------|------|
| 1 | 6 | 6 | 100% | COMPLETE |
| 2 | 5 | 5 | 100% | COMPLETE |
| 3 | 10 | 10 | 100% | COMPLETE |
| 4 | 3 | 3 | 100% | COMPLETE |
| 5 | 4 | 4 | 100% | COMPLETE |
| 6 | 8 | 15 | 53% | IN PROGRESS |

**아카이브 대상**: Phase 1-5 (100% 완료)
→ `/roadmap archive` 실행 시 요약으로 압축됩니다.
```

### archive
1. 100% 완료된 Phase 자동 감지
2. 해당 Phase의 상세 테이블을 요약문으로 변환
3. 사용자에게 변경 내용 미리보기 제공
4. 승인 후 ROADMAP.md 업데이트

**아카이브 규칙:**
- 100% 완료된 Phase만 대상
- 현재 진행 중인 Phase는 제외
- 요약 시 주요 성과만 유지 (상세 테이블 제거)

**변환 예시:**

Before:
```markdown
## Phase 3: 리팩토링 - **COMPLETE**

### 3-1. Backend 리팩토링
| 작업 | 설명 | 상태 |
|------|------|------|
| Router 분리 | `main.py` → `routers/` | [x] |
| Service 분리 | `logic.py` → `services/` | [x] |
...
```

After:
```markdown
## Phase 1-5: Foundation & Refactoring - **ARCHIVED**

완료된 주요 성과:
- Phase 1: 기본 기능 구현 (FastAPI + Next.js + FFmpeg)
- Phase 2: VRT 안정성 기반 구축 (Golden Master + SSIM)
- Phase 3: Backend/Frontend 리팩토링 (logic.py 88% 감소, page.tsx 57% 감소)
- Phase 4: 안정성 검증 완료 (VRT 36/36 통과)
- Phase 5: 기능 확장 (Post Card, 오버레이 시스템)

> 상세 이력: `git log --oneline docs/ROADMAP.md` 참조
```

## 출력 형식

```markdown
## 현재 상태: Phase 6-3

### 진행중
- [ ] 9.2: 포즈/표정/구도 태그 확장

### 완료
- [x] 6-1: DB 스키마 설정 (PostgreSQL)
- [x] 6-2: Studio Integration
- [x] 9.1: DB 태그 통합 (keywords.json 제거)

### 다음 작업
→ 9.2: Gemini 템플릿 강화
```

## 관련 파일
- `docs/ROADMAP.md`
