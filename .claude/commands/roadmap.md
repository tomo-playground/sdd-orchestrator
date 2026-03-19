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
| `features` | 미구현 기능 명세 목록 조회 |

## 실행 내용

### 조회 (기본)
1. `docs/01_product/ROADMAP.md` 읽기
2. 현재 Phase 파싱
3. 완료/진행중/대기 항목 요약

### next
1. 로드맵에서 첫 번째 미완료 항목 찾기
2. `docs/01_product/FEATURES/` 에서 해당 기능 명세 확인
3. 해당 항목의 상세 내용 출력

### update
1. 지정된 항목을 `[x]`로 변경
2. 날짜 추가 (완료일)

### status
1. 각 Phase별 `[x]` / `[ ]` 개수 집계
2. 완료율 계산 (완료/전체)
3. 요약 테이블 출력

### features
1. `docs/01_product/FEATURES/` 디렉토리 스캔
2. 각 파일의 상태(미착수/진행중/완료) 파싱
3. 기능 명세 목록 테이블 출력

### archive
1. 100% 완료된 Phase 자동 감지
2. 해당 Phase의 상세 테이블을 요약문으로 변환
3. 사용자에게 변경 내용 미리보기 제공
4. 승인 후 ROADMAP.md 업데이트

## ROADMAP vs Backlog (혼용 금지)

| 용어 | 역할 | 위치 |
|------|------|------|
| **Roadmap** | 제품 방향, Phase, 마일스톤 | `docs/01_product/ROADMAP.md` |
| **Backlog** | 실행 가능한 태스크 큐 | `.claude/tasks/backlog.md` |

- `/roadmap`은 Phase/마일스톤 조회·관리 전용.
- 개별 태스크 관리는 `.claude/tasks/` (backlog → current → done).
- `/roadmap next`는 ROADMAP 기준 다음 방향을 제시하되, 실행 태스크는 Backlog에서 선택.

## 관련 파일
- `docs/01_product/ROADMAP.md` - 마스터 로드맵 (Phase/마일스톤)
- `.claude/tasks/backlog.md` - 실행 가능한 태스크 큐 (우선순위)
- `docs/01_product/FEATURES/` - 기능별 명세서
- `docs/01_product/PRD.md` - 제품 요구사항
