---
id: SP-075
priority: P1
scope: fullstack
branch: feat/SP-075-knowledge-db
created: 2026-03-23
status: approved
approved_at: 2026-03-24
depends_on:
label: feat
---

## 무엇을 (What)
시리즈별 소재 풀(StoryCard)을 DB에서 관리하고, 대본 생성 시 Research 노드가 검증된 소재를 Writer에 자동 주입한다.

## 왜 (Why)
현재 Writer는 사용자가 입력한 topic(한 줄)만으로 Gemini가 즉흥 생성한다. 구조(Director/Critic/Review)는 잘 갖춰져 있지만 **"무엇을 쓸지"에 대한 소재가 없다.** 그 결과:
- 사실/디테일이 얕은 뻔한 대본
- 매번 Gemini 즉흥 → 품질 들쭉날쭉
- 소재 중복 관리 불가 (같은 이야기 반복)
- 채널 방향성/소재 전략 부재

소재 카드를 시리즈에 연결하면: 검증된 상황 + 공감 디테일 + 후크 각도가 Writer에 주입되어 대본 품질이 근본적으로 올라간다.

## 완료 기준 (DoD)

### DB / Model
- [ ] `story_cards` 테이블 생성 (Alembic 마이그레이션)
  - group_id FK(RESTRICT), cluster(varchar), title, status(unused/used/retired)
  - situation(text), hook_angle(text), key_moments(JSONB), emotional_arc(JSONB), empathy_details(JSONB), characters_hint(JSONB)
  - hook_score(float), used_in_storyboard_id FK(SET NULL), used_at
  - deleted_at, created_at, updated_at (SoftDeleteMixin, TimestampMixin)
- [ ] SQLAlchemy ORM `StoryCard` 모델 + Group relationship

### API
- [ ] `GET /api/v1/groups/{group_id}/story-cards` — 시리즈별 소재 목록 (status 필터, 페이지네이션)
- [ ] `POST /api/v1/groups/{group_id}/story-cards` — 소재 생성 (단건)
- [ ] `POST /api/v1/groups/{group_id}/story-cards/generate` — Gemini로 소재 대량 생성 (cluster + 개수 지정)
- [ ] `PATCH /api/v1/story-cards/{id}` — 소재 수정
- [ ] `DELETE /api/v1/story-cards/{id}` — 소재 Soft Delete

### Research 노드 연결
- [ ] Research 노드에서 group_id 기반 미사용(unused) 소재 조회 + topic 매칭 (Gemini Flash 시맨틱 선택)
- [ ] 추천된 소재를 `research_brief["story_materials"]`로 Writer에 주입
- [ ] Writer 프롬프트 빌더에 소재 카드 포맷팅 섹션 추가
- [ ] 대본 생성 완료 시 사용된 소재 status → "used" + used_in_storyboard_id 업데이트

### Gemini 소재 생성
- [ ] `POST /generate` 엔드포인트: 시리즈 컨텍스트(name, description) + cluster + 개수 → Gemini Flash로 소재 카드 배치 생성
- [ ] 생성된 소재의 hook_score를 Gemini가 자체 평가 (0.0~1.0)

### 테스트
- [ ] StoryCard CRUD API 테스트 (생성/조회/수정/삭제/필터)
- [ ] Research 노드 소재 주입 테스트 (소재 있을 때/없을 때)
- [ ] 소재 status 전환 테스트 (unused→used, used_in_storyboard_id 설정)
- [ ] Gemini 소재 생성 테스트 (모킹)
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과

## 영향 분석
- 관련 함수/파일:
  - `services/agent/nodes/research.py` — 소재 DB 조회 추가
  - `services/agent/prompt_builders_writer.py` — 소재 포맷팅 섹션
  - `models/` — StoryCard ORM 추가
  - `routers/` — story_cards 라우터 추가
- 상호작용 가능성:
  - Research 노드 확장 → Writer 입력 변경 (하위 호환: story_materials 없으면 기존 동작)
  - Group 삭제 시 story_cards RESTRICT → 삭제 차단 (기존 Group 삭제 로직 확인 필요)
- 관련 Invariant: INV-1 (404 시 자동 재생성 금지)

## 제약 (Boundaries)
- 변경 파일 10개 이하 목표
- Frontend UI는 이번 범위에 포함하지 않음 (API만 구현, UI는 후속 태스크)
- 벡터 검색(pgvector) 도입하지 않음 — Gemini Flash 시맨틱 선택으로 충분
- 소재 성과 피드백 루프 (조회수 연동)는 후속 태스크

## 힌트 (선택)
- 관련 파일: `services/agent/nodes/research.py`, `services/agent/prompt_builders_writer.py`
- 참고: 브레인스토밍에서 확정된 소재 카드 JSONB 구조 (key_moments, emotional_arc, empathy_details, characters_hint)
- Gemini 소재 생성 시 `GEMINI_SAFETY_SETTINGS` + system_instruction 분리 필수 (CLAUDE.md 규칙)
