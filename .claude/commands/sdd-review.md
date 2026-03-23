# /sdd-review Command

열린 PR의 코드 리뷰 + 리뷰 이슈 자동 수정을 실행하는 SDD 명령입니다.

## 실행 내용

```bash
bash /home/tomo/Workspace/shorts-producer/.claude/scripts/sdd-fix.sh
```

## 동작

### Phase 1: 코드 리뷰
1. 열린 PR 중 "Code review" 코멘트가 없는 PR 감지
2. `/code-review:code-review {PR번호}` 자동 실행
3. PR에 리뷰 코멘트 게시

### Phase 2: 자동 수정
1. "Found N issues" 코멘트가 있는 PR 감지
2. 리뷰 이후 push가 없으면 (아직 미수정)
3. 해당 브랜치에서 Claude가 리뷰 이슈 자동 수정 → push

## 전제 조건
- `gh` CLI 인증 완료
- 열린 PR이 있어야 함

> cron 5분 자동 실행과 동일한 스크립트. 즉시 실행이 필요할 때 사용.
