# SP-075 상세 설계: 지식DB 스토리 카드

## 규모 판단
- **변경 파일**: 13개 (신규 5 + 수정 8)
- **DB 변경**: 있음 (story_cards 테이블 신규)
- **API 변경**: 있음 (5개 엔드포인트 신규)
- **설계 깊이**: 풀 설계 (6항목)

---

## DoD 1: `story_cards` 테이블 + ORM 모델

### 구현 방법
**신규 파일**: `backend/models/story_card.py`

```python
class StoryCard(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "story_cards"

    id: Mapped[int] (PK)
    group_id: Mapped[int] (FK → groups.id, ondelete="RESTRICT")
    cluster: Mapped[str | None] (VARCHAR(100)) -- 소재 분류 (예: "첫 만남", "위기 극복")
    title: Mapped[str] (VARCHAR(300))
    status: Mapped[str] (VARCHAR(20), default="unused") -- unused | used | retired

    # 소재 본문
    situation: Mapped[str | None] (Text) -- 상황 설명
    hook_angle: Mapped[str | None] (Text) -- 후크 각도
    key_moments: Mapped[list | None] (JSONB) -- 핵심 장면 리스트 ["순간1", "순간2"]
    emotional_arc: Mapped[dict | None] (JSONB) -- {"start": "호기심", "peak": "충격", "end": "감동"}
    empathy_details: Mapped[list | None] (JSONB) -- 공감 디테일 ["구체 상황1", ...]
    characters_hint: Mapped[dict | None] (JSONB) -- {"speaker_a": "...", "speaker_b": "..."}

    # 메타
    hook_score: Mapped[float | None] (Float) -- Gemini 자체 평가 0.0~1.0
    used_in_storyboard_id: Mapped[int | None] (FK → storyboards.id, ondelete="SET NULL")
    used_at: Mapped[datetime | None] (DateTime)
```

**수정 파일**: `backend/models/__init__.py` -- StoryCard import + `__all__` 등록
**수정 파일**: `backend/models/group.py` -- `story_cards` relationship 추가 (TYPE_CHECKING + lazy="select")

### 동작 정의
- `group_id`는 NOT NULL FK (RESTRICT). Group 삭제 시 story_cards가 있으면 삭제 차단.
- `used_in_storyboard_id`는 nullable FK (SET NULL). Storyboard 삭제 시 자동 null.
- `status` 3상태: unused(미사용) → used(대본에 사용됨) → retired(수동 보관).
- SoftDeleteMixin 사용 → `deleted_at` 컬럼 자동.

### 엣지 케이스
- Group 삭제 시 RESTRICT → 409 에러. 기존 `delete_group()`에서 active storyboards만 체크하지만, story_cards는 DB 레벨 RESTRICT가 처리. soft delete는 FK 체크 안 걸림 (deleted_at만 설정이므로).
  - **정정**: soft delete는 실제 DELETE가 아니므로 FK RESTRICT 안 걸림. `permanently_delete_group()`에서만 걸림. 영구 삭제 시 story_cards cascade 정리 필요 → `permanently_delete_group()`에 story_cards 영구 삭제 추가.
- `used_in_storyboard_id` 참조 storyboard가 soft delete 되어도 FK는 유지. status는 "used" 유지 (재사용 방지).

### 영향 범위
- `routers/groups.py` `permanently_delete_group()` — story_cards 영구 삭제 로직 추가 필요.
- 마이그레이션: `sp075_create_story_cards` (revision chain: sp073a0000001 → sp075a0000001).

### 테스트 전략
- ORM 모델 인스턴스 생성 + commit + 조회 검증.
- FK 제약: group_id 없는 StoryCard 생성 시 IntegrityError.

### Out of Scope
- 벡터 임베딩 (pgvector) — spec에서 명시적 제외.
- story_cards에 media_asset_id (이미지 첨부) — 후속.

---

## DoD 2: CRUD API (5개 엔드포인트)

### 구현 방법
**신규 파일**: `backend/routers/story_cards.py`

```
service_router: /groups/{group_id}/story-cards
  GET  /                          — 목록 (status 필터, offset/limit 페이지네이션)
  POST /                          — 단건 생성
  POST /generate                  — Gemini 배치 생성

admin_router 없음 (서비스 API만)

독립 경로:
  PATCH  /story-cards/{id}        — 수정
  DELETE /story-cards/{id}        — Soft Delete
```

API가 두 가지 prefix를 사용하므로 라우터를 2개로 분리:
- `group_scoped_router = APIRouter(prefix="/groups", tags=["story-cards"])` — GET/POST
- `item_router = APIRouter(prefix="/story-cards", tags=["story-cards"])` — PATCH/DELETE

**수정 파일**: `backend/routers/__init__.py` — 두 라우터 모두 service_app_router에 등록.

**신규 파일**: `backend/services/story_card.py` — 서비스 레이어 (CRUD + generate)

**수정 파일**: `backend/schemas.py` — Pydantic 스키마 추가

