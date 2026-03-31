Now let me check the Tag model and the admin router for this endpoint:
Now let me check the router to see how the classify endpoint is defined:
Now I have enough context. Let me also quickly check for any bulk/batch patterns already used in the codebase:
Good — there's already a pattern using `on_conflict_do_update` in the import script. Let me check the test file and the Tag model's classification fields:
Now I have all the context needed. Let me write the design.


# SP-126: Admin tags/classify N+1 쿼리 최적화 — 상세 설계

## 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `backend/services/tag_classifier.py` | 수정 | `_lookup_db_batch()`, `_save_classification_batch()` 추가, `classify_batch()` 리팩터링 |
| `backend/tests/test_tag_classifier_batch.py` | 신규 | N+1 회귀 테스트 + 배치 메서드 단위 테스트 |

---

## DoD 1: `_lookup_db()` → 배치 쿼리로 변환 (WHERE name IN (...))

### 구현 방법

**새 메서드 `_lookup_db_batch(tags: list[str]) -> dict[str, ClassificationResult]` 추가.**

현재 `_lookup_db(tag)` 는 단일 태그에 `select(Tag).where(Tag.name == tag)` 실행 → N번 호출.

```python
def _lookup_db_batch(self, tags: list[str]) -> dict[str, ClassificationResult]:
    """Batch lookup tags in database. Single query with WHERE name IN (...)."""
    if not tags:
        return {}

    stmt = select(Tag).where(Tag.name.in_(tags))
    rows = self.db.execute(stmt).scalars().all()

    results: dict[str, ClassificationResult] = {}
    for row in rows:
        if not row.group_name:
            continue
        # Legacy unclassified 판별 (기존 _lookup_db 로직 동일)
        if row.group_name == "subject" and row.classification_source in (None, "default"):
            results[row.name] = {
                "group": row.group_name,
                "confidence": 0.3,
                "source": "db",
            }
        else:
            results[row.name] = {
                "group": row.group_name,
                "confidence": max(
                    row.classification_confidence
                    if isinstance(row.classification_confidence, (int, float))
                    else 1.0,
                    0.9,
                ),
                "source": "db",
            }
    return results
```

**`classify_batch()` 수정**: Second pass 루프를 `_lookup_db_batch()` 단일 호출로 교체.

```python
# Before (N+1):
for tag in no_rule_match:
    normalized = normalize_prompt_token(tag)
    db_result = self._lookup_db(normalized)
    ...

# After (1 query):
normalized_map = {tag: normalize_prompt_token(tag) for tag in no_rule_match}
db_results = self._lookup_db_batch(list(normalized_map.values()))
for tag in no_rule_match:
    norm = normalized_map[tag]
    db_result = db_results.get(norm)
    if db_result and db_result["confidence"] >= 0.8:
        results[tag] = db_result
    else:
        still_unknown.append(tag)
```

**기존 `_lookup_db()` 유지**: `classify()` (단건) 메서드에서 사용 중이므로 삭제하지 않음.

### 동작 정의

- 태그 50개 요청 시 DB 조회 쿼리 1회 (기존 최대 50회 → 1회)
- 반환 결과는 기존과 동일 (ClassificationResult dict)
- confidence 판별 로직 (0.8 threshold, legacy subject 0.3) 기존과 동일

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| `tags` 빈 리스트 | `_lookup_db_batch` 즉시 빈 dict 반환 |
| DB에 없는 태그 | 결과 dict에 포함 안 됨 → `still_unknown`으로 분류 |
| 동일 태그 중복 입력 | `normalize_prompt_token` 후 중복 → `IN` 절에서 자연스럽게 dedup, 원본 tag loop에서 같은 결과 매핑 |
| `group_name`이 NULL인 태그 | `_lookup_db_batch`에서 `continue` → 결과에 미포함 (기존 동작 동일) |

---

## DoD 2: `_save_classification()` → bulk insert/update로 변환

### 구현 방법

**새 메서드 `_save_classification_batch(items: list[tuple[str, ClassificationResult]]) -> None` 추가.**

PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` (upsert) 패턴 사용. 프로젝트 내 `scripts/import_wd14_tags.py:226`에 동일 패턴 존재.

```python
def _save_classification_batch(
    self,
    items: list[tuple[str, ClassificationResult]],
    *,
    defer_commit: bool = False,
) -> None:
    """Bulk upsert classification results. Single query."""
    if not items:
        return

    from sqlalchemy.dialects.postgresql import insert

    rows = []
    for tag, result in items:
        tag = normalize_prompt_token(tag)
        if not tag:
            continue
        default_layer = GROUP_NAME_TO_LAYER.get(result["group"] or "", 1)
        category = self._group_to_category(result["group"])
        rows.append({
            "name": tag,
            "category": category,
            "group_name": result["group"],
            "default_layer": default_layer,
            "classification_source": result["source"],
            "classification_confidence": result["confidence"],
        })

    if not rows:
        return

    try:
        stmt = insert(Tag).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["name"],
            set_={
                "group_name": stmt.excluded.group_name,
                "default_layer": stmt.excluded.default_layer,
                "classification_source": stmt.excluded.classification_source,
                "classification_confidence": stmt.excluded.classification_confidence,
            },
        )
        self.db.execute(stmt)
        if not defer_commit:
            self.db.commit()
        logger.info("✅ [TagClassifier] Batch saved %d tags", len(rows))
    except Exception as e:
        logger.error("❌ [TagClassifier] Batch save failed: %s", e)
        self.db.rollback()
