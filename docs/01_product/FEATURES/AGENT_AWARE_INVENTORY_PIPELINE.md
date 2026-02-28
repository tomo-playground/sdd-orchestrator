# Agent-Aware Inventory Pipeline (Director 캐스팅 시스템)

> **상태**: 미착수 — Phase A/B/C 3단계 점진적 전환
> **선행**: Phase 10 (True Agentic Architecture), Phase 18 (Stage Workflow), Phase 19 (탭 페르소나 재배치)
> **관련**: [AGENTIC_PIPELINE.md](AGENTIC_PIPELINE.md), [STAGE_WORKFLOW.md](STAGE_WORKFLOW.md)
> **리뷰**: 6-Agent Cross Review 완료 (PM/Backend/Frontend/TechLead/UX/Prompt — 2026-02-28)

---

## 1. 배경 및 문제 정의

### 1-1. 왜 필요한가

현재 파이프라인에서 Director Plan은 `creative_goal`/`target_emotion`/`quality_criteria`만 수립한다.
캐릭터·구조·스타일 선택은 **유저가 Script 탭에서 사전 결정**해야 하며, Agent는 주어진 것만 소비한다.

Film Production 메타포에서 Director는 "캐스팅 + 연출" 권한을 갖는다.
이 기능은 Director Agent에게 **인벤토리 인지 → 자율 캐스팅** 능력을 부여하여,
토픽에 최적인 캐릭터/구조/스타일 조합을 제안하는 "캐스팅 시스템"을 구축한다.

### 1-2. 해결하는 핵심 문제

| 문제 | 현재 상태 | 도입 후 |
|------|----------|---------|
| **유저 결정 부담** | 캐릭터 40+명, 구조 4종, 스타일 N종에서 직접 선택 | Director가 토픽 기반 최적 조합 추천 |
| **토픽-캐릭터 미스매치** | 유저가 항상 같은 캐릭터만 반복 사용 | 토픽에 적합한 캐릭터를 데이터 기반 추천 |
| **Express 모드 한계** | 캐릭터/구조 미선택 시 Express 사용 불가 | Director가 자율 선택 → 토픽만으로 생성 가능 |
| **Director 역할 미흡** | creative_goal만 수립, 프로덕션 결정에 미관여 | 캐스팅 + 크리에이티브 방향 통합 수립 |

---

## 2. Phase 구성

### Phase A: Director Inventory Awareness (MVP, Backend + 최소 Frontend)

| # | 항목 | 설명 |
|---|------|------|
| 1 | `services/agent/inventory.py` 인벤토리 로딩 서비스 | 캐릭터/구조/스타일 요약 + 토큰 프루닝 (20명 상한) |
| 2 | `director_plan.j2` 템플릿 인벤토리 섹션 추가 | 캐릭터 목록 + 구조 메타 + 스타일 목록 주입 + CoT 캐스팅 가이드 |
| 3 | `DirectorPlanOutput` 필드 확장 | `casting` 객체 (character_id + character_name 교차검증) |
| 4 | `ScriptState`에 `CastingRecommendation` 추가 | Director 추천 결과 상태 보관 |
| 5 | `inventory_resolve` 시스템 노드 | user override vs Director 추천 병합 + 5항목 유효성 검증 |
| 6 | Graph 엣지 삽입 | `director_plan → inventory_resolve → research` |
| 7 | SSE `node_result` 기반 캐스팅 전달 | 기존 SSE 인프라 활용, `inventory_resolve` 노드 결과로 전달 |
| 8 | 후방 호환성 보장 | 기존 character_id 선택 유지, Express/Quick 모드 불변 |
| 9 | 최소 Frontend 토스트 | `casting_recommendation` 수신 시 토스트로 추천 표시 |

### Phase B: Casting UX (Frontend)

**선행**: `useScriptEditor.ts` SSE 파싱 분리 리팩터링 (832줄 → 400줄 이하)