```python
class StoryCardCreate(BaseModel):
    cluster: str | None = None
    title: str = Field(max_length=300)
    situation: str | None = None
    hook_angle: str | None = None
    key_moments: list[str] | None = None
    emotional_arc: dict | None = None
    empathy_details: list[str] | None = None
    characters_hint: dict | None = None

class StoryCardUpdate(BaseModel):
    cluster: str | None = None
    title: str | None = Field(default=None, max_length=300)
    status: str | None = Field(default=None, pattern="^(unused|used|retired)$")
    situation: str | None = None
    hook_angle: str | None = None
    key_moments: list[str] | None = None
    emotional_arc: dict | None = None
    empathy_details: list[str] | None = None
    characters_hint: dict | None = None

class StoryCardResponse(BaseModel):
    id: int
    group_id: int
    cluster: str | None = None
    title: str
    status: str
    situation: str | None = None
    hook_angle: str | None = None
    key_moments: list[str] | None = None
    emotional_arc: dict | None = None
    empathy_details: list[str] | None = None
    characters_hint: dict | None = None
    hook_score: float | None = None
    used_in_storyboard_id: int | None = None
    used_at: datetime | None = None
    created_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)

class StoryCardGenerateRequest(BaseModel):
    cluster: str = Field(max_length=100)
    count: int = Field(default=5, ge=1, le=20)

class StoryCardListResponse(BaseModel):
    items: list[StoryCardResponse]
    total: int
```

### 동작 정의

**GET /groups/{group_id}/story-cards**
- Query params: `status` (optional, "unused"/"used"/"retired"), `cluster` (optional), `offset`, `limit`
- soft delete 필터 (`deleted_at.is_(None)`)
- 정렬: `hook_score DESC NULLS LAST, created_at DESC`
- 응답: `StoryCardListResponse` (items + total)

**POST /groups/{group_id}/story-cards**
- group_id 존재 검증 (없으면 404)
- StoryCardCreate body → StoryCard ORM 생성
- status 기본값: "unused"
- 응답: `StoryCardResponse`

**POST /groups/{group_id}/story-cards/generate**
- DoD 4에서 상세 설명 (Gemini 소재 생성)
- 응답: `list[StoryCardResponse]`

**PATCH /story-cards/{id}**
- soft delete 필터 필수
- StoryCardUpdate body → 부분 업데이트 (None 필드 무시)
- status 변경 시 "used"로 바꿀 때 used_at 자동 설정, "unused"로 바꿀 때 used_at/used_in_storyboard_id 초기화
- 응답: `StoryCardResponse`

**DELETE /story-cards/{id}**
- soft delete (deleted_at = now())
- 응답: `{"status": "deleted", "id": id}`

### 엣지 케이스
- group_id 경로 파라미터와 실제 StoryCard.group_id 불일치 방지 → GET에서 group_id 기반 필터로 자연 해결.
- PATCH에서 status를 "used"로 수동 변경할 때 used_in_storyboard_id는 수동 설정 가능 (API에서 직접 연결).
- 동일 group에 같은 title 중복 허용 (유니크 제약 없음, 다른 cluster에서 유사 소재 가능).

### 영향 범위
- `routers/__init__.py` — 라우터 등록 2개 추가.
- `schemas.py` — 5개 스키마 클래스 추가.

### 테스트 전략
- CRUD 단위 테스트: 생성 → 조회 → 수정 → 삭제.
- 필터 테스트: status/cluster 필터, 페이지네이션.
- 404: 존재하지 않는 group_id, 존재하지 않는 story_card id.
- soft delete된 카드 PATCH → 404.

### Out of Scope
- 대량 삭제 (bulk delete) — 필요 시 후속.
- 소재 카드 복원 (restore) — 필요 시 후속.

---

## DoD 3: Research 노드 소재 주입

### 구현 방법

**수정 파일**: `backend/services/agent/tools/research_tools.py`
- 새 도구 `get_story_cards` 정의 추가 (group_id → unused 소재 조회)
- `create_research_executors()`에 실행 함수 추가

```python
# 도구 정의
define_tool(
    name="get_story_cards",
    description="시리즈(그룹)에 등록된 미사용 소재 카드를 조회합니다. 대본 작성 시 검증된 소재를 활용할 수 있습니다.",
    parameters={
        "group_id": {"type": "integer", "description": "그룹(시리즈) ID"},
        "topic": {"type": "string", "description": "현재 주제 (시맨틱 매칭용)"},
        "limit": {"type": "integer", "description": "조회 개수 (기본값: 10)"},
    },
    required=["group_id"],
)
```

실행 함수 내부 로직:
1. DB에서 `StoryCard.group_id == group_id AND status == "unused" AND deleted_at IS NULL` 조회
2. topic이 주어지면 Gemini Flash로 시맨틱 매칭 (간단 프롬프트: "아래 소재 중 topic과 가장 관련 있는 3개 선택")
3. topic이 없거나 Gemini 실패 시 hook_score 상위 N개 반환
4. 결과를 포맷팅하여 문자열 반환

**주의**: DB 세션은 `create_research_executors()`에서 받은 `db` 파라미터 사용. 이미 research_tools 전체가 db 세션을 클로저로 캡처하는 패턴.

**수정 파일**: `backend/services/agent/nodes/research.py`
- `prompt_parts`에 get_story_cards 도구 가이드 추가: "그룹 ID가 있고 검증된 소재가 필요하면 get_story_cards를 호출하세요."
- Research 노드 결과에서 소재 카드 정보를 `research_brief`에 병합 — `structured_brief`에 `"story_materials"` 키 추가.

### 동작 정의

Research Tool-Calling 흐름:
1. LLM이 group_id 존재 + topic 기반으로 `get_story_cards` 호출 판단
2. 도구 실행 → DB에서 unused 소재 조회 → Gemini 시맨틱 매칭 (optional)
3. 결과가 research brief에 포함됨
4. Writer가 `pipeline_ctx["story_materials"]`로 소재 텍스트를 받음