```

**`classify_batch()` 수정**: First pass에서 rule 매칭된 태그를 모아두고 한 번에 `_save_classification_batch()` 호출.

```python
# Before (N+1):
for tag in tags:
    ...
    if rule_result and rule_result["confidence"] >= 0.9:
        self._save_classification(normalized, rule_result)  # 개별 INSERT/UPDATE

# After (1 query):
rule_matched: list[tuple[str, ClassificationResult]] = []
for tag in tags:
    ...
    if rule_result and rule_result["confidence"] >= 0.9:
        rule_matched.append((normalized, rule_result))
        results[tag] = rule_result
    ...
if rule_matched:
    self._save_classification_batch(rule_matched)
```

**기존 `_save_classification()` 유지**: `classify()` (단건), `classify_batch_with_llm()`, background 함수들에서 개별 호출로 사용 중. 이들은 이번 스코프 밖.

### 동작 정의

- rule 매칭된 태그 N개 → INSERT/UPDATE 쿼리 1회 (기존 최대 N회 → 1회)
- 기존 태그 → `ON CONFLICT DO UPDATE` (group_name, default_layer, classification_source, classification_confidence 갱신)
- 신규 태그 → INSERT
- commit은 배치 완료 후 1회

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| `items` 빈 리스트 | 즉시 반환 |
| `normalize_prompt_token` 결과가 빈 문자열 | `rows`에서 제외 (skip) |
| DB 에러 (constraint violation 등) | rollback + 에러 로그 (기존 동작 동일) |
| `_group_to_category()` 호출 N+1 우려 | `group_to_category()` 함수가 `db.query().limit(1)` → 최대 고유 group 수 만큼 호출 (보통 5-10개). 50태그여도 group 종류는 제한적이므로 허용 범위. 캐시 최적화는 out of scope |

### 주의: Tag.validates 바이패스

`on_conflict_do_update`는 ORM 레벨이 아닌 Core 레벨 실행이므로 `Tag._validate_group_name`(group_name 변경 시 `default_layer` 자동 동기화) 트리거가 작동하지 않음. **이를 보완하기 위해 `_save_classification_batch`에서 `default_layer`를 명시적으로 계산하여 upsert 값에 포함** (`GROUP_NAME_TO_LAYER.get(...)` 호출). 기존 `_save_classification()`도 동일하게 `default_layer`를 명시 계산하므로 동작 일치.

---

## DoD 3: 기존 테스트 통과 + N+1 회귀 테스트 추가

### 영향 범위

- `backend/tests/test_router_tags.py` — 기존 `test_classify_tags` 등은 `classify_batch`를 mock하므로 내부 구현 변경에 영향 없음. 통과 유지.
- `backend/tests/test_prompt_fixes.py` — `_lookup_db` 단건 테스트. 메서드 유지하므로 영향 없음.

### 테스트 전략

**신규 파일: `backend/tests/test_tag_classifier_batch.py`**

| 테스트 | 검증 내용 |
|--------|----------|
| `test_lookup_db_batch_single_query` | `_lookup_db_batch(N개)` 호출 시 `db.execute` 정확히 1회 호출 (N+1 회귀 방지) |
| `test_lookup_db_batch_empty` | 빈 리스트 → 빈 dict, `db.execute` 0회 |
| `test_lookup_db_batch_legacy_subject_low_confidence` | `group_name="subject"`, `classification_source=None` → confidence 0.3 |
| `test_lookup_db_batch_classified_high_confidence` | 명시 분류 태그 → confidence ≥ 0.9 |
| `test_lookup_db_batch_no_group_name_excluded` | `group_name=None` 태그 → 결과에서 제외 |
| `test_save_classification_batch_single_query` | `_save_classification_batch(N개)` 호출 시 `db.execute` 정확히 1회 |
| `test_save_classification_batch_empty` | 빈 리스트 → `db.execute` 0회 |
| `test_save_classification_batch_rollback_on_error` | DB 에러 시 rollback 호출 확인 |
| `test_classify_batch_uses_batch_methods` | `classify_batch()` 호출 시 `_lookup_db_batch` 사용 + `_save_classification_batch` 사용 확인 (spy/patch) |

**테스트 방식**: `unittest.mock.MagicMock`으로 DB 세션 mock. `db.execute` 호출 횟수로 N+1 회귀 검증.

---

## Out of Scope

- `classify()` 단건 메서드 최적화 (호출 경로가 다름, 이번 이슈는 `classify_batch`만 대상)
- `classify_batch_with_llm()` 배치 최적화 (이미 `defer_commit=True`로 부분 최적화됨)
- `classify_tags_background()` / `classify_tags_background_llm()` 최적화 (background 함수, 별도 이슈)
- `_group_to_category()` 캐시 최적화 (group 종류 수가 제한적이라 실질적 병목 아님)
- `_save_classification_batch`에 `valence` 파라미터 지원 (현재 classify_batch에서 valence 저장 안 함)

---

## BLOCKER

없음. DB 스키마 변경 없음, 외부 의존성 추가 없음. `sqlalchemy.dialects.postgresql.insert`는 이미 프로젝트에서 사용 중 (`migrate_patterns_to_rules`, `import_wd14_tags.py`).