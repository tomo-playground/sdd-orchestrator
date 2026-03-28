# /sdd-sync Command

머지 완료된 태스크를 정리하는 SDD 포스트머지 동기화 명령입니다.

## 실행 내용

```bash
bash /home/tomo/Workspace/shorts-producer/.claude/scripts/sdd-sync.sh
```

## 동작
1. `git pull` (main 최신화)
2. `current/` 태스크 중 머지된 PR 감지
3. 태스크 → `done/` 이동 + `status: done` 업데이트
4. 로컬/원격 feat 브랜치 삭제
5. worktree 디렉토리 삭제
6. **`backlog.md` 업데이트** — 완료된 태스크를 완료 섹션으로 이동 + depends 해소 표시
7. 자동 커밋 + 푸시

## 전제 조건
- main 브랜치에서 실행
- unstaged 변경 없어야 함

> cron 5분 자동 실행과 동일한 스크립트. 즉시 실행이 필요할 때 사용.