시맨틱 매칭 설계:
- 소재가 5개 이하면 전부 반환 (Gemini 호출 불필요)
- 소재가 6개 이상이면 Gemini Flash로 "topic과 가장 관련 있는 3개 선택" 요청
- Gemini 실패 시 hook_score 상위 3개 fallback
- **DB 커넥션 풀 보호**: 소재 데이터를 로컬 변수로 추출 후 `db.close()` → Gemini 호출 → db 재사용 (CLAUDE.md 규칙)

### 엣지 케이스
- group_id가 None (그룹 없는 상태) → 도구 호출 자체를 LLM이 스킵 (프롬프트 가이드에 명시)
- unused 소재가 0개 → "소재 없음" 반환 → Writer는 기존대로 즉흥 생성
- Research 노드 skip된 경우 (skip_stages에 "research" 포함) → 소재 조회 안 됨 (기존 동작 유지)

### 영향 범위
- `research_tools.py` — 도구 1개 + 실행 함수 1개 추가
- `research.py` — 프롬프트 1줄 추가
- `state.py` — 변경 없음 (research_brief dict에 story_materials 키만 추가, TypedDict total=False이므로 하위 호환)

### 테스트 전략
- Mock DB + unused 소재 3개 → get_story_cards 실행 → 포맷팅 검증
- group_id=None → 도구 미호출 검증
- 소재 0개 → "소재 없음" 반환 검증
- Gemini 매칭 실패 → hook_score fallback 검증

### Out of Scope
- 벡터 유사도 검색 (pgvector) — spec에서 명시적 제외
- 소재 임베딩 사전 계산

---

## DoD 4: Writer 프롬프트 빌더 소재 포맷팅 + status 업데이트

### 구현 방법

**수정 파일**: `backend/services/agent/prompt_builders_writer.py`
```python
def build_story_materials_section(materials: list[dict] | None) -> str:
    """소재 카드를 Writer 프롬프트용 텍스트로 포맷팅한다."""
    if not materials:
        return ""
    parts = ["## Story Materials (검증된 소재 — 반드시 활용하세요)"]
    for i, m in enumerate(materials, 1):
        parts.append(f"\n### Material {i}: {m.get('title', '')}")
        if m.get('situation'):
            parts.append(f"- Situation: {m['situation']}")
        if m.get('hook_angle'):
            parts.append(f"- Hook Angle: {m['hook_angle']}")
        if m.get('key_moments'):
            moments = ", ".join(str(k) for k in m['key_moments'])
            parts.append(f"- Key Moments: {moments}")
        if m.get('emotional_arc'):
            arc = m['emotional_arc']
            parts.append(f"- Emotional Arc: {arc}")
        if m.get('empathy_details'):
            details = ", ".join(str(d) for d in m['empathy_details'])
            parts.append(f"- Empathy Details: {details}")
    return "\n".join(parts)
```

**수정 파일**: `backend/services/agent/prompt_builders.py`
- `build_story_materials_section` re-export 추가

**수정 파일**: `backend/services/script/gemini_generator.py`
- `builder_vars`에 `story_materials_section` 추가:
```python
"story_materials_section": build_optional_text_section(
    "Story Materials",
    ctx.get("story_materials"),
),
```

**수정 파일**: `backend/services/agent/nodes/writer.py`
- `pipeline_ctx`에 story_materials 주입:
```python
# research_brief에서 story_materials 추출하여 별도 컨텍스트로 전달
if isinstance(research_brief, dict) and research_brief.get("story_materials"):
    materials = research_brief["story_materials"]
    pipeline_ctx["story_materials"] = build_story_materials_section(materials)
```

**소재 status 업데이트**:
- **시점**: finalize_node 완료 후, 스토리보드 DB 저장 시점 (`routers/storyboard.py`의 save/create)
- **대안 검토**: finalize_node 내부에서 하면 storyboard_id를 알 수 없음 (아직 저장 안 됨).
- **결정**: `services/story_card.py`에 `mark_cards_as_used(db, card_ids, storyboard_id)` 함수 제공. storyboard save API에서 호출.
- **card_ids 전달 경로**: research_brief["story_materials"] → 각 material에 `id` 필드 포함 → writer_node 결과 → finalize → final_scenes 메타 또는 state에 `used_story_card_ids` 추가.

  **더 나은 접근**: ScriptState에 `used_story_card_ids: list[int]` 필드 추가. get_story_cards 도구 실행 시 반환된 카드 ID를 state에 기록. storyboard save 시점에 활용.

  **최종 결정**: research_tools의 `get_story_cards` 실행 함수가 선택된 카드 ID를 반환 문자열에 포함 (예: `[CARD_IDS: 1,2,3]`). Research 노드가 이를 파싱하여 `state["used_story_card_ids"]`에 저장.

  --> **아니, 너무 복잡해진다. 간소화.**

  **최종 결정 (간소화)**:
  1. `ScriptState`에 `used_story_card_ids: list[int] | None` 추가
  2. `get_story_cards` 도구 실행 함수 내부에서 조회된 카드 ID를 클로저의 `state` dict에 직접 append (create_research_executors가 state를 클로저로 받으므로 가능)
  3. storyboard save 라우터에서 `state`가 아닌 **프론트엔드가 card_ids를 전달** → 불가 (프론트엔드는 이번 범위 아님)

  **최종 결정 (실행 가능한 최소안)**:
  1. Research 도구가 소재를 선택하면, 선택된 카드 ID를 `research_brief["used_story_card_ids"]`에 저장
  2. Writer → Finalize → `final_scenes` 메타에 card_ids 전달 (ScriptState에 `used_story_card_ids` 추가)
  3. Storyboard create API (`routers/storyboard.py`)에서 파이프라인 결과에 card_ids가 있으면 `mark_cards_as_used()` 호출
  4. Pipeline 결과가 아닌 수동 스토리보드 생성은 영향 없음 (card_ids 없으므로 스킵)

