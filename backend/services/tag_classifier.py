"""Dynamic Tag Classification Service (15.7).

Hybrid classification: DB Cache → Rules → Danbooru API → LLM Fallback
Replaces hardcoded CATEGORY_PATTERNS with dynamic, learnable system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import logger
from models.tag import ClassificationRule, Tag

if TYPE_CHECKING:
    pass


class ClassificationResult(TypedDict):
    """Result of tag classification."""

    group: str | None
    confidence: float
    source: str  # 'db', 'rule', 'danbooru', 'llm'


# Danbooru category mapping (ID → SD group hint)
DANBOORU_CATEGORY_MAP = {
    0: None,  # General - needs further classification
    1: "style",  # Artist
    3: None,  # Copyright - usually not useful for SD
    4: "identity",  # Character
    5: "quality",  # Meta
}


class TagClassifier:
    """Hybrid tag classification service."""

    def __init__(self, db: Session):
        self.db = db
        self._rules_cache: list[ClassificationRule] | None = None

    def classify(self, tag: str) -> ClassificationResult:
        """Classify a single tag.

        Priority:
        1. Pattern rules (classification_rules table) - always check first
        2. DB cache (existing tag with group_name)
        3. Danbooru API (if available)
        4. LLM fallback (Gemini)
        """
        from services.keywords.core import normalize_prompt_token

        # Disable lower() in normalize_prompt_token if we want case-sensitive (but tokens are usually lower)
        # normalize_prompt_token returns lowercased, stripped, weight-removed string
        normalized = normalize_prompt_token(tag)
        # DB uses underscores, normalize_prompt_token uses underscores. Perfect.

        # Step 1: Rule-based classification (highest priority)
        rule_result = self._apply_rules(normalized)
        if rule_result and rule_result["confidence"] >= 0.9:
            # Save to DB (will override any existing Danbooru classification)
            self._save_classification(normalized, rule_result)
            return rule_result

        # Step 2: DB lookup (only if no rule matched)
        db_result = self._lookup_db(normalized)
        if db_result and db_result["confidence"] >= 0.8:
            return db_result

        # Step 3: Danbooru API
        danbooru_result = self._classify_via_danbooru(normalized)
        if danbooru_result and danbooru_result["group"]:
            self._save_classification(normalized, danbooru_result)
            return danbooru_result

        # Step 4: LLM fallback (placeholder - implement with Gemini)
        # For now, return unknown
        return {
            "group": None,
            "confidence": 0.0,
            "source": "unknown",
        }

    def _classify_via_danbooru(self, tag: str) -> ClassificationResult | None:
        """Classify tag using Danbooru API."""
        from services.danbooru import classify_from_danbooru, get_tag_info_sync
        from services.keywords.core import normalize_prompt_token

        try:
            # Danbooru uses underscores, weight removal handled by normalize_prompt_token
            # limit: normalize_prompt_token handles space->underscore
            normalized = normalize_prompt_token(tag)
            tag_info = get_tag_info_sync(normalized)
            if tag_info:
                group = classify_from_danbooru(tag_info)
                if group:
                    logger.info(
                        "🏷️ [Danbooru] Classified '%s' → %s (category=%s, posts=%d)",
                        tag,
                        group,
                        tag_info.get("category_name"),
                        tag_info.get("post_count", 0),
                    )
                    return {
                        "group": group,
                        "confidence": 0.85,
                        "source": "danbooru",
                    }
        except Exception as e:
            logger.warning("⚠️ [Danbooru] Classification failed for '%s': %s", tag, e)

        return None

    def classify_batch(
        self,
        tags: list[str],
        *,
        sync_danbooru: bool = False,
    ) -> tuple[dict[str, ClassificationResult], list[str]]:
        """Classify multiple tags. Returns (results, pending_tags).

        Step 1-2 (Rules + DB) are always synchronous.
        Step 3 (Danbooru) is deferred to background by default.

        Args:
            tags: Tags to classify
            sync_danbooru: If True, call Danbooru synchronously (legacy behavior)

        Returns:
            (results_dict, pending_tags_for_background)
        """
        from services.keywords.core import normalize_prompt_token

        results: dict[str, ClassificationResult] = {}
        no_rule_match = []

        # First pass: check pattern rules (highest priority)
        for tag in tags:
            normalized = normalize_prompt_token(tag)
            rule_result = self._apply_rules(normalized)
            if rule_result and rule_result["confidence"] >= 0.9:
                self._save_classification(normalized, rule_result)
                results[tag] = rule_result
            else:
                no_rule_match.append(tag)

        # Second pass: check DB cache for tags without rule match
        still_unknown = []
        for tag in no_rule_match:
            normalized = normalize_prompt_token(tag)
            db_result = self._lookup_db(normalized)
            if db_result and db_result["confidence"] >= 0.8:
                results[tag] = db_result
            else:
                still_unknown.append(tag)

        # Sync mode: Danbooru inline (legacy, for admin/testing)
        if sync_danbooru:
            for tag in still_unknown[:10]:
                normalized = normalize_prompt_token(tag)
                danbooru_result = self._classify_via_danbooru(normalized)
                if danbooru_result and danbooru_result["group"]:
                    self._save_classification(normalized, danbooru_result)
                    results[tag] = danbooru_result
                else:
                    results[tag] = {"group": None, "confidence": 0.0, "source": "unknown"}
            for tag in still_unknown[10:]:
                results[tag] = {"group": None, "confidence": 0.0, "source": "unknown"}
            return results, []

        # Async mode (default): mark unknown, defer Danbooru to background
        for tag in still_unknown:
            results[tag] = {"group": None, "confidence": 0.0, "source": "pending"}

        return results, still_unknown

    def _lookup_db(self, tag: str) -> ClassificationResult | None:
        """Look up tag in database.

        Legacy tags (group_name="subject", source=NULL) are unclassified dumps.
        Return low confidence so Danbooru/LLM can reclassify them.
        """
        stmt = select(Tag).where(Tag.name == tag)
        result = self.db.execute(stmt).scalar_one_or_none()

        if result and result.group_name:
            # Legacy unclassified: subject + default/null source → low confidence (falls through to LLM)
            if result.group_name == "subject" and result.classification_source in (None, "default"):
                return {
                    "group": result.group_name,
                    "confidence": 0.3,
                    "source": "db",
                }
            # DB에 명시적으로 분류된 태그는 최소 0.9 confidence 보장
            return {
                "group": result.group_name,
                "confidence": max(result.classification_confidence or 1.0, 0.9),
                "source": "db",
            }
        return None

    def _get_rules(self) -> list[ClassificationRule]:
        """Get classification rules (cached)."""
        if self._rules_cache is None:
            stmt = (
                select(ClassificationRule)
                .where(ClassificationRule.is_active == True)  # noqa: E712
                .order_by(ClassificationRule.priority.desc())
            )
            self._rules_cache = list(self.db.execute(stmt).scalars().all())
        return self._rules_cache

    def _apply_rules(self, tag: str) -> ClassificationResult | None:
        """Apply pattern rules to classify tag."""
        rules = self._get_rules()

        for rule in rules:
            matched = False
            pattern = rule.pattern.lower()

            if rule.rule_type == "exact":
                matched = tag == pattern
            elif rule.rule_type == "suffix":
                matched = tag.endswith(pattern)
            elif rule.rule_type == "prefix":
                matched = tag.startswith(pattern)
            elif rule.rule_type == "contains":
                matched = pattern in tag

            if matched:
                return {
                    "group": rule.target_group,
                    "confidence": 0.95,
                    "source": "rule",
                }

        return None

    async def classify_batch_with_llm(
        self,
        tags: list[str],
    ) -> dict[str, ClassificationResult]:
        """Rules + DB + Danbooru + LLM 배치 분류 (async).

        기존 classify_batch(sync_danbooru=True) 실행 후,
        여전히 미분류인 태그를 Gemini Flash로 배치 분류한다.
        """
        results, _pending = self.classify_batch(tags, sync_danbooru=True)

        truly_unknown = [t for t, r in results.items() if not r.get("group")]
        if truly_unknown:
            from services.tag_classifier_llm import classify_tags_via_llm

            llm_results = await classify_tags_via_llm(truly_unknown)
            for lr in llm_results:
                result: ClassificationResult = {
                    "group": lr["group_name"],
                    "confidence": lr["confidence"],
                    "source": "llm",
                }
                self._save_classification(lr["tag"], result, defer_commit=True)
                results[lr["tag"]] = result
            # 배치 완료 후 한 번에 commit
            try:
                self.db.commit()
            except Exception as e:
                logger.error("❌ [TagClassifier] Batch LLM commit failed: %s", e)
                self.db.rollback()

        return results

    def _save_classification(
        self, tag: str, result: ClassificationResult, *, defer_commit: bool = False,
    ) -> None:
        """Save classification result to DB.

        Args:
            defer_commit: True이면 commit을 건너뛴다 (배치 호출 시 호출자가 commit).
        """
        from services.keywords.patterns import GROUP_NAME_TO_LAYER

        try:
            stmt = select(Tag).where(Tag.name == tag)
            existing = self.db.execute(stmt).scalar_one_or_none()

            default_layer = GROUP_NAME_TO_LAYER.get(result["group"] or "", 1)

            if existing:
                existing.group_name = result["group"]
                existing.default_layer = default_layer
                existing.classification_source = result["source"]
                existing.classification_confidence = result["confidence"]
            else:
                category = self._group_to_category(result["group"])
                new_tag = Tag(
                    name=tag,
                    category=category,
                    group_name=result["group"],
                    default_layer=default_layer,
                    classification_source=result["source"],
                    classification_confidence=result["confidence"],
                )
                self.db.add(new_tag)

            if not defer_commit:
                self.db.commit()
            logger.info("✅ [TagClassifier] Saved: %s → %s", tag, result["group"])
        except Exception as e:
            logger.error("❌ [TagClassifier] Failed to save %s: %s", tag, e)
            self.db.rollback()

    def _group_to_category(self, group: str | None) -> str:
        return group_to_category(group, self.db)


def group_to_category(group: str | None, db: Session) -> str:
    """Map group_name to category by looking up existing tags in DB.

    DB에 같은 group_name을 가진 태그가 있으면 그 category를 따른다.
    없으면 fallback으로 "scene"을 반환한다.
    """
    if not group:
        return "scene"

    existing = db.query(Tag.category).filter(Tag.group_name == group, Tag.category.isnot(None)).limit(1).scalar()
    return existing or "scene"


def classify_tags_background(tags: list[str]) -> None:
    """Background task: Danbooru로 미분류 태그 조회 후 DB 저장.

    BackgroundTasks에서 호출되므로 별도 DB 세션을 생성합니다.
    """
    if not tags:
        return

    from database import get_db

    db = next(get_db())
    try:
        classifier = TagClassifier(db)
        classified = 0
        for tag in tags[:10]:  # Danbooru rate limit 방어
            result = classifier._classify_via_danbooru(tag)
            if result and result["group"]:
                classifier._save_classification(tag, result)
                classified += 1
        if classified:
            logger.info("🔄 [Background] Danbooru classified %d/%d tags", classified, len(tags))
    except Exception as e:
        logger.error("❌ [Background] Danbooru classification failed: %s", e)
    finally:
        db.close()


def classify_tags_background_llm(tags: list[str]) -> None:
    """Background task: Danbooru + LLM으로 미분류 태그 조회 후 DB 저장.

    Danbooru 먼저 시도 후 여전히 미분류인 태그를 LLM으로 분류한다.
    BackgroundTasks에서 호출되므로 별도 DB 세션 + asyncio.run 사용.
    """
    if not tags:
        return

    import asyncio

    from database import get_db

    db = next(get_db())
    try:
        classifier = TagClassifier(db)

        # Step 1: Danbooru 동기 호출 (최대 10개)
        danbooru_classified = 0
        still_unknown = []
        for tag in tags[:10]:
            result = classifier._classify_via_danbooru(tag)
            if result and result["group"]:
                classifier._save_classification(tag, result)
                danbooru_classified += 1
            else:
                still_unknown.append(tag)
        # Danbooru 제한 초과분도 LLM 대상에 추가
        still_unknown.extend(tags[10:])

        # Step 2: LLM 분류 (최대 30개)
        llm_classified = 0
        if still_unknown:
            llm_results = asyncio.run(
                _classify_via_llm_batch(still_unknown[:30])
            )
            for lr in llm_results:
                cr: ClassificationResult = {
                    "group": lr["group_name"],
                    "confidence": lr["confidence"],
                    "source": "llm",
                }
                classifier._save_classification(lr["tag"], cr, defer_commit=True)
                llm_classified += 1
            if llm_classified:
                try:
                    db.commit()
                except Exception as e:
                    logger.error("❌ [Background LLM] Batch commit failed: %s", e)
                    db.rollback()

        total = danbooru_classified + llm_classified
        if total:
            logger.info(
                "🔄 [Background] Classified %d/%d tags (danbooru=%d, llm=%d)",
                total, len(tags), danbooru_classified, llm_classified,
            )
    except Exception as e:
        logger.error("❌ [Background LLM] Classification failed: %s", e)
    finally:
        db.close()


async def _classify_via_llm_batch(tags: list[str]) -> list:
    """LLM 배치 분류 헬퍼 (background에서 asyncio.run으로 호출)."""
    from services.tag_classifier_llm import classify_tags_via_llm

    return await classify_tags_via_llm(tags)


# Utility function to migrate CATEGORY_PATTERNS to classification_rules
def migrate_patterns_to_rules(db: Session, patterns: dict[str, list[str]]) -> int:
    """Migrate hardcoded CATEGORY_PATTERNS to classification_rules table.

    Args:
        db: Database session
        patterns: Dictionary of group_name → list of patterns

    Returns:
        Number of rules created
    """
    from sqlalchemy.dialects.postgresql import insert

    count = 0
    rules_to_insert = []

    for group_name, pattern_list in patterns.items():
        for pattern in pattern_list:
            rules_to_insert.append(
                {
                    "rule_type": "exact",
                    "pattern": pattern.lower(),
                    "target_group": group_name,
                    "priority": 0,
                    "is_active": True,
                }
            )

    if rules_to_insert:
        # Use ON CONFLICT DO NOTHING to skip duplicates
        stmt = insert(ClassificationRule).values(rules_to_insert)
        stmt = stmt.on_conflict_do_nothing(index_elements=["rule_type", "pattern"])
        result = db.execute(stmt)
        count = result.rowcount
        db.commit()

    logger.info("✅ [Migration] Created %d classification rules", count)
    return count