| # | 항목 | 설명 |
|---|------|------|
| 1 | CharacterSelector "AI 추천" 그룹 | 드롭다운 최상단에 "AI Recommended" 그룹 + Sparkles 배지 |
| 2 | Script 탭 캐스팅 배너 | SSE 수신 시 Script 탭 상단에 추천 배너 + "수락/거절" CTA |
| 3 | Stage 캐스팅 비교 카드 | Director 추천 vs 현재 선택 경량 비교 (`StageCastingCompareCard.tsx`) |
| 4 | character_id Optional 전환 | `character_id: null` 전송으로 Director 자율 캐스팅 진입 |
| 5 | `pipelineSteps.ts` "캐스팅" 단계 | "디렉터" 스텝에 `inventory_resolve` 노드 통합 |

### Phase C: Autonomous Express

| # | 항목 | 설명 |
|---|------|------|
| 1 | `director_plan_lite` 경량 노드 | Flash 모델, 캐스팅만 수행 (캐릭터 10명 이하 제한) |
| 2 | Express 라우팅 확장 | `routing.py` 3번째 분기 + `script_graph.py` conditional_edges 목록 확장 |
| 3 | One-Click Express UI | 토픽만 입력 → 전체 자동 생성 + 2단계 확인 인터랙션 |
| 4 | AI 결정 요약 카드 | 완료 후 캐릭터/구조/스타일 선택 근거 + 각 항목 "변경" 링크 |
| 5 | Fallback 전략 | 캐스팅 실패 시 최근 사용 캐릭터 + monologue 구조로 degradation |

---

## 3. 기술 설계

### 3-1. 인벤토리 로딩 서비스 (`inventory.py`)

#### 캐릭터 프루닝 전략 (최대 20명)

> **주의**: Character 모델에 `group_id` FK가 없다. 캐릭터는 전역 엔티티이며, Group과의 연결은
> `storyboard_characters JOIN storyboards` 간접 관계로만 추적 가능.

```
전체 캐릭터 목록 (N명)
  ↓ Filter: storyboard_characters → storyboards WHERE group_id 일치
  ↓         + 한 번도 사용되지 않은 캐릭터도 포함 (전체 캐릭터 중 deleted_at IS NULL)
  ↓ Sort: usage_count(해당 group 내 사용 횟수) DESC → LoRA 유무 → 생성일
  ↓ Limit: INVENTORY_MAX_CHARACTERS (config, 기본 20명)
  ↓ Summarize: {id, name, gender, lora_name, appearance_summary, has_reference}
```

**쿼리 설계** (N+1 방지를 위해 selectinload 사용):
```sql
SELECT c.id, c.name, c.gender, c.lora_name,
       COUNT(sc.id) FILTER (WHERE sb.group_id = :gid) as usage_count,
       (c.reference_image_asset_id IS NOT NULL) as has_reference
FROM characters c
LEFT JOIN storyboard_characters sc ON c.id = sc.character_id
LEFT JOIN storyboards sb ON sc.storyboard_id = sb.id AND sb.deleted_at IS NULL
WHERE c.deleted_at IS NULL
GROUP BY c.id
ORDER BY usage_count DESC, (c.lora_name IS NOT NULL) DESC, c.created_at DESC
LIMIT :max_chars
```

**appearance_summary 구성**: `character_tags` JOIN `tags` WHERE `group_name IN ('hair', 'eyes', 'body_type')` — 자연어 1줄 요약으로 변환 (태그 나열이 아닌 "갈색 머리의 여고생" 형태). `is_permanent=True` 태그 우선.

**토큰 예산 (실측 기반)**: 캐릭터당 ~80-120토큰 × 20명 = ~1,600-2,400토큰 (Gemini Pro 32K의 ~5-7.5%)

**DB 세션 관리**: `director_plan_node` 진입 시 DB 세션으로 인벤토리 로드 → 세션 close → LLM 호출. CLAUDE.md "외부 호출 전 db.close() 필수" 원칙 준수.

#### 구조 메타데이터

`inventory.py` 내부에 `STRUCTURE_METADATA` 상수로 관리 (`StoryboardPreset` dataclass 변경 없음):