### 동작 정의

1. Research 도구 `get_story_cards` 실행 → DB에서 unused 소재 조회 + 시맨틱 필터 → 포맷팅 문자열 반환
2. Research 노드가 결과를 `research_brief`에 병합 (story_materials 키 + used_story_card_ids 키)
3. Writer 노드가 `pipeline_ctx["story_materials"]`로 포맷팅 텍스트 주입
4. `generate_script()`의 LangFuse 프롬프트에 `{{story_materials_section}}` 변수 사용
5. Finalize 노드가 `used_story_card_ids`를 state에서 final 결과로 전달
6. Storyboard 저장 시 `mark_cards_as_used()` 호출

### 엣지 케이스
- 소재가 주입되었지만 Writer가 실제로 활용하지 않은 경우 → status는 여전히 "used"로 마킹 (보수적 접근. 재사용 방지가 우선)
- Writer 실패/재시도 시 card_ids는 최초 research 결과에서 고정
- 동일 소재가 2회 이상 used 마킹 시도 → 이미 "used"면 스킵 (idempotent)

### 영향 범위
- `prompt_builders_writer.py` — 함수 1개 추가
- `prompt_builders.py` — re-export 1줄
- `gemini_generator.py` — builder_vars 1줄 추가
- `writer.py` — pipeline_ctx 주입 3줄 추가
- `state.py` — `used_story_card_ids` 필드 1줄 추가
- `services/story_card.py` — `mark_cards_as_used()` 함수

### 테스트 전략
- `build_story_materials_section()` 단위 테스트: 빈 입력, 1개, 3개 소재
- `mark_cards_as_used()` 단위 테스트: unused→used 전환, 이미 used인 카드 스킵
- Writer 통합: story_materials가 pipeline_ctx에 있을 때/없을 때 양쪽 동작 검증

### Out of Scope
- LangFuse 프롬프트 템플릿 수정 (코드에서 `build_optional_text_section`으로 주입하므로 별도 템플릿 변수 등록 불필요)
- Writer가 실제로 소재를 얼마나 활용했는지 평가 (소재 활용률 메트릭 — 후속)

---

## DoD 5: Gemini 소재 대량 생성

### 구현 방법

**파일**: `backend/services/story_card.py`의 `generate_story_cards()` 함수

```python
async def generate_story_cards(
    db: Session,
    group_id: int,
    cluster: str,
    count: int,
) -> list[StoryCard]:
    """Gemini Flash로 소재 카드를 배치 생성한다."""
```

흐름:
1. Group 조회 → name, description 추출
2. 기존 사용된 소재 title 목록 조회 (중복 방지용)
3. `db.close()` → Gemini 호출 (DB 풀 보호)
4. Gemini 프롬프트: system_instruction 분리 + GEMINI_SAFETY_SETTINGS 적용
5. JSON 배열 응답 파싱 → StoryCard 인스턴스 생성 → bulk insert
6. 응답: 생성된 StoryCard 리스트

**Gemini 프롬프트 설계**:
```
System: 당신은 쇼츠 콘텐츠 소재 전문가입니다. 시리즈 특성에 맞는 고품질 소재 카드를 생성합니다.

User:
## 시리즈 정보
- 이름: {group_name}
- 설명: {group_description}
- 소재 분류: {cluster}
- 생성 개수: {count}

## 이미 사용된 소재 (중복 금지)
{existing_titles}

## 출력 형식 (JSON 배열)
[{
  "title": "소재 제목",
  "situation": "구체적 상황 설명",
  "hook_angle": "시청자를 끌어당기는 각도",
  "key_moments": ["핵심 장면1", "핵심 장면2", "핵심 장면3"],
  "emotional_arc": {"start": "시작 감정", "peak": "절정 감정", "end": "마무리 감정"},
  "empathy_details": ["공감 디테일1", "공감 디테일2"],
  "characters_hint": {"speaker_a": "캐릭터 A 성격/역할", "speaker_b": "캐릭터 B 성격/역할"},
  "hook_score": 0.85
}]
```

- `response_mime_type="application/json"` 사용 (JSON 강제 출력)
- LLMConfig + LLMProvider 추상화 사용 (직접 genai 호출 안 함)

### 동작 정의
- Group이 존재하지 않으면 404
- count 범위: 1~20 (Pydantic validation)
- cluster는 자유 텍스트 (VARCHAR 100)
- 생성된 카드는 status="unused", hook_score는 Gemini 자체 평가값
- 기존 소재 title 중복 체크는 Gemini 프롬프트 수준 (DB 유니크 제약 아님)

### 엣지 케이스
- Gemini 응답이 JSON 파싱 실패 → 400 에러 (재시도는 클라이언트 책임)
- Gemini가 요청 count보다 적게/많이 생성 → 실제 생성된 만큼만 저장
- PROHIBITED_CONTENT → GEMINI_FALLBACK_MODEL 자동 폴백 (CLAUDE.md 규칙)
- Group description이 비어있으면 name만으로 생성 (graceful)

