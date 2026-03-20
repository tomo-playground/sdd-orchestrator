---
id: SP-010
priority: P1
scope: fullstack
branch: feat/SP-010-api-proxy-internal
created: 2026-03-20
status: done
depends_on:
label: enhancement
reviewer: stopper2008
assignee: stopper2008
---

## 무엇을
Frontend API 호출을 Next.js rewrite 프록시 경유로 전환하여, FastAPI 서버(8000)를 외부 네트워크에 노출하지 않고 Next.js(3000)만으로 서비스 제공

## 왜
현재 브라우저가 `NEXT_PUBLIC_API_URL`(8000번)을 직접 호출하므로 외부 배포 시 API 서버도 public 노출이 필수. 서버-to-서버 프록시 방식으로 전환하면 3000번 포트만 열어도 서비스가 동작하고, 보안상 API 서버를 internal network에 숨길 수 있다.

## 수정 포인트 (7개)

### 1. `frontend/app/constants/index.ts` — API 경로를 상대 경로로 (핵심)
```typescript
// Before
export const API_ROOT = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const API_BASE = `${API_ROOT}/api/v1`;
export const ADMIN_API_BASE = `${API_ROOT}/api/admin`;

// After
export const API_ROOT = "";  // 상대 경로 -> same-origin -> rewrite 프록시 경유
export const API_BASE = "/api/v1";
export const ADMIN_API_BASE = "/api/admin";
```
- 81개 파일이 이 상수를 import -> 이 파일만 수정하면 전체 자동 반영

### 2. `frontend/next.config.ts` — rewrite 규칙 수정 (버그 수정)
```typescript
// Before (버그: /api prefix 제거됨)
{ source: "/api/:path*", destination: "http://127.0.0.1:8000/:path*" }

// After (/api prefix 보존)
{ source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" }
```
- 백엔드 라우터가 `/api/v1`, `/api/admin` prefix 사용 (routers/__init__.py 확인 완료)
- `/outputs/:path*`, `/assets/:path*` rewrite는 그대로 유지
- `/health` rewrite 추가 필요 (수정 포인트 7 참조)

### 3. `frontend/app/utils/url.ts` — resolveImageUrl() 수정
```typescript
// Before: API_ROOT이 "http://localhost:8000"이라 절대 URL 생성
return url.startsWith("http") ? url : `${API_ROOT}${url}`;

// After: API_ROOT=""이므로 상대 경로 그대로 반환 -> rewrite 경유
// 로직 변경 불필요, API_ROOT="" 반영으로 자동 동작
// 단, 테스트에서 `result!.startsWith("http")` 검증이 실패할 수 있음
```

### 4. `frontend/app/utils/__tests__/url.test.ts` — 테스트 기대값 수정
```typescript
// Before: API_ROOT이 절대 URL이라 http로 시작하는 결과 기대
expect(result!.startsWith("http")).toBe(true);

// After: 상대 경로이므로 /로 시작
expect(result!.startsWith("/")).toBe(true);
```

### 5. `frontend/app/components/shell/ConnectionGuard.tsx` — 하드코딩된 포트 치환 제거
```typescript
// Before: 8000 -> 9000 포트 치환 (MinIO 직접 접근)
const VIDEO_URL = `${API_BASE.replace(":8000", ":9000")}/shorts-producer/shared/video/connection_loading.mp4`;

// After: 이 비디오를 어떻게 서빙할지 결정 필요
// 옵션 A: next.config.ts에 MinIO rewrite 추가
// 옵션 B: 백엔드 static 경로로 서빙
// 옵션 C: public/ 폴더에 배치
```
- `API_BASE.replace(":8000", ":9000")`는 상대 경로에서는 동작하지 않음 -> 반드시 수정 필요
- SP-009 분석: 이 VIDEO_URL은 이미 broken (MinIO에 해당 파일 없음, 현재도 404)
- **권장: VIDEO_URL 라인 제거 (dead feature)**. 캐릭터 프리뷰 fallback은 정상 동작

### 6. `frontend/.env.local` — 환경변수 정리
```bash
# Before
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE=http://localhost:8000

# After: 두 변수 모두 불필요 -> 제거 또는 주석 처리
# NEXT_PUBLIC_API_URL은 더 이상 사용하지 않음
# NEXT_PUBLIC_API_BASE는 코드에서 참조 0건 (이미 dead)
```

