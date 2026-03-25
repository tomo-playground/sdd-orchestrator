# /tunnel Command

Cloudflare 빠른 터널로 로컬 서비스를 외부에 임시 노출합니다.

## 사용법

```
/tunnel [target]
```

### Targets

| Target | 설명 | 포트 |
|--------|------|------|
| `frontend` | Frontend만 노출 | 3000 |
| `backend` | Backend API만 노출 | 8000 |
| `all` | Frontend + Backend 동시 노출 | 3000, 8000 |
| (없음) | `all`과 동일 |

## 실행 내용

### 1. cloudflared 설치 확인
```bash
which cloudflared || echo "cloudflared 미설치"
```

미설치 시 안내:
```bash
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
```

### 2. 대상 서비스 헬스체크
터널 기동 전 대상 서비스가 살아있는지 확인:
```bash
curl -s http://localhost:3000 > /dev/null   # Frontend
curl -s http://localhost:8000/health         # Backend
```

죽어있으면 터널 기동하지 않고 "서비스를 먼저 시작하세요" 안내.

### 3. 터널 기동
각 터널은 **백그라운드**로 실행. 로그에서 trycloudflare.com URL을 파싱하여 사용자에게 출력.

```bash
# Frontend 터널
cloudflared tunnel --url http://localhost:3000 2>&1 &

# Backend 터널
cloudflared tunnel --url http://localhost:8000 2>&1 &
```

### 4. 기존 터널 감지
이미 cloudflared 프로세스가 실행 중이면 중복 기동하지 않고 기존 PID 표시.

```bash
ps aux | grep "cloudflared tunnel" | grep -v grep
```

### 5. 터널 종료
`/tunnel stop` 으로 모든 cloudflared 터널 프로세스를 종료.

```bash
pkill -f "cloudflared tunnel"
```

## 출력 형식

```markdown
## Cloudflare Tunnel

| 서비스 | 로컬 | 외부 URL |
|--------|------|----------|
| Frontend | localhost:3000 | https://xxx-xxx.trycloudflare.com |
| Backend | localhost:8000 | https://yyy-yyy.trycloudflare.com |

> 임시 URL입니다. cloudflared 프로세스 종료 시 비활성화됩니다.
> Frontend에서 Backend API를 호출하려면 NEXT_PUBLIC_API_URL을 Backend 터널 URL로 설정하세요.
```

## 주의사항

- 임시 터널은 계정 없이 동작하지만 uptime 보장 없음
- ICMP proxy 경고(ping_group_range)는 무시해도 무방
- 민감 데이터(DB, .env)는 노출되지 않음 (웹 서비스 포트만 터널링)