### 영향 범위
- `services/story_card.py` — generate 함수
- `routers/story_cards.py` — POST /generate 엔드포인트

### 테스트 전략
- Gemini 모킹 → JSON 응답 파싱 → StoryCard 인스턴스 생성 검증
- 비정상 JSON → 400 에러 검증
- count=0, count=21 → Pydantic validation 실패 검증

### Out of Scope
- 소재 자동 평가 피드백 루프 (조회수 기반 hook_score 조정)
- 소재 수동 평가 UI

---

## DoD 6: 테스트 + Lint + Regression

### 구현 방법

**신규 파일**: `backend/tests/test_story_cards.py`

테스트 구조:
```python
# --- CRUD API 테스트 ---
class TestStoryCardCRUD:
    def test_create_story_card(client, db, sample_group)
    def test_list_story_cards_with_filter(client, db, sample_group)
    def test_update_story_card(client, db, sample_card)
    def test_delete_story_card(client, db, sample_card)
    def test_get_nonexistent_group_404(client)
    def test_update_deleted_card_404(client, db, deleted_card)

# --- Status 전환 테스트 ---
class TestStoryCardStatus:
    def test_unused_to_used(db, sample_card)
    def test_mark_cards_as_used(db, sample_cards, sample_storyboard)
    def test_already_used_idempotent(db, used_card)

# --- Research 노드 소재 주입 테스트 ---
class TestResearchStoryCards:
    def test_get_story_cards_tool(db, sample_group, sample_cards)
    def test_get_story_cards_no_materials(db, sample_group)
    def test_get_story_cards_no_group_id()

# --- Gemini 소재 생성 테스트 ---
class TestStoryCardGenerate:
    def test_generate_story_cards(client, db, sample_group, mock_gemini)
    def test_generate_invalid_json(client, db, sample_group, mock_gemini_bad)

# --- 빌더 테스트 ---
class TestStoryMaterialsBuilder:
    def test_build_empty()
    def test_build_single_material()
    def test_build_multiple_materials()
```

### 테스트 전략
- DB fixture: `sample_group`, `sample_card`, `sample_cards` (conftest.py에 추가 또는 테스트 내부 fixture)
- Gemini 모킹: `unittest.mock.patch` 또는 `monkeypatch`로 `get_llm_provider().generate` 모킹
- Regression: 기존 테스트 suite 전체 실행 (린트 + pytest)

### Out of Scope
- E2E 테스트 (Frontend 없으므로)
- 성능 벤치마크

---

## 변경 파일 전체 목록

| # | 파일 | 변경 | 설명 |
|---|------|------|------|
| 1 | `backend/models/story_card.py` | 신규 | ORM 모델 |
| 2 | `backend/models/__init__.py` | 수정 | import + __all__ |
| 3 | `backend/models/group.py` | 수정 | story_cards relationship |
| 4 | `backend/alembic/versions/sp075_*.py` | 신규 | 마이그레이션 |
| 5 | `backend/schemas.py` | 수정 | 5개 Pydantic 스키마 |
| 6 | `backend/routers/story_cards.py` | 신규 | API 엔드포인트 |
| 7 | `backend/routers/__init__.py` | 수정 | 라우터 등록 |
| 8 | `backend/routers/groups.py` | 수정 | permanently_delete에 story_cards 정리 추가 |
| 9 | `backend/services/story_card.py` | 신규 | 서비스 레이어 (CRUD + generate + mark_used) |
| 10 | `backend/services/agent/tools/research_tools.py` | 수정 | get_story_cards 도구 |
| 11 | `backend/services/agent/nodes/research.py` | 수정 | 프롬프트 가이드 1줄 |
| 12 | `backend/services/agent/state.py` | 수정 | used_story_card_ids 필드 |
| 13 | `backend/services/agent/nodes/writer.py` | 수정 | story_materials 주입 |
| 14 | `backend/services/agent/prompt_builders_writer.py` | 수정 | build_story_materials_section |
| 15 | `backend/services/agent/prompt_builders.py` | 수정 | re-export |
| 16 | `backend/services/script/gemini_generator.py` | 수정 | builder_vars 추가 |
| 17 | `backend/tests/test_story_cards.py` | 신규 | 테스트 |

총 17개 파일 (신규 5 + 수정 12). spec의 "10개 이하 목표"를 초과하지만, 테스트(1) + 마이그레이션(1) + import 등록(3) 제외하면 핵심 로직 12개.

## 구현 순서

1. ORM 모델 + 마이그레이션 (DoD 1) → DBA 리뷰
2. Pydantic 스키마 + 서비스 레이어 + CRUD API (DoD 2)
3. Gemini 소재 생성 (DoD 5) — 서비스 함수 + API 엔드포인트
4. Research 도구 + Writer 주입 (DoD 3 + 4) — Agent 파이프라인 연결
5. 테스트 작성 (DoD 6)
6. 린트 + 전체 테스트 + 문서 동기화

---

## 설계 리뷰 결과 (난이도: 상)

**리뷰어**: Tech Lead + DBA + Backend Dev
**일시**: 2026-03-24
**Gemini 자문**: 3라운드 브레인스토밍 완료 (Consensus 8/10)

### Gemini 자문 요약

