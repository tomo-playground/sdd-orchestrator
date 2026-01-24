# /roadmap Command

로드맵 조회 및 업데이트를 수행하는 원자적 명령입니다.

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

## 출력 형식

```markdown
## 현재 상태: Phase 6

### 진행중
- [ ] 6-1: keywords.json 구조 개편

### 완료
- [x] 5-1: Backend 리팩토링
- [x] 5-2: Frontend 리팩토링

### 다음 작업
→ 6-1: keywords.json 구조 개편
```

## 관련 파일
- `docs/ROADMAP.md`
