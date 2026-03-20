# GitHub Actions Self-Hosted Runner 설정 가이드

> SDD 워크플로우의 이벤트 드리븐 자동화를 위한 self-hosted runner 구축 가이드.
> cron 폴링 대신 GitHub Webhook으로 PR 코멘트 발생 시에만 자동 수정을 실행합니다.

---

## 아키텍처

```
CodeRabbit/사람: PR에 코멘트
  ↓ GitHub Webhook (즉시)
GitHub Actions: sdd-review.yml 트리거
  ↓
Self-hosted Runner (Docker): claude --worktree → 수정 → push
  ↓
CodeRabbit: push 감지 → incremental review (자동 재리뷰)
```

### 기존 (cron) vs 변경 (이벤트 드리븐)

| 항목 | cron (이전) | self-hosted runner (현재) |
|------|-----------|------------------------|
| 트리거 | 5분 폴링 | 코멘트 이벤트 즉시 |
| Claude 기동 | 매 5분 (할 일 없어도) | 코멘트 있을 때만 |
| 비용 | 불필요한 API 호출 | 이벤트당만 |
| 업계 표준 | No | Yes |

---

## 초기 설정

### 1. Runner 등록 토큰 발급

```bash
gh api repos/tomo-playground/shorts-producer/actions/runners/registration-token \
  -X POST --jq '.token'
```

> 토큰은 1시간 유효. 만료 시 재발급 필요.

### 2. .env.runner 생성

```bash
cd ~/Workspace/shorts-producer
cp .env.runner.example .env.runner  # 또는 직접 편집
```

```env
RUNNER_TOKEN=AAGHWNYA44BA...   # 위에서 발급한 토큰
```

### 3. Runner 컨테이너 기동

```bash
docker compose -f docker-compose.runner.yml up -d
```

### 4. 등록 확인

```bash
# GitHub에서 runner 상태 확인
gh api repos/tomo-playground/shorts-producer/actions/runners --jq '.runners[] | {name, status, labels: [.labels[].name]}'
```

정상이면:
```json
{
  "name": "sdd-runner",
  "status": "online",
  "labels": ["self-hosted", "sdd"]
}
```

---

## 동작 방식

### 트리거 이벤트

| 이벤트 | 동작 |
|--------|------|
| PR에 일반 코멘트 (`issue_comment`) | 자동 수정 실행 |
| PR에 인라인 리뷰 코멘트 (`pull_request_review_comment`) | 자동 수정 실행 |
| 봇 코멘트 (CodeRabbit, GitHub Actions) | 스킵 (무한 루프 방지) |
| 이미 수정된 PR (push > 코멘트) | 스킵 |

### 실행 흐름

```
1. 코멘트 이벤트 감지
2. PR 번호 추출
3. 봇 코멘트 여부 확인 → 봇이면 스킵
4. 마지막 push vs 마지막 코멘트 시각 비교 → 이미 수정됐으면 스킵
5. PR 브랜치명 조회
6. claude --worktree {branch} 로 격리 수정
7. 수정 → commit → push → PR 코멘트
```

---

## 운영

### 로그 확인

```bash
# Runner 컨테이너 로그
docker logs shorts-producer-github-runner-1 --tail 50

# GitHub Actions 실행 이력
gh run list --workflow sdd-review.yml --limit 10
```

### Runner 중지/재시작

```bash
# 중지
docker compose -f docker-compose.runner.yml down

# 재시작
docker compose -f docker-compose.runner.yml restart

# 토큰 만료 시 재등록
docker compose -f docker-compose.runner.yml down
# 새 토큰 발급 → .env.runner 업데이트
docker compose -f docker-compose.runner.yml up -d
```

### Runner 삭제 (사용 안 할 때)

```bash
docker compose -f docker-compose.runner.yml down -v
gh api repos/tomo-playground/shorts-producer/actions/runners/{runner_id} -X DELETE
```

---

## 트러블슈팅

### Runner가 offline 상태

```bash
# 컨테이너 상태 확인
docker ps | grep github-runner

# 로그 확인
docker logs shorts-producer-github-runner-1

# 토큰 만료가 원인이면 재등록
gh api repos/tomo-playground/shorts-producer/actions/runners/registration-token -X POST --jq '.token'
# .env.runner 업데이트 후 재시작
```

### Claude CLI 인증 실패

```bash
# 호스트에서 Claude 인증 상태 확인
claude --version

# 볼륨 마운트 확인
docker exec shorts-producer-github-runner-1 ls -la /home/runner/.claude/
```

### Workflow가 트리거 안 됨

```bash
# Actions 활성화 확인
gh api repos/tomo-playground/shorts-producer/actions/permissions --jq '.enabled'

# Workflow 파일 확인
gh workflow list
```

---

## 보안 고려사항

- `.env.runner`는 `.gitignore`에 포함 — git에 커밋되지 않음
- Claude 인증 파일은 `:ro` (읽기 전용) 마운트
- Runner는 `repo` 스코프 — 이 리포지토리에만 접근
- 봇 코멘트 스킵 로직으로 무한 루프 방지
