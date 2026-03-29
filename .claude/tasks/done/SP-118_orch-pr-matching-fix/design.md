# SP-118 상세 설계: 오케스트레이터 PR 매칭 오류 수정

## 변경 파일 요약

| 파일 | 변경 |
|------|------|
| `sdd-orchestrator/src/sdd_orchestrator/tools/worktree.py` | `_has_open_pr()` 매칭 로직 수정 |

---

## 근본 원인

`_has_open_pr("SP-117")` → `gh pr list --search SP-117` 실행
→ GitHub search는 **부분 매칭** → "SP-111"의 PR (feat/**SP-111**-e2e-docker-ci)이 매칭됨
→ SP-117에 PR이 없는데 PR #283 반환 → auto-launch 차단

## DoD 1: PR 매칭 로직 정확 매칭

### 구현 방법
- `worktree.py:_has_open_pr()` — `--search` 대신 `--json`으로 전체 PR 조회 후 브랜치명에서 정확 매칭

### 동작 정의
```python
# before — 부분 매칭 (buggy)
["gh", "pr", "list", "--state", "open", "--search", task_id, "--json", "number", "--jq", ".[0].number"]

# after — 전체 PR 조회 후 브랜치명에서 정확 매칭
["gh", "pr", "list", "--state", "open", "--json", "number,headRefName"]
# 결과에서 headRefName에 task_id가 정확히 포함된 것만 필터
# 예: "feat/SP-117-xxx" → SP-117 매칭 O
#     "feat/SP-111-xxx" → SP-117 매칭 X
#     "fix/SP-117-yyy" → SP-117 매칭 O
```

### 매칭 규칙
- 브랜치명에서 `SP-NNN` 패턴 추출: `re.search(r"SP-\d+", headRefName)`
- 추출한 SP 번호와 `task_id` 정확 일치 비교

### 엣지 케이스
- PR이 0개 → None 반환 (정상)
- 브랜치명에 SP 번호가 없는 PR → 무시
- 같은 태스크로 여러 PR → 첫 번째 반환

### 테스트 전략
- `_has_open_pr("SP-117")` + PR 목록에 `feat/SP-111-xxx`만 있을 때 → None
- `_has_open_pr("SP-117")` + PR 목록에 `feat/SP-117-yyy`가 있을 때 → "PR #N"
- `_has_open_pr("SP-117")` + PR 목록이 비었을 때 → None

### Out of Scope
- `gh pr list` 캐싱
- 다른 _has_open_pr 호출 지점 변경 (동일 함수이므로 자동 적용)