```python
STRUCTURE_METADATA: dict[str, StructureMeta] = {
    "monologue": StructureMeta(requires_two_characters=False, tone="intimate"),
    "dialogue": StructureMeta(requires_two_characters=True, tone="dynamic"),
    "narrated_dialogue": StructureMeta(requires_two_characters=True, tone="narrative"),
    "confession": StructureMeta(requires_two_characters=False, tone="emotional"),
}
```

> `suitable_for` 필드 제거: 4종 구조에서 선택지가 적어 Director의 자연어 이해만으로 충분. 구조 추천보다 **캐릭터 추천**에 인지 리소스 집중.

#### 스타일 목록

StyleProfile 테이블에서 `is_active=True`인 항목만 로드:
`{id, name, description, default_positive}`
> `sample_image_url` 제거: StyleProfile에 해당 필드 없음 + CLAUDE.md URL 규칙 위반 + LLM이 URL을 활용하지 못함.
> `checkpoint_name` → `sd_model.model_name` JOIN 필요 → 대신 `description` 텍스트로 대체.

#### Config 상수 등록 (`config_pipelines.py`)

```python
INVENTORY_MAX_CHARACTERS = 20       # 캐릭터 프루닝 상한 (실측 후 점진 확대)
INVENTORY_CASTING_ENABLED = True    # Feature flag (Phase C 점진 전환용)
```

### 3-2. Director Plan 템플릿 확장

기존 `director_plan.j2`에 인벤토리 + CoT 캐스팅 가이드 추가:

```
## Available Inventory (신규)

### Characters ({{ characters|length }}명)
{% for char in characters %}
- ID {{ char.id }}: {{ char.name }} ({{ char.gender }})
  - 특징: {{ char.appearance_summary }}
  - LoRA: {{ "전용 LoRA (일관성 높음)" if char.lora_name else "없음" }}
  - 레퍼런스: {{ "있음" if char.has_reference else "없음" }}
{% endfor %}

### Structures ({{ structures|length }}종)
{% for struct in structures %}
- {{ struct.id }}: {{ struct.name }} ({{ struct.tone }})
  - 2인 필수: {{ struct.requires_two_characters }}
{% endfor %}

### Styles ({{ styles|length }}종)
{% for style in styles %}
- ID {{ style.id }}: {{ style.name }} — {{ style.description[:50] }}
{% endfor %}

## Casting Guide (CoT 유도)
### Step 1: 토픽의 핵심 감정과 장르를 파악하세요
### Step 2: 1인 독백 vs 대화/갈등에 따라 구조를 선택하세요
### Step 3: LoRA가 있는 캐릭터를 우선 고려하세요 (이미지 일관성)
### Step 4: 캐릭터 ID와 이름을 반드시 함께 기재하세요
```

### 3-3. Pydantic 모델 확장

```python
class CastingRecommendation(BaseModel):
    """Director의 캐스팅 추천."""
    character_id: int | None = None
    character_name: str = ""          # ID 교차검증용 (필수)
    character_b_id: int | None = None # 2인 구조 시
    character_b_name: str = ""        # ID 교차검증용
    structure: str | None = None
    style_profile_id: int | None = None
    reasoning: str = ""               # 추천 근거 (한국어, 20자 이상 권장)

    @model_validator(mode="after")
    def validate_casting(self) -> Self:
        """2인 구조 시 character_b_id 필수, 중복 방지."""
        TWO_CHAR = {"dialogue", "narrated_dialogue"}
        if self.structure in TWO_CHAR and not self.character_b_id:
            raise ValueError(f"2인 구조 '{self.structure}'에 character_b_id 필수")
        if self.character_id and self.character_id == self.character_b_id:
            raise ValueError("character_id와 character_b_id는 달라야 함")
        return self
```

### 3-4. director_plan_node 반환값 변경

```python
# 기존: {"director_plan": plan}
# 변경 후:
return {
    "director_plan": plan,
    "casting_recommendation": result.get("casting"),  # inventory_resolve가 소비
}
```

### 3-5. inventory_resolve 노드

```
director_plan → inventory_resolve → research
```