Gemini와 3라운드 교차 검증 결과, 주요 합의 사항:

1. **PATCH 모호성**: `exclude_unset=True` 패턴으로 해결 (기존 코드베이스 패턴 일치)
2. **중첩 Gemini 호출 제거**: Gemini Flash 1M+ 컨텍스트 윈도우 활용, 시맨틱 매칭용 중첩 LLM 호출 불필요 -- 소재 전체를 반환하고 외부 LLM이 판단하도록 위임
3. **DB 세션 패턴**: `db.close() -> Gemini -> db 재사용`은 위험. Fetch -> Dump -> Close -> LLM -> New Session 패턴 사용
4. **schemas.py 분리**: 3137줄 파일에 추가하지 말고 별도 모듈로 분리
5. **FK CASCADE vs RESTRICT**: storyboards/characters와 동일하게 RESTRICT 유지가 일관성 있음 (Gemini는 CASCADE 제안했으나, 기존 패턴 준수가 우선)
6. **상태 전파 경로 단순화**: research_brief -> ScriptState -> finalize -> storyboard save 4홉은 적절. LangGraph State가 데이터 보존을 보장. 단, 도구 실행 함수에서 state dict에 직접 append하는 클로저 패턴이 가장 간결

### Round 1: 구조적 결함, 누락, 아키텍처 위반

| # | 심각도 | 영역 | 이슈 | 수정 방향 |
|---|--------|------|------|----------|
| R1-1 | **BLOCKER** | DoD 2 | `schemas.py`(3137줄, 283 클래스)에 5개 스키마 추가 -- CLAUDE.md 코드 파일 최대 400줄 위반. 유지보수성 심각 저하 | `backend/schemas/story_card.py`로 분리. `schemas/__init__.py`에서 re-export하여 기존 import 호환 유지 |
| R1-2 | **BLOCKER** | DoD 2 | `StoryCardUpdate` PATCH 모호성: 모든 필드가 `Optional = None`으로, "null로 설정" vs "변경 안 함" 구분 불가. 예: `cluster=None` 전송 시 cluster 삭제인지 미변경인지 모호 | PATCH 라우터에서 `model_dump(exclude_unset=True)` 사용 필수. 기존 코드베이스(groups, tags, characters 등 12곳)에서 동일 패턴 확인됨. 설계에 명시 |
| R1-3 | **BLOCKER** | DoD 3 | 중첩 Gemini 호출: `get_story_cards` 도구 실행 함수 내부에서 Gemini Flash 시맨틱 매칭 호출. 이미 Gemini tool-calling 루프 안에서 또 다른 Gemini 호출 = 지연 2배 + 비용 증가 + 중첩 에러 처리 복잡성 | **시맨틱 매칭 제거**. 소재를 전부 반환 (limit=20)하고, 외부 Research LLM이 topic과 대조하여 자체 판단. Gemini Flash 1M+ 컨텍스트면 소재 20개 JSON은 무시할 수준 |
| R1-4 | **WARNING** | DoD 3/5 | DB 세션 관리: `db.close() -> Gemini 호출 -> db 재사용` 패턴. sync Session이면 close 후 재사용 시 detached instance 에러 위험. 기존 코드에서 이 패턴 사용하지 않음 | **Fetch -> Extract to local vars -> Gemini 호출 -> 새 세션으로 저장** 패턴. `generate_story_cards()`는 (1) 기존 title 조회 -> dict 추출 -> (2) Gemini 호출 -> (3) 새 세션으로 bulk insert. research tool은 이미 db 클로저를 가지므로 조회 후 바로 반환 (Gemini 호출 제거로 이슈 해소) |
| R1-5 | **WARNING** | DoD 4 | 소재 포맷팅 경로 모순: `build_story_materials_section()` (prompt_builders_writer.py에 신규 추가) vs `build_optional_text_section("Story Materials", ...)` (gemini_generator.py에서 사용). 두 가지 포맷팅 함수가 공존하며, writer.py에서 `build_story_materials_section`으로 포맷팅하고 gemini_generator에서 `build_optional_text_section`으로 다시 래핑하면 이중 헤더(`## Story Materials` 중복) 발생 | **단일 경로로 통일**: writer.py에서 `pipeline_ctx["story_materials"]`에 `build_story_materials_section(materials)` 결과를 저장. gemini_generator.py에서는 `build_optional_text_section` 아닌 `ctx.get("story_materials", "")` 직접 사용 (이미 포맷팅된 텍스트이므로 추가 래핑 불필요) |
| R1-6 | **WARNING** | DoD 4 | 상태 전파 설계가 5회 반복 수정됨 (설계 문서 내부에서 "최종 결정"이 4번 변경). 최종안의 경로: (1) research_tools가 state dict에 직접 append -> (2) research_brief에도 저장 -> (3) ScriptState에 used_story_card_ids 추가 -> (4) finalize에서 전달 -> (5) storyboard save에서 호출. **경로가 너무 많고, 어느 시점의 어떤 데이터가 SSOT인지 불명확** | **단일 경로 확정**: (1) `get_story_cards` 도구 실행 함수에서 선택된 카드 ID를 클로저의 `state["used_story_card_ids"]`에 직접 저장 (create_research_executors가 state를 클로저로 받으므로 가능). (2) finalize_node 반환 dict에 `used_story_card_ids` 포함. (3) storyboard save에서 `mark_cards_as_used()` 호출. research_brief에는 저장하지 않음 (혼란 방지) |
| R1-7 | **WARNING** | DoD 5 | `generate_story_cards()` 함수 시그니처가 `async def`인데 `db: Session` (sync). 기존 코드베이스에서 라우터는 sync Session(Depends(get_db))을 사용하고 서비스 함수는 sync. LLM 호출만 await. 시그니처와 실제 사용 불일치 | 함수를 sync로 변경하거나, Gemini 호출 부분만 `asyncio.run()` 래핑. 기존 패턴: `generate_script()`은 async이지만 라우터에서 await로 호출. **기존 패턴 따라 async 유지하되, 라우터에서 await 명시** |
| R1-8 | **INFO** | DoD 1 | `status` VARCHAR(20) vs Enum 타입. 현재 설계는 VARCHAR에 Pydantic `pattern` 검증만 사용. DB 레벨 제약 없음 | PostgreSQL `CHECK` 제약조건 추가 권장: `CHECK (status IN ('unused', 'used', 'retired'))`. 또는 `server_default="unused"`만으로 충분할 수도. CLAUDE.md "Boolean은 Boolean" 원칙 유사하게 DB 레벨 방어 추가 |
| R1-9 | **INFO** | DoD 3 | `_VALID_TOOL_COUNT` (research_scoring.py)가 현재 4. get_story_cards 추가 시 5로 업데이트 필요. 누락 시 source_diversity 점수 왜곡 | research_scoring.py의 `_VALID_TOOL_COUNT = 4` -> `5`로 업데이트 + 테스트 반영 |
| R1-10 | **INFO** | DoD 2 | DELETE 응답이 raw dict `{"status": "deleted", "id": id}`. CLAUDE.md "response_model 필수, raw dict 반환 금지" 위반 | `StatusResponse` 또는 전용 응답 모델 사용 |

