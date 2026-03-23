# /sdd-fix Command

리뷰 이슈를 자동 수정하는 SDD 명령입니다.

## 실행 내용

```bash
bash /home/tomo/Workspace/shorts-producer/.claude/scripts/sdd-fix.sh
```

## 동작
1. "Found N issues" 코멘트가 있는 열린 PR 감지
2. 리뷰 이후 push가 없으면 (아직 미수정)
3. 해당 브랜치에서 Claude가 리뷰 이슈 자동 수정 → push

## 전제 조건
- `gh` CLI 인증 완료
- 열린 PR이 있어야 함

> cron 5분 자동 실행과 동일한 스크립트. 즉시 실행이 필요할 때 사용.