**5항목 유효성 검증** (인벤토리 로드 시 valid ID set을 state에 보관 → in-memory 검증):

1. **ID 유효성**: character_id가 인벤토리 목록 내 존재 (없으면 character_name으로 fuzzy match fallback)
2. **구조 적합성**: dialogue/narrated_dialogue 선택 시 character_b_id 필수
3. **중복 검증**: character_id != character_b_id
4. **LoRA 호환성**: style_profile_id의 base_model과 character LoRA의 base_model 일치 여부
5. **스타일 유효성**: style_profile_id가 is_active=True인 StyleProfile에 존재

**병합 로직**:

| 조건 | 동작 |
|------|------|
| user가 character_id 선택함 | user 선택 유지 (Director 추천 무시) |
| user가 character_id 미선택 + Director 추천 유효 | Director 추천 적용 |
| user가 character_id 미선택 + Director 추천 무효/없음 | character_id=None 유지 |
| user가 structure 선택함 | user 선택 유지 |
| user가 structure 미선택 + Director 추천 있음 | Director 추천 적용 |
| style_profile_id 미선택 + Director 추천 있음 | Director 추천의 style_profile_id → style name으로 변환하여 적용 |

**에러 핸들링**: 기존 노드 패턴과 동일한 try/except graceful degradation. 실패 시 `{"casting_recommendation": None}` 반환.

### 3-6. Graph 엣지 변경

```python
# Phase A
graph.add_edge("director_plan", "inventory_resolve")
graph.add_edge("inventory_resolve", "research")

# Phase C 추가 (feature flag)
graph.add_conditional_edges(
    START, route_after_start,
    ["director_plan", "director_plan_lite", "writer"]  # 3분기
)
```

Phase A에서는 `route_after_start` 변경 없음 (Quick/Express → `"writer"` 직행 불변).
Phase C에서 `routing.py`에 3번째 분기 `"director_plan_lite"` 추가 필수.

### 3-7. SSE 이벤트 (기존 인프라 활용)

별도 이벤트 타입 도입 대신, 기존 `node_result` 기반 패턴 통일:

```json
{
  "node": "inventory_resolve",
  "status": "completed",
  "node_result": {
    "casting": {
      "character_id": 42,
      "character_name": "건우",
      "structure": "monologue",
      "style_profile_id": 3,
      "reasoning": "감성적 독백 주제에 건우의 차분한 톤이 적합"
    }
  }
}
```

> `_NODE_META`에 `inventory_resolve` 등록. `processSSEStream`의 기존 `event.node` + `event.status` 분기를 그대로 활용.

---

## 4. UI 레이아웃

### 4-1. Script 탭 변경 (Phase B)

| 요소 | 변경 |
|------|------|
| CharacterSelector | 드롭다운 최상단에 "AI Recommended" 그룹 + Sparkles 아이콘 |
| StructureSelector | Director 추천 구조에 Sparkles 배지 (별표 아닌 통일된 아이콘) |
| character_id 미선택 | `character_id: null` 전송으로 Director 자율 캐스팅 진입 (별도 토글 불필요) |
| 캐스팅 배너 | SSE 수신 시 Script 탭 상단 배너: "Director 추천: 건우 — [수락] [무시]" |

> `auto_cast` 토글 대신 **character_id 미선택 = Director 자율 캐스팅** 으로 단순화.
> 기존 워크플로우 보존: character_id를 선택하면 Director 추천 무시 (user override).

### 4-2. Stage 캐스팅 비교 카드 (Phase B)

`StageCastingCompareCard.tsx` 신규 컴포넌트 (StageCharactersSection 내부):

| 상태 | 표시 내용 |
|------|----------|
| SSE 미수신 (파이프라인 실행 전) | 표시 안 함 |
| SSE 수신 + 추천 유효 | 경량 비교: 추천 캐릭터 썸네일 + 이름 + reasoning 1줄 + "수락" CTA |
| 유저가 "수락" 클릭 | 일반 CharacterCard로 전환, 비교 카드 소멸 |
| 유저가 "무시" 또는 직접 다른 캐릭터 선택 | 비교 카드 소멸 |
| Director 추천 실패 (reasoning만 전달) | "직접 캐릭터를 선택해주세요" 안내 배너 |

