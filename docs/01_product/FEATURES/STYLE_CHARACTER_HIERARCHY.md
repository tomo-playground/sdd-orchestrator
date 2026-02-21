# StyleProfile-Character Hierarchy (화풍 루트 아키텍처)

**상태**: Phase 0~2 완료 (DB + API + Wizard)
**우선순위**: P1 (Scene Diversity 이후)
**최종 갱신**: 2026-02-21

---

## 1. 문제 정의

### 현황

현재 StyleProfile(화풍)과 Character(캐릭터)가 **독립 엔티티**로 존재하여 아무 조합이나 가능하다.

```
현재 구조:
  StyleProfile ──(설정값)── group_config ── Group
  Character ──(독립)── Project (optional)
  Scene ──(자유 선택)── 아무 Character
```

### 발생 문제

| 문제 | 실제 사례 | 영향 |
|------|----------|------|
| **SD 모델 불일치** | Anime 캐릭터 → Realistic 그룹 | 이미지 완전 파괴 |
| **LoRA 충돌** | flat_color 캐릭터 → Default Anime 그룹 | 스타일 불안정 (#443) |
| **LoRA 이중 적용** | flat_color 캐릭터 → Flat Color 그룹 | 과적용 (0.6+0.4=1.0) |
| **Preview 불일치** | 캐릭터 프리뷰가 다른 화풍으로 생성됨 | IP-Adapter 참조 오류 |
| **사용자 혼란** | 캐릭터 선택에 필터 없음 | 잘못된 조합 빈번 |

### 근본 원인

**화풍이 "루트"가 아닌 "설정값"으로 취급됨.** 캐릭터는 특정 화풍의 SD 모델 + LoRA 조합에서만 정상 동작하지만, 이 종속 관계가 데이터 모델에 표현되지 않는다.

---

## 2. 목표 구조

### 화풍(StyleProfile) = 루트

```
StyleProfile (화풍)          ← ROOT
  ├── SD Model               ← base checkpoint
  ├── Style LoRAs            ← 화풍 전용 LoRA
  ├── Quality / Negative     ← 기본 품질 태그
  │
  └── Characters             ← 이 화풍 전용 캐릭터
        ├── Character LoRA   ← 호환 보장
        ├── Appearance Tags  ← 화풍에 맞는 태그
        └── Preview Image    ← 이 화풍으로 생성됨

Project
  └── Group → StyleProfile 선택
        └── Storyboard
              └── Scene → 해당 StyleProfile의 Character만 선택
```

### 핵심 원칙

1. **캐릭터는 화풍에 종속**: 캐릭터 생성 시 화풍 지정 필수
2. **씬은 호환 캐릭터만 선택 가능**: 그룹 화풍 → 캐릭터 자동 필터
3. **LoRA 중복 감지**: StyleProfile LoRA와 Character LoRA 충돌 시 경고/자동 조정
4. **Preview = 실제 화풍**: 캐릭터 프리뷰 이미지는 소속 화풍으로 생성

---

## 3. 구현 범위

### Phase 0: DB 스키마 + 마이그레이션

| 작업 | 상세 |
|------|------|
| `characters.style_profile_id` FK 추가 | `style_profiles.id` 참조, nullable (하위 호환) |
| Alembic 마이그레이션 | 컬럼 추가 + 기존 데이터 역매핑 |
| 기존 캐릭터 역매핑 | LoRA 기반 자동 추론 (아래 매핑 테이블 참조) |

**역매핑 규칙** (기존 데이터):

| 캐릭터 (id) | LoRA | 추론 StyleProfile |
|-------------|------|------------------|
| Flat Color Girl (8) | flat_color (style) | Flat Color Anime (id=3) |
| Flat Color Boy (12) | flat_color (style) | Flat Color Anime (id=3) |
| J_huiben Girl (13) | J_huiben (style) | Children Picture Book (id=4) |
| J_huiben Boy (14) | J_huiben (style) | Children Picture Book (id=4) |
| Midoriya (3) | mha_midoriya (character) | Default Anime (id=1) |
| Harukaze Doremi (9) | harukaze-doremi-casual (style) | Default Anime (id=1) ※ |

> ※ Doremi의 LoRA(`lora_id=7`)는 어떤 StyleProfile에도 등록되어 있지 않음.
> 향후 Doremi 전용 StyleProfile 생성을 권장하나, Phase 0에서는 Default Anime 폴백.

**마이그레이션 방식**: 캐릭터 6개이므로 LoRA 추론 알고리즘 대신 **명시적 딕셔너리 매핑** 사용.

```python
EXPLICIT_MAPPING = {
    3: 1,   # Midoriya → Default Anime
    8: 3,   # Flat Color Girl → Flat Color Anime
    9: 1,   # Doremi → Default Anime (폴백)
    12: 3,  # Flat Color Boy → Flat Color Anime
    13: 4,  # J_huiben Girl → Children Picture Book
    14: 4,  # J_huiben Boy → Children Picture Book
}
```

### Phase 1: Backend API

| 작업 | 상세 |
|------|------|
| `GET /characters?style_profile_id=N` | 화풍별 캐릭터 필터 |
| `POST /characters` 요청에 `style_profile_id` **optional** 추가 | DB nullable 유지, Phase 2 완료 후 필수화 |
| `GET /characters` 응답에 `style_profile` 요약 포함 | 프론트엔드 표시용 |
| LoRA 중복 감지 API | 캐릭터 LoRA vs StyleProfile LoRA 충돌 체크 |
| LoRA 중복 경고 로그 | `ConsistencyResolver`에서 중복 LoRA 감지 시 WARNING 로그 |

> **주의**: Phase 1에서 `style_profile_id`를 API 필수로 변경하면, Phase 2(Wizard 화풍 선택)
> 배포 전까지 캐릭터 생성 불가 구간이 발생한다. **Phase 2 완료 후 일괄 필수화** 또는
> Phase 1+2를 하나의 릴리스 단위로 묶어야 한다.

### Phase 2: 캐릭터 생성 Wizard 개선

| 작업 | 상세 |
|------|------|
| Step 0: 화풍 선택 | StyleProfile 목록에서 선택 (카드 UI) |
| LoRA Step 필터링 | 선택된 화풍의 SD 모델과 호환되는 LoRA만 표시 |
| Preview 생성 | 선택된 화풍의 SD 모델 + LoRA로 미리보기 생성 |
| LoRA 중복 경고 | StyleProfile에 이미 있는 LoRA 선택 시 경고 |

### Phase 3: 캐릭터 선택 필터링

| 작업 | 상세 |
|------|------|
| ScriptTab 캐릭터 드롭다운 | 현재 그룹의 StyleProfile 기반 필터 |
| SetupWizard 캐릭터 선택 | 동일 필터 적용 |
| Multi-char 씬 필터링 | Character A, B 모두 동일 StyleProfile 제약 |
| 비호환 캐릭터 표시 | 숨기기 or 비활성 + 경고 라벨 |
| 캐릭터 없는 화풍 안내 | "이 화풍에 캐릭터가 없습니다. 새로 만드세요." |
| 화풍 미설정 그룹 처리 | GroupConfig.style_profile_id=NULL → 필터 미적용 + 화풍 설정 권장 안내 |

### Phase 4: LoRA 충돌 방지

| 작업 | 상세 |
|------|------|
| 이미지 생성 시 LoRA 중복 제거 | 캐릭터 LoRA == StyleProfile LoRA → 한 번만 적용 |
| Weight 자동 조정 | 중복 시 높은 weight 채택 |
| SD 모델 검증 | 캐릭터의 화풍 SD 모델 != 그룹 화풍 SD 모델 → 에러 |
| `prepare_prompt()` 검증 | 진입 시 `character.style_profile_id != group.config.style_profile_id` → 경고 로그 + 진행 |

---

## 4. UI 변경

### 4.1 캐릭터 Wizard — Step 0 추가

```
┌─────────────────────────────────────┐
│  Select Style                       │
│                                     │
│  ┌──────────┐  ┌──────────┐        │
│  │  Anime   │  │Flat Color│        │
│  │ Default  │  │  Anime   │        │
│  │          │  │          │        │
│  │ ✓ 선택됨 │  │          │        │
│  └──────────┘  └──────────┘        │
│                                     │
│  ┌──────────┐  ┌──────────┐        │
│  │ Children │  │Realistic │        │
│  │ Picture  │  │          │        │
│  │  Book    │  │          │        │
│  └──────────┘  └──────────┘        │
└─────────────────────────────────────┘
```

### 4.2 캐릭터 선택 드롭다운 — 필터링

```
현재:
  [Midoriya          ▾]    ← 전체 캐릭터
  [Flat Color Girl   ]
  [Flat Color Boy    ]
  [J_huiben Girl     ]

개선:
  [Flat Color Girl   ▾]    ← 현재 화풍(Flat Color Anime) 캐릭터만
  [Flat Color Boy    ]
  ──────────────────────
  다른 화풍 캐릭터 (비호환)  ← 접혀있거나 비활성
```

---

## 5. 데이터 모델 변경

### ERD 변경

```
style_profiles (기존)
  id, name, sd_model_id, loras, ...

characters (변경)
  id, name, ...
  + style_profile_id  FK → style_profiles.id  (nullable, ondelete=SET NULL)
  + ix_characters_style_profile_id  btree INDEX
```

**ORM relationship 정의** (필수):

```python
# models/character.py
style_profile_id: Mapped[int | None] = mapped_column(
    Integer,
    ForeignKey("style_profiles.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)
style_profile: Mapped["StyleProfile | None"] = relationship(
    "StyleProfile", foreign_keys=[style_profile_id],
)
```

### API 스키마 변경

```python
# POST /characters (Request)
class CharacterCreateRequest:
    name: str
    gender: str
    style_profile_id: int | None = None  # Phase 0~1: optional, Phase 2 완료 후: 필수

# GET /characters (Response)
class CharacterListItem:
    id: int
    name: str
    style_profile_id: int | None
    style_profile_name: str | None  # 화풍 이름 (조인)
```

---

## 6. 마이그레이션 전략

### 단계적 적용 (하위 호환성 보장)

1. **Phase 0**: `style_profile_id` nullable로 추가 → 기존 코드 영향 없음
2. **Phase 0**: 기존 캐릭터 명시적 딕셔너리 역매핑 (data migration)
3. **Phase 1**: API에 `style_profile_id` 필터 추가 (**optional** param)
4. **Phase 2**: Wizard에 화풍 선택 추가 → 완료 시 `POST /characters` API 필수화
5. **Phase 3**: 캐릭터 선택 UI 필터링 적용
6. **Future**: `style_profile_id` NOT NULL 전환

**NOT NULL 전환 사전 조건**:
```sql
-- 전환 전 반드시 실행: 결과가 0이어야 전환 가능
SELECT count(*) FROM characters
WHERE style_profile_id IS NULL AND deleted_at IS NULL;
```
NOT NULL 전환은 역매핑과 **별도 마이그레이션 파일**로 분리.

---

## 7. 테스트 계획

| 카테고리 | 테스트 | 예상 수 |
|----------|--------|---------|
| DB 마이그레이션 | 역매핑 정확성, FK 제약 | 4 |
| API 필터 | `?style_profile_id=` 필터 동작 | 4 |
| LoRA 중복 감지 | 동일 LoRA, 다른 LoRA, 빈 LoRA | 4 |
| 캐릭터 생성 | style_profile_id 포함/미포함 | 3 |
| 이미지 생성 | LoRA 이중 적용 방지 | 3 |
| Multi-char | A/B 모두 동일 화풍 제약 | 2 |
| 화풍 미설정 | GroupConfig null 시 필터 미적용 | 2 |
| StyleProfile 삭제 | SET NULL 후 캐릭터 상태 확인 | 2 |
| **총** | | **~24** |

---

## 8. 선행 조건

- Phase 11 (Scene Diversity) 완료 ← **완료됨**
- StyleProfile CRUD 안정 ← **완료됨**
- Character Builder Wizard ← **완료됨**

## 9. 주의 사항 (리뷰 반영)

| 항목 | 내용 |
|------|------|
| **배포 순서** | Phase 1에서 API 필수화 금지. Phase 2 Wizard 완료 후 일괄 필수화 |
| **기존 Preview** | 역매핑 후 preview 재생성 불필요 (opt-in: `/{id}/regenerate-reference`) |
| **StyleProfile 삭제** | `SET NULL` 후 "소속 없는 캐릭터" 발생 → 삭제 API에서 소속 캐릭터 수 경고 |
| **useCharacters Hook** | `style_profile_id` 필터 추가 시 모든 호출 사이트 점검 (관리 페이지는 전체 목록 필요) |
| **문서 업데이트** | 구현 시 DB_SCHEMA.md, SCHEMA_SUMMARY.md, DB_SCHEMA_CHANGELOG.md 동시 갱신 |

## 10. 관련 문서

- [PROJECT_GROUP.md](PROJECT_GROUP.md) — 프로젝트/그룹 시스템
- [CHARACTER_BUILDER.md](CHARACTER_BUILDER.md) — 캐릭터 빌더
- `docs/03_engineering/architecture/DB_SCHEMA.md` — DB 스키마