### 7. `frontend/app/hooks/useBackendHealth.ts` — health 체크 경로
```typescript
// Before
await axios.get(`${API_ROOT}/health`, { timeout: 5_000 });

// After: API_ROOT=""이면 "/health"가 됨
// -> next.config.ts rewrite에서 /health가 백엔드로 프록시되는지 확인 필요
// 현재 rewrite: /api/:path* -> 매칭 안됨!
// 해결: rewrite에 { source: "/health", destination: "http://127.0.0.1:8000/health" } 추가
```

## 런타임 리스크 (반드시 검증)

### R1. SSE(EventSource) 프록시 호환성
- `renderWithProgress.ts`, `generateWithProgress.ts`에서 SSE 사용
- Next.js rewrite는 HTTP 프록시 — SSE(long-lived connection) 전달 시 **버퍼링** 이슈 가능
- Next.js는 기본적으로 SSE를 프록시할 수 있지만, 프레임워크 버전에 따라 동작이 다를 수 있음
- **검증 방법**: 실제 이미지 생성/렌더링 실행하여 progress 이벤트가 실시간 도착하는지 확인
- **폴백**: 이미 polling 폴백 로직이 있음 (`startPolling()`) — SSE 실패 시 자동 전환

### R2. MinIO URL이 백엔드 응답에 절대 경로로 포함
- 백엔드가 `STORAGE_PUBLIC_URL`(기본값 `http://localhost:9000`)로 이미지/비디오 URL 생성
- 이 URL은 API 응답의 `image_url`, `video_url`, `reference_image_url` 등에 포함
- **브라우저가 이 URL을 직접 요청** -> MinIO(9000)도 외부 노출 필요
- 이번 태스크에서는 **API 서버(8000) 비노출**만 목표. MinIO(9000) 비노출은 별도 태스크
- **당장 해결 불필요하지만 인지 필요**: 완전한 single-port 서빙을 위해서는 MinIO도 프록시 필요

### R3. Long-running 요청 타임아웃
- 이미지 생성(5분), 렌더링(20분) 등 장시간 요청이 존재
- Next.js rewrite 프록시의 기본 타임아웃 확인 필요
- 다만 이 요청들은 async 패턴: POST로 task_id 받고(짧은 요청) -> SSE/polling으로 추적
- POST 자체는 60초 이내 응답이므로 **타임아웃 리스크 낮음**

### R4. Request body 크기 제한
- Next.js 기본 body size limit: 1MB (API Routes), rewrite는 제한 없음
- 현재 대용량 POST는 없음 (이미지는 base64로 전송되는 경우가 있을 수 있음)
- **리스크 낮음**: rewrite는 API Routes와 달리 body size 제한이 없음

## 완료 기준 (DoD)
- [ ] 수정 포인트 1~7 전체 반영
- [ ] SSE(EventSource) rewrite 프록시 경유 시 실시간 이벤트 수신 확인 (R1)
- [ ] 이미지/비디오 URL(MinIO) 로딩 정상 확인 (R2 인지, 이번 스코프 아님)
- [ ] 8000번 포트 미노출 상태에서 3000번만으로 API 호출 동작 확인
- [ ] 기존 테스트(vitest) 통과
- [ ] 기존 E2E 테스트 통과 (있는 경우)

## 제약
- 변경 파일 10개 이하 목표
- 건드리면 안 되는 것: 백엔드 라우터 prefix, API 응답 구조, MinIO 설정
- 의존성 추가 금지
- scope가 fullstack인 이유: ConnectionGuard 비디오 서빙 방식에 따라 백엔드 또는 next.config 추가 수정 가능

## 스코프 밖 (Won't)
- MinIO(9000) 프록시화 — 별도 태스크로 분리
- 백엔드 CORS 설정 간소화 — 프록시 전환 후 optional 최적화
- 프로덕션 배포 설정 (Nginx, SSL 등)

## 힌트
- 81개 파일이 API_ROOT/API_BASE/ADMIN_API_BASE import -> constants 수정으로 대부분 자동 해결
- 개별 수정 필요: ConnectionGuard (포트 치환), useBackendHealth (/health 경로), url.test.ts (기대값)
- 백엔드 CORS 설정 (`backend/main.py:177-183`): 프록시 전환 후 same-origin이 되므로 CORS 설정 간소화 가능 (optional, 이 태스크 스코프 밖)
- SP-009(환경 표준화)와 겹치는 파일: next.config.ts, ConnectionGuard.tsx, .env.local — **SP-010을 먼저 수행** 권장