> 추천 캐릭터 상세 정보는 `character_id`로 별도 fetch (SSE에는 경량 데이터만 포함).
> "수락" 후 AI 배지 제거 — 유저의 "내 선택" 소유감 보존.

### 4-3. 파이프라인 진행률 (Phase B)

`pipelineSteps.ts`의 기존 "디렉터" 스텝에 `inventory_resolve` 노드 통합:
```typescript
{ label: "디렉터/캐스팅", nodes: ["Director", "inventory_resolve", "Human Gate"] }
```

> `PipelineStatusDots`는 Studio 레벨 파이프라인 (Script→Stage→Images→Render) 이므로 변경 없음.

### 4-4. Zustand 상태 저장 위치 (Phase B)

`casting_recommendation` 수신 시 `useStoryboardStore`에 동기화:
```typescript
// useScriptEditor processSSEStream에서
if (event.node === "inventory_resolve" && event.node_result?.casting) {
  useStoryboardStore.getState().setCastingRecommendation(event.node_result.casting);
}
```

> Stage 탭 비교 카드가 이 데이터를 소비. 기존 `sound_recommendation → useRenderStore` 동기화 패턴 참고.

### 4-5. One-Click Express (Phase C)

| 요소 | 설명 |
|------|------|
| 토픽 입력 필드 | 단일 텍스트 입력 |
| "바로 생성" 버튼 | 2단계 확인: 첫 클릭 → "정말 시작할까요?" 변환 (3초) → 재클릭으로 확정 |
| AI 결정 요약 카드 | 완료 후 캐릭터/구조/스타일 + 근거, 각 항목에 "변경" 링크 |
| 결과 유도 | 자동으로 Stage 탭 이동 + "Director가 선택한 결과를 확인하세요" 배너 |

---

## 5. 추가 아이디어 (후속)

| 아이디어 | Phase | 효과 |
|---------|-------|------|
| 캐스팅 히스토리 분석 (성공 조합 학습) | C+ | 반복 추천 품질 향상 |
| 캐릭터 Chemistry 점수 (2인 구조 시 조합 적합도) | C+ | 대화 자연스러움 향상 |
| 토픽 자동 분류 (emotional/comedy/educational 등) | B+ | 구조 추천 정확도 향상 |
| Group 기본 캐릭터 설정 (Director 미추천 시 fallback) | A+ | Phase C Fallback 선행 |
| prompt_histories 활용 (캐릭터별 평균 Match Rate) | A+ | 안정적인 캐릭터 우선 추천 |

---

## 6. DoD (Definition of Done)

### Phase A

| # | 항목 | 검증 기준 |
|---|------|----------|
| 1 | 인벤토리 로딩 | `storyboard_characters JOIN storyboards` 기반 그룹 내 캐릭터가 Director 템플릿에 주입되는가? |
| 2 | 토큰 프루닝 | 20명 초과 캐릭터가 정확히 프루닝되는가? (경계값 테스트) |
| 3 | Director 캐스팅 | Director가 유효한 character_id + character_name을 반환하는가? (ID 유효성 비율 ≥ 95%, 100회 실행 기준) |
| 4 | inventory_resolve | user override > Director 추천 우선순위가 정확한가? (5항목 유효성 검증 통과) |
| 5 | Graph 엣지 | `director_plan → inventory_resolve → research` 경로가 정상 동작하는가? |
| 6 | SSE 이벤트 | `node: "inventory_resolve"` 이벤트가 Frontend에 전달 + 토스트 표시되는가? |
| 7 | 후방 호환성 | 기존 character_id 선택 워크플로우가 정상 동작하는가? |
| 8 | Quick 모드 불변 | Quick/Express 모드가 기존과 동일하게 동작하는가? |
| 9 | Graceful Degradation | 인벤토리 로드/캐스팅 실패 시 기존 동작으로 fallback하는가? |
| 10 | Fallback 발동률 | inventory_resolve에서 Director 추천 무효화 비율 ≤ 10% (100회 기준) |

