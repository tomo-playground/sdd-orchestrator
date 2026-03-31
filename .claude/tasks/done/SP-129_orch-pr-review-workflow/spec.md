# SP-129: sdd-orchestrator PR 기반 리뷰 워크플로우

- **branch**: feat/SP-129_orch-pr-review-workflow
- **priority**: P2
- **scope**: sdd-orchestrator, .claude/scripts
- **assignee**: AI
- **created**: 2026-03-31

## 배경

sdd-orchestrator 코드가 리뷰 없이 main에 auto-push됨. main repo와 동일한 feat 브랜치 + PR + 자동 리뷰 패턴을 적용.

## DoD (Definition of Done)

- [ ] sdd-fix.sh: orchestrator auto-push를 feat 브랜치 + `gh pr create --repo tomo-playground/sdd-orchestrator`로 변경
- [ ] sdd-sync.sh: 동일
- [ ] sdd-orchestrator 레포에 `.github/workflows/pr-review.yml` 추가 (CodeRabbit 트리거)
- [ ] 경미한 변경 auto-merge 조건 정의 (CI 통과 시)
- [ ] 즉시: Slack diff 알림 추가 (PR 워크플로우 구축 전 임시 가시성)

## 수정 대상 파일

- `.claude/scripts/sdd-fix.sh`
- `.claude/scripts/sdd-sync.sh`
- `sdd-orchestrator/.github/workflows/pr-review.yml` (신규)
