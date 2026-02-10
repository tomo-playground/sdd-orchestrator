"""Tests for automatic tag_effectiveness updates from WD14 validation.

Validates that _increment_tag_effectiveness correctly:
- Creates new TagEffectiveness records
- Increments counters (use_count, match_count)
- Calculates effectiveness ratio
- Skips WD14_UNMATCHABLE_TAGS
- Skips tags not in DB
"""

import pytest

from models.tag import Tag, TagEffectiveness
from services.validation import _increment_tag_effectiveness


@pytest.fixture
def sample_tags(db_session):
    """Create sample tags for testing."""
    tags = []
    for name in ["smile", "brown_hair", "school_uniform", "cowboy_shot", "looking_at_viewer"]:
        tag = Tag(name=name, category="test", default_layer=0)
        db_session.add(tag)
        tags.append(tag)
    db_session.commit()
    return {t.name: t for t in tags}


def test_increment_creates_new_records(db_session, sample_tags):
    """New TagEffectiveness records are created for tags without existing records."""
    _increment_tag_effectiveness(
        db=db_session,
        matched_tags=["smile", "brown_hair"],
        missing_tags=[],
    )

    eff = db_session.query(TagEffectiveness).filter(TagEffectiveness.tag_id == sample_tags["smile"].id).first()
    assert eff is not None
    assert eff.use_count == 1
    assert eff.match_count == 1
    assert eff.effectiveness == 1.0


def test_increment_updates_existing_records(db_session, sample_tags):
    """Existing TagEffectiveness records have counters incremented."""
    existing = TagEffectiveness(tag_id=sample_tags["smile"].id, use_count=5, match_count=3, effectiveness=0.6)
    db_session.add(existing)
    db_session.commit()

    _increment_tag_effectiveness(
        db=db_session,
        matched_tags=["smile"],
        missing_tags=[],
    )

    db_session.refresh(existing)
    assert existing.use_count == 6
    assert existing.match_count == 4
    assert abs(existing.effectiveness - 4 / 6) < 0.001


def test_increment_matched_vs_missing(db_session, sample_tags):
    """Matched tags get match_count++, missing tags get only use_count++."""
    _increment_tag_effectiveness(
        db=db_session,
        matched_tags=["smile"],
        missing_tags=["brown_hair"],
    )

    eff_matched = db_session.query(TagEffectiveness).filter(TagEffectiveness.tag_id == sample_tags["smile"].id).first()
    assert eff_matched.use_count == 1
    assert eff_matched.match_count == 1
    assert eff_matched.effectiveness == 1.0

    eff_missing = (
        db_session.query(TagEffectiveness).filter(TagEffectiveness.tag_id == sample_tags["brown_hair"].id).first()
    )
    assert eff_missing.use_count == 1
    assert eff_missing.match_count == 0
    assert eff_missing.effectiveness == 0.0


def test_increment_skips_unmatchable_tags(db_session, sample_tags):
    """Tags in WD14_UNMATCHABLE_TAGS are not tracked."""
    # "masterpiece" is in WD14_UNMATCHABLE_TAGS
    masterpiece = Tag(name="masterpiece", category="quality", default_layer=0)
    db_session.add(masterpiece)
    db_session.commit()

    _increment_tag_effectiveness(
        db=db_session,
        matched_tags=["masterpiece", "smile"],
        missing_tags=[],
    )

    eff_master = db_session.query(TagEffectiveness).filter(TagEffectiveness.tag_id == masterpiece.id).first()
    assert eff_master is None  # Skipped

    eff_smile = db_session.query(TagEffectiveness).filter(TagEffectiveness.tag_id == sample_tags["smile"].id).first()
    assert eff_smile is not None  # Not skipped


def test_increment_skips_unknown_tags(db_session, sample_tags):
    """Tags not found in the DB are silently skipped."""
    _increment_tag_effectiveness(
        db=db_session,
        matched_tags=["nonexistent_tag_xyz"],
        missing_tags=["another_unknown"],
    )

    count = db_session.query(TagEffectiveness).count()
    assert count == 0


def test_increment_effectiveness_calculation(db_session, sample_tags):
    """effectiveness = match_count / use_count after multiple increments."""
    # 3 uses, 2 matches → effectiveness = 2/3
    _increment_tag_effectiveness(db=db_session, matched_tags=["smile"], missing_tags=[])
    _increment_tag_effectiveness(db=db_session, matched_tags=["smile"], missing_tags=[])
    _increment_tag_effectiveness(db=db_session, matched_tags=[], missing_tags=["smile"])

    eff = db_session.query(TagEffectiveness).filter(TagEffectiveness.tag_id == sample_tags["smile"].id).first()
    assert eff.use_count == 3
    assert eff.match_count == 2
    assert abs(eff.effectiveness - 2 / 3) < 0.001


def test_increment_empty_tags(db_session, sample_tags):
    """No error when both matched and missing are empty."""
    _increment_tag_effectiveness(db=db_session, matched_tags=[], missing_tags=[])
    count = db_session.query(TagEffectiveness).count()
    assert count == 0