### Phase B

**선행**: `useScriptEditor.ts` SSE 파싱 분리 (832줄 → 400줄 이하)

| # | 항목 | 검증 기준 |
|---|------|----------|
| 1 | AI 추천 그룹 | CharacterSelector 드롭다운 최상단에 추천 캐릭터 그룹이 표시되는가? |
| 2 | 캐스팅 배너 | Script 탭에서 추천 수신 시 배너가 나타나고 "수락" 클릭 시 캐릭터가 적용되는가? |
| 3 | 비교 카드 라이프사이클 | Stage 탭에서 비교 카드 생성→수락/거절→소멸이 정상 동작하는가? |
| 4 | character_id Optional | character_id 미선택으로 파이프라인 시작 시 Director 캐스팅이 작동하는가? |
| 5 | 캐스팅 실패 UI | 추천 실패 시 "직접 선택하세요" 안내가 표시되는가? |

### Phase C

| # | 항목 | 검증 기준 |
|---|------|----------|
| 1 | director_plan_lite | Flash 모델로 10명 이하 캐릭터 풀에서 캐스팅이 수행되는가? |
| 2 | Express 라우팅 | `route_after_start` 3분기 + conditional_edges 확장이 정상 동작하는가? |
| 3 | Fallback | 캐스팅 실패 시 최근 사용 캐릭터 + monologue로 정상 생성되는가? |
| 4 | AI 결정 요약 | 완료 후 요약 카드에서 각 항목 "변경" 링크가 동작하는가? |

---

## 7. 사이드 이펙트 분석

### 7-1. Director Plan 템플릿 확장

| # | 영향 | 위험도 | 대응 |
|---|------|--------|------|
| 1 | 인벤토리 주입으로 프롬프트 길이 증가 (~2,400토큰) | MEDIUM | 상한 20명, 실측 후 점진 확대 |
| 2 | Director 응답 시간 증가 (컨텍스트 증가) | LOW | Pro 모델 사용 |
| 3 | Director가 잘못된 character_id 반환 | MEDIUM | character_name 교차검증 + fuzzy match fallback |
| 4 | 40명 리스트에서 LLM 위치 편향 | MEDIUM | 20명 상한 + 토픽 관련도 사전 정렬 |
| 5 | DB 커넥션 풀 고갈 | MEDIUM | 인벤토리 로드 후 db.close() → LLM 호출 |

### 7-2. Graph 엣지 삽입

| # | 영향 | 위험도 | 대응 |
|---|------|--------|------|
| 1 | LangGraph 체크포인트에 새 state key | LOW | `total=False` TypedDict이므로 안전 |
| 2 | 기존 테스트에서 직접 엣지 가정 | LOW | 테스트 업데이트 |
| 3 | Quick/Express 분기 영향 | LOW | `"writer"` 직행이므로 영향 없음 |

### 7-3. Frontend 영향 (Phase B)

| # | 영향 | 위험도 | 대응 |
|---|------|--------|------|
| 1 | `useScriptEditor.ts` 832줄 → SSE 파싱 분리 필요 | **HIGH** | Phase B 선행 리팩터링 |
| 2 | `processSSEStream`이 `node_result` 기반이므로 새 프로토콜 불필요 | LOW | 기존 패턴 준수 |
| 3 | Zustand 스토어에 `castingRecommendation` 추가 | LOW | `useStoryboardStore` |

### 7-4. Express 모드 변경 (Phase C)

| # | 영향 | 위험도 | 대응 |
|---|------|--------|------|
| 1 | `route_after_start` 3분기 + `conditional_edges` 확장 | **HIGH** | Phase C에서만, feature flag |
| 2 | `director_plan_lite` 실패 시 Express 전체 실패 | **HIGH** | Fallback: 최근 사용 캐릭터 + monologue |
| 3 | Flash 모델 ID 정확도 | MEDIUM | 캐릭터 풀 10명 이하 제한 |

