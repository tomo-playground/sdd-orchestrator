# YouTube Shorts Upload

> 상태: **Phase 1 완료** (7-1 #17) | 우선순위: 완료

## 배경

렌더링 완료된 영상을 수동으로 다운로드 후 YouTube Studio에서 다시 업로드해야 하는 반복 작업 발생.
Project(채널) 단위로 YouTube 계정을 연동하면 OutputTab에서 바로 업로드 가능.

## 목표

- 렌더링 완료 영상을 YouTube Shorts로 직접 업로드
- 스토리보드 메타데이터 자동 매핑 (제목, 태그)
- 업로드 이력 추적

## 결정 사항

| 항목 | 결정 |
|------|------|
| 트리거 | 수동 (OutputTab Upload 버튼) |
| 계정 연동 | Project : YouTube 채널 = 1:1 |
| 메타데이터 | 스토리보드 title/topic → YouTube 제목, Caption 해시태그 → YouTube 태그 |
| 공개 설정 | 비공개 (private) 고정 |
| 업로드 이력 | render_history 테이블 확장 (3컬럼) |
| 업로드 방식 | BackgroundTasks 비동기 |
| OAuth UX | 팝업 |

## 사용자 시나리오

### 1. YouTube 계정 연동

1. Manage > YouTube 탭 진입
2. "계정 연결" 버튼 클릭
3. Google OAuth 팝업 → 권한 승인
4. 채널명/썸네일 표시, 연동 완료

### 2. 영상 업로드

1. Studio > OutputTab에서 렌더링 완료 확인
2. "Upload to YouTube" 버튼 클릭
3. 메타데이터 편집 모달 (제목, 설명, 태그 자동 채움 + 수정 가능)
4. "업로드" 클릭 → 비동기 업로드 시작
5. 완료 시 YouTube URL 표시

### 3. 업로드 이력 확인

1. Manage > YouTube 탭에서 업로드 이력 테이블 확인
2. 썸네일, 제목, 일시, 상태, YouTube 링크

## 기술 개요

### API

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/youtube/auth/authorize?project_id={id}` | OAuth 시작 |
| GET | `/youtube/auth/callback` | OAuth 콜백 |
| DELETE | `/youtube/auth/disconnect/{project_id}` | 연동 해제 |
| POST | `/youtube/upload/{render_history_id}` | 업로드 시작 |
| GET | `/youtube/status/{render_history_id}` | 업로드 상태 조회 |

### DB 변경

**신규 테이블**: `youtube_credentials`
- `project_id` (FK, UNIQUE) — 1:1
- `channel_id`, `channel_title`
- `encrypted_access_token`, `encrypted_refresh_token`, `token_expiry`
- `is_active` (Boolean)

**확장**: `render_history`
- `youtube_video_id` (nullable)
- `youtube_uploaded_at` (nullable)
- `youtube_status` (nullable: uploading, processing, live, failed)

### Backend 구조

```
services/youtube/
├── auth.py          # OAuth2 flow + token refresh
├── client.py        # YouTube Data API v3 wrapper
├── upload.py        # 업로드 로직 + 재시도
└── exceptions.py    # QuotaExceeded, TokenExpired 등
```

### 제약 사항

- YouTube API 일일 10,000 units, 업로드 1건 = 1,600 units → **하루 최대 6건**
- OAuth scope: `youtube.upload` + `youtube.readonly` 최소 권한
- 토큰 Fernet 암호화 저장 (평문 DB 저장 금지)
- Shorts 제한: 60초 이하, 세로(9:16)

## Phase 분리

| Phase | 범위 | 상태 |
|-------|------|------|
| Phase 1 | OAuth 연동 + 수동 업로드 + 이력 저장 | **[x] 완료** |
| Phase 2 | Quota 대시보드 + 업로드 큐 | [ ] |
| Phase 3 | 예약 업로드 (스케줄링) | [ ] |

### Phase 1 구현 완료 사항
- `youtube_credentials` 테이블 (Fernet 암호화)
- `render_history` 테이블에 YouTube 업로드 트래킹 3컬럼
- `services/youtube/` 패키지 (auth, client, upload)
- `routers/youtube.py` — 5개 엔드포인트
- Frontend: YouTube Upload 모달 (메타데이터 편집 + 업로드)
- per-project OAuth credential 연동
- `useYouTubeUpload` 훅 + `youtubeActions.ts`
