# GitHub Actions Self-Hosted Runner 설정 가이드

> SDD 워크플로우의 이벤트 드리븐 자동화.
> PR 코멘트 발생 시 호스트의 Claude CLI가 자동 수정 실행.

---

## 아키텍처

```
CodeRabbit/사람: PR에 코멘트
  ↓ GitHub Webhook (즉시)
GitHub Actions: sdd-review.yml 트리거
  ↓
호스트 runner (~/actions-runner/): Claude CLI로 수정 → push
  ↓
CodeRabbit: push 감지 → incremental review (자동 재리뷰)
```

호스트에서 직접 실행하므로 Claude CLI, MCP, gh, git, pytest, vitest 등 **기존 개발 환경을 그대로 사용**합니다.

---

## 설치 (최초 1회)

### 1. Runner 다운로드

```bash
mkdir -p ~/actions-runner && cd ~/actions-runner
curl -sO -L https://github.com/actions/runner/releases/download/v2.324.0/actions-runner-linux-x64-2.324.0.tar.gz
tar xzf actions-runner-linux-x64-2.324.0.tar.gz
```

### 2. 등록

```bash
TOKEN=$(gh api repos/tomo-playground/shorts-producer/actions/runners/registration-token -X POST --jq '.token')

./config.sh \
  --url https://github.com/tomo-playground/shorts-producer \
  --token "$TOKEN" \
  --name sdd-runner-1 \
  --labels self-hosted,sdd \
  --unattended --replace

# 2번째 runner (~/actions-runner-2/)
cd ~/actions-runner-2
./config.sh \
  --url https://github.com/tomo-playground/shorts-producer \
  --token "$TOKEN" \
  --name sdd-runner-2 \
  --labels self-hosted,sdd \
  --unattended
```

### 3. 기동 (2대 동시)

```bash
cd ~/actions-runner && nohup ./run.sh > /tmp/runner1.log 2>&1 &
cd ~/actions-runner-2 && nohup ./run.sh > /tmp/runner2.log 2>&1 &
```

### 4. 자동 시작 (cron @reboot)

```bash
crontab -e
# 아래 2줄 추가:
@reboot cd /home/tomo/actions-runner && nohup ./run.sh > /tmp/runner1.log 2>&1 &
@reboot cd /home/tomo/actions-runner-2 && nohup ./run.sh > /tmp/runner2.log 2>&1 &
```

---

## 운영

### 상태 확인

```bash
# GitHub에서 확인
gh api repos/tomo-playground/shorts-producer/actions/runners \
  --jq '.runners[] | {name, status}'

# 로컬 프로세스 확인
ps aux | grep 'actions-runner' | grep -v grep

# 로그 확인
tail -20 /tmp/github-runner.log
```

### 수동 재시작

```bash
# 전체 종료
pkill -f 'actions-runner.*/run.sh'

# 2대 재시작
cd ~/actions-runner && nohup ./run.sh > /tmp/runner1.log 2>&1 &
cd ~/actions-runner-2 && nohup ./run.sh > /tmp/runner2.log 2>&1 &
```

### Runner 삭제

```bash
cd ~/actions-runner
./config.sh remove --token $(gh api repos/tomo-playground/shorts-producer/actions/runners/registration-token -X POST --jq '.token')
```

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `Listening for Jobs` 안 뜸 | 토큰 만료 | 토큰 재발급 후 `./config.sh --replace` |
| Workflow 실행 안 됨 | runner offline | `ps aux \| grep actions-runner` 확인 → 재시작 |
| Claude 인증 실패 | OAuth 만료 | 호스트에서 `claude` 실행하여 재인증 |
| WSL 재시작 후 안 뜸 | cron 미실행 | `crontab -l` 확인, 수동 `./run.sh` 실행 |