---

## 8. 의존성

| 의존성 | 상태 | 설명 |
|--------|------|------|
| Phase 10 (True Agentic) — LangGraph 17-노드 그래프 | 완료 | Director Plan 노드 + StateGraph 인프라 |
| `DirectorPlanOutput` Pydantic 모델 | 완료 | `llm_models.py`에 5필드 정의 |
| `director_plan.j2` Jinja2 템플릿 | 완료 | Project Brief + Mission + JSON Format |
| `StoryboardPreset` dataclass | 완료 | `presets.py`에 id/name/structure/template 등 |
| `ScriptState` TypedDict (total=False) | 완료 | `state.py`에 character_id/structure/style 등 |
| Phase 18 (Stage Workflow) | 완료 | Stage 탭 인프라 (비교 카드 배치용) |
| Phase 19 (탭 페르소나 재배치) | 완료 | Stage = 프로듀서 소유 |
| SSE `_NODE_META` + `_build_node_payload` | 완료 | `scripts.py` router |
| **`useScriptEditor.ts` 분리** (Phase B 선행) | **미완료** | 832줄 → SSE 파싱 + 스토어 동기화 분리 |

---

## 9. 테스트 전략

### Phase A (~42개)

| 범위 | 예상 수량 |
|------|----------|
| `inventory.py` 캐릭터 프루닝 (경계값, 빈 그룹, LoRA 우선순위, group JOIN) | ~12 |
| `inventory.py` 구조/스타일 메타데이터 로딩 | ~5 |
| `director_plan.j2` 템플릿 렌더링 (인벤토리 주입 + CoT 가이드) | ~5 |
| `DirectorPlanOutput` casting 필드 + model_validator 검증 | ~6 |
| `inventory_resolve` 노드 (user override 6시나리오 + 5항목 유효성) | ~8 |
| Graph 엣지 통합 테스트 (Full/Quick/Express 3모드) | ~4 |
| SSE `inventory_resolve` node_result 전달 | ~2 |

### Phase B (~15개)

| 범위 | 예상 수량 |
|------|----------|
| CharacterSelector AI 추천 그룹 렌더링 | ~3 |
| 캐스팅 배너 표시/수락/거절 | ~3 |
| StageCastingCompareCard 라이프사이클 (생성→수락→소멸) | ~4 |
| `useStoryboardStore` 캐스팅 상태 동기화 | ~2 |
| SSE 에러 케이스 + 캐스팅 실패 UI | ~3 |

### Phase C (~12개)

| 범위 | 예상 수량 |
|------|----------|
| `director_plan_lite` Flash 모델 응답 검증 | ~4 |
| Express 라우팅 3분기 (director_plan_lite → writer) | ~3 |
| Fallback 전략 (캐스팅 실패 → 최근 사용 캐릭터) | ~3 |
| One-Click Express E2E + 결정 요약 카드 | ~2 |

**총 ~69개 테스트**

---

## 10. 스코프 외

| 항목 | 이유 |
|------|------|
| 캐릭터 Chemistry 점수 | 2인 구조 최적화는 후속 고도화 |
| 토픽 자동 분류기 (ML 모델) | Director LLM의 자연어 이해로 대체 |
| 캐스팅 히스토리 학습 (성공률 기반) | 데이터 충분히 축적 후 검토 |
| LoRA 자동 다운로드/설치 | 인프라 레벨 기능, 별도 Phase |
| Multi-Group 크로스 캐스팅 | 보안/권한 이슈, 별도 설계 필요 |
| `StoryboardPreset` 구조 변경 | inventory.py 내 상수로 분리 (SRP) |
| Character 모델에 `group_id` FK 추가 | 전역 엔티티 원칙 유지, 간접 조인으로 해결 |

---

## 11. 관련 파일

### Backend 신규