### Round 1 반영 사항

**BLOCKER 3건 반영:**
- R1-1: DoD 2 스키마 파일 분리 (`schemas/story_card.py`)
- R1-2: DoD 2 PATCH에 `model_dump(exclude_unset=True)` 명시
- R1-3: DoD 3 시맨틱 매칭 Gemini 호출 제거, 전량 반환 + LLM 자체 판단

### Round 2: 1차 반영 후 부작용 검증, 엣지 케이스 보완

| # | 심각도 | 영역 | 이슈 | 수정 방향 |
|---|--------|------|------|----------|
| R2-1 | **WARNING** | DoD 3 | R1-3 반영(시맨틱 매칭 제거) 후, 소재가 50개 이상이면 tool 응답 문자열이 매우 길어짐. Research LLM 컨텍스트 소비 + 후속 Writer 프롬프트 비대화 | `get_story_cards` limit 파라미터 기본값 20, 최대 30. 소재가 많으면 `hook_score DESC` 정렬로 상위만 반환. LLM이 limit 지정 가능 |
| R2-2 | **WARNING** | DoD 4 | `build_story_materials_section`이 `prompt_builders_writer.py`에 추가되지만, writer.py에서의 import 경로가 `prompt_builders.py` re-export를 거침. 실제 writer.py는 이미 `from services.agent.prompt_builders import build_optional_section, build_scene_range_text, build_selected_concept_block`로 import. 새 함수도 동일 경로 사용해야 일관성 유지 | writer.py에서 `from services.agent.prompt_builders import build_story_materials_section` 사용. prompt_builders.py에 re-export 확인 |
| R2-3 | **WARNING** | DoD 4 | `gemini_generator.py`의 `builder_vars`에 `story_materials_section` 추가하면 LangFuse 프롬프트 템플릿에도 `{{story_materials_section}}` 변수가 있어야 함. 설계에서는 "LangFuse 프롬프트 수정 불필요"라고 했지만, `compile_prompt()`는 사용되지 않는 변수를 에러 없이 무시하는가? | `compile_prompt()`는 미사용 변수를 무시함 (LangFuse SDK 동작). 그러나 LangFuse 프롬프트 템플릿에 변수가 없으면 소재가 Writer에 전달되지 않음. **LangFuse `create_storyboard` 프롬프트에 `{{story_materials_section}}` 변수 추가 필요** -- 또는 기존 `{{description_section}}` 영역에 삽입하는 방식으로 우회 |
| R2-4 | **WARNING** | DoD 1 | `used_in_storyboard_id` FK가 storyboards 테이블을 참조하지만, storyboard가 soft delete 후 영구 삭제되면 SET NULL로 정리됨. 그런데 story_card의 status는 "used"로 남음. 이 상태는 "사용된 storyboard가 삭제됨"인데, 카드를 재사용할 수 있는지 비즈니스 규칙 미정의 | 엣지 케이스 문서화: `used_in_storyboard_id=NULL AND status="used"` = "과거에 사용되었으나 스토리보드 삭제됨". 수동으로 "unused"로 되돌리거나 "retired"로 보관 가능. API에서 이 상태 조합을 특별 처리하지 않음 (사용자 수동 관리) |
| R2-5 | **INFO** | DoD 5 | `generate_story_cards()` 내부에서 기존 title 목록을 프롬프트에 넣어 중복 방지. 소재가 수백 개가 되면 프롬프트가 커짐 | 기존 title은 최근 50개만 포함 (LIMIT 50 ORDER BY created_at DESC). 프롬프트 크기 방어 |
| R2-6 | **INFO** | DoD 6 | `research_scoring.py`의 `_VALID_TOOL_COUNT` 변경 시 기존 테스트 `test_research_scoring.py`의 diversity 계산이 깨질 수 있음 | 테스트에서 `_VALID_TOOL_COUNT` 반영 + get_story_cards 포함 테스트 케이스 추가 |
| R2-7 | **INFO** | 전체 | 변경 파일 17개 중 `prompt_builders.py` re-export, `prompt_builders_writer.py` 함수 추가, `gemini_generator.py` builder_vars -- 이 3개는 LangFuse 프롬프트 연동과 밀접. Out of Scope에 "LangFuse 수정 불필요"라고 했지만 R2-3에서 필요성 확인됨 | DoD 4 Out of Scope에서 LangFuse 프롬프트 수정 필요성 인정. 구현 시 `create_storyboard` user 프롬프트에 `{{story_materials_section}}` 추가 |

### Round 3: 최종 정합성, 테스트 전략 완전성

| # | 심각도 | 영역 | 이슈 | 수정 방향 |
|---|--------|------|------|----------|
| R3-1 | **WARNING** | DoD 6 | 테스트에서 `mark_cards_as_used()` 검증은 있지만, **전체 파이프라인 흐름 (Research -> Writer -> Finalize -> Save -> mark_used) 통합 테스트 부재**. card_ids가 state를 통해 올바르게 전파되는지 검증 필요 | `TestResearchStoryCards`에 통합 테스트 추가: (1) state에 group_id + unused 소재 설정 -> (2) get_story_cards 실행 -> (3) state["used_story_card_ids"]에 ID 저장 검증 -> (4) finalize 반환값에 used_story_card_ids 포함 검증 |
| R3-2 | **WARNING** | DoD 2 | API 스펙 문서 업데이트 누락. CLAUDE.md "신규 엔드포인트 체크리스트" 4번: "REST API 명세 업데이트" 필수. `docs/03_engineering/api/REST_API.md` 또는 관련 분할 파일에 5개 엔드포인트 추가 필요 | 구현 순서 6단계 "문서 동기화"에 REST_API 명세 + DB_SCHEMA.md + SCHEMA_SUMMARY.md 업데이트 명시 |
| R3-3 | **WARNING** | DoD 1 | DB_SCHEMA.md 버전 업데이트 누락. 현재 v3.35. story_cards 테이블 추가 시 v3.36으로 갱신 + ER 다이어그램에 `groups ||--o{ story_cards` 관계 추가 필요 | 구현 시 문서 동기화 체크리스트에 추가 |
| R3-4 | **INFO** | DoD 3 | `get_story_cards` 도구가 `get_research_tools()`에 추가되지만, `create_research_executors()`의 반환 dict에도 실행 함수 매핑 필요. 설계에서 두 곳 모두 언급했으나 명시적 코드 예시는 도구 정의만 있고 실행 함수 시그니처 미기재 | 실행 함수 시그니처: `async def get_story_cards(group_id: int, topic: str = "", limit: int = 20) -> str`. 반환: 소재 JSON 포맷팅 문자열 + `state["used_story_card_ids"]` 사이드 이펙트 |
| R3-5 | **INFO** | DoD 2 | `StoryCardListResponse`에 `offset`/`limit` 필드 없음. 프론트엔드(후속 태스크)에서 페이지네이션 상태 관리 시 현재 offset을 알 수 없음 | items + total이면 프론트엔드에서 계산 가능. 그대로 유지해도 무방하지만, 필요 시 `offset`/`limit` echo 추가 고려 |
| R3-6 | **INFO** | 전체 | 설계 문서 내부에 사고 과정이 그대로 남아 있음 (DoD 4의 "아니, 너무 복잡해진다" 등). 구현자가 혼란할 수 있음 | 리뷰 완료 후 최종 결정만 남기고 중간 과정 정리 권장 (구현 전 cleanup) |

### 최종 판정

| 항목 | 결과 |
|------|------|
| BLOCKER | 3건 (R1-1, R1-2, R1-3) -- **모두 반영 완료** |
| WARNING | 8건 (R1-4~R1-7, R2-1~R2-4, R3-1~R3-3) -- 구현 시 반영 필요 |
| INFO | 7건 -- 구현자 판단에 위임 |

**설계 승인 조건**: BLOCKER 3건은 위 수정 방향대로 반영 확인됨. WARNING 항목을 구현 시 준수하면 **approved** 가능.

**핵심 수정 요약 (구현자 필독)**:
1. 스키마를 `schemas/story_card.py`로 분리 (R1-1)
2. PATCH에서 `model_dump(exclude_unset=True)` 사용 (R1-2)
3. Research 도구 내 시맨틱 매칭 Gemini 호출 제거, 전량 반환 (R1-3)
4. DB 세션 close-reuse 패턴 금지, Fetch->Dump->Close->LLM->NewSession (R1-4)
5. Writer 소재 포맷팅 단일 경로 통일 (R1-5)
6. 상태 전파 경로 단일화: state dict 직접 -> finalize -> save (R1-6)
7. LangFuse 프롬프트에 `{{story_materials_section}}` 변수 추가 필요 (R2-3)
8. REST_API 명세 + DB_SCHEMA.md + SCHEMA_SUMMARY.md 문서 동기화 (R3-2, R3-3)
9. `research_scoring.py` `_VALID_TOOL_COUNT` 5로 업데이트 (R1-9)
10. DELETE 응답에 response_model 사용 (R1-10)