| 파일 | Phase | 설명 |
|------|-------|------|
| `services/agent/inventory.py` | A | 인벤토리 로딩 + 프루닝 서비스 (300줄 초과 시 loader/summarizer 분리) |
| `services/agent/nodes/inventory_resolve.py` | A | user override vs Director 추천 병합 + 5항목 검증 |
| `services/agent/nodes/director_plan_lite.py` | C | 경량 캐스팅 전용 노드 (Flash, 10명 제한) |
| `templates/creative/director_plan_lite.j2` | C | 경량 캐스팅 템플릿 |

### Backend 수정

| 파일 | Phase | 변경 내용 |
|------|-------|----------|
| `services/agent/llm_models.py` | A | `CastingRecommendation` (model_validator) + `DirectorPlanOutput.casting` |
| `services/agent/state.py` | A | `casting_recommendation` + `valid_character_ids` state key 추가 |
| `services/agent/nodes/director_plan.py` | A | 인벤토리 로드 → template_vars 추가 + return에 `casting_recommendation` 포함 |
| `templates/creative/director_plan.j2` | A | 인벤토리 섹션 + CoT 캐스팅 가이드 + casting JSON format |
| `services/agent/script_graph.py` | A,C | `inventory_resolve` 노드 등록 + 엣지 변경 (C: conditional_edges 확장) |
| `services/agent/routing.py` | C | `route_after_start` 3분기 추가 (`director_plan_lite`) |
| `config_pipelines.py` | A | `INVENTORY_MAX_CHARACTERS`, `INVENTORY_CASTING_ENABLED` 상수 |
| `routers/scripts.py` | A | `_NODE_META`에 `inventory_resolve` 등록 |
| `schemas.py` | A | `CastingRecommendationResponse` 스키마 |

### Frontend 수정

| 파일 | Phase | 변경 내용 |
|------|-------|----------|
| `CharacterSelector.tsx` | B | "AI Recommended" 그룹 + Sparkles 배지 |
| `StageCastingCompareCard.tsx` (신규) | B | 캐스팅 비교 카드 (경량 버전) |
| `StageCharactersSection.tsx` | B | StageCastingCompareCard 삽입 |
| `useScriptEditor.ts` (분리 후) | B | `inventory_resolve` node_result → `useStoryboardStore` 동기화 |
| `pipelineSteps.ts` | B | "디렉터/캐스팅" 스텝에 `inventory_resolve` 노드 추가 |
| `types/index.ts` | B | `CastingRecommendation` 타입 |
| `useStoryboardStore.ts` | B | `castingRecommendation` 상태 + `setCastingRecommendation` 액션 |

### 문서

| 문서 | 업데이트 내용 |
|------|-------------|
| `docs/01_product/ROADMAP.md` | Phase 20 등록 |
| `docs/03_engineering/api/REST_API.md` | SSE `inventory_resolve` 노드 이벤트 |
| `docs/03_engineering/architecture/DB_SCHEMA.md` | 스키마 변경 없음 (state 레벨) |

---

## 12. 6-Agent Cross Review 반영 내역

| 에이전트 | BLOCKER 해소 | 주요 반영 |
|---------|-------------|----------|
| **PM** | DoD #3 기준 구체화, StoryboardPreset SSOT | DoD에 정량 메트릭 추가, 구조 메타를 inventory.py 내 상수로 분리 |
| **Backend** | group_id 미존재, storyboard_count 미존재, 반환값 구조 | 간접 JOIN 쿼리 설계, director_plan_node return dict 명시, DB 세션 관리 |
| **Frontend** | useScriptEditor 832줄, SSE 프로토콜 이중화, PipelineStatusDots 오류 | Phase B 선행 리팩터링, node_result 기반 통일, pipelineSteps.ts로 정정 |
| **Tech Lead** | Phase C routing 누락, sample_image_url URL 위반 | Phase C에 routing.py/script_graph.py 명시, 스타일 요약에서 URL 제거 |
| **UX/UI** | auto_cast 상세, 비교 카드 라이프사이클, Express 신뢰 | auto_cast → character_id null 단순화, 카드 상태 5단계 정의, 결정 요약 카드 |
| **Prompt Eng** | group_id(재확인), 데이터 소스 부재 | 자연어 요약, CoT 가이드, character_name 교차검증, 20명 상한 |
