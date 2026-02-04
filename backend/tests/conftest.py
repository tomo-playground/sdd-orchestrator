"""
VRT (Visual Regression Test) pytest configuration and fixtures.

DB Isolation:
- Tests use SQLite in-memory database (fast, isolated)
- Each test gets a fresh database
- Production PostgreSQL database is never touched
"""

import os
import random
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Paths
TESTS_DIR = Path(__file__).parent
GOLDEN_MASTERS_DIR = TESTS_DIR / "golden_masters"
FIXTURES_DIR = TESTS_DIR / "fixtures"
BACKEND_DIR = TESTS_DIR.parent

# Add backend to path for imports
sys.path.insert(0, str(BACKEND_DIR))

from database import get_db  # noqa: E402
from main import app  # noqa: E402
from models import Base  # noqa: E402

# Test database URL (SQLite in-memory for speed and isolation)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def set_test_mode():
    """Automatically set test mode for all tests."""
    os.environ["VRT_TEST_MODE"] = "1"
    yield
    # Cleanup after test
    if "VRT_TEST_MODE" in os.environ:
        del os.environ["VRT_TEST_MODE"]


@pytest.fixture(autouse=True)
def seed_random():
    """Seed random for deterministic tests."""
    random.seed(42)
    yield


@pytest.fixture
def golden_masters_dir() -> Path:
    """Return the golden masters directory path."""
    return GOLDEN_MASTERS_DIR


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the fixtures directory path."""
    return FIXTURES_DIR


@pytest.fixture
def backend_dir() -> Path:
    """Return the backend directory path."""
    return BACKEND_DIR


@pytest.fixture
def update_golden_mode() -> bool:
    """Check if we're in golden master update mode."""
    return os.environ.get("VRT_UPDATE_GOLDEN", "").lower() in ("1", "true", "yes")


@pytest.fixture
def ssim_threshold() -> float:
    """SSIM threshold for image comparison (0.95 = 95% similarity)."""
    return float(os.environ.get("VRT_SSIM_THRESHOLD", "0.95"))


@pytest.fixture
def fixed_seed() -> int:
    """Return the fixed seed for deterministic tests."""
    from constants.testing import VRTConfig
    return VRTConfig.FIXED_SEED


@pytest.fixture
def test_random() -> random.Random:
    """Return a seeded Random instance for tests."""
    from constants.testing import create_seeded_random
    return create_seeded_random()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh test database for each test.

    Uses SQLite in-memory for:
    - Speed: No disk I/O
    - Isolation: Each test gets a clean database
    - Safety: Production PostgreSQL is never touched

    Database is automatically destroyed after each test.
    """
    # Create engine with SQLite in-memory (StaticPool ensures single shared connection)
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Map PostgreSQL-specific types → SQLite-compatible equivalents
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    for table in Base.metadata.tables.values():
        for col in table.columns:
            type_name = type(col.type).__name__
            if type_name == "JSONB":
                col.type = JSON()
            elif type_name == "ARRAY":
                col.type = JSON()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    session = TestingSessionLocal()

    yield session

    # Cleanup
    session.close()
    # Tables automatically destroyed when in-memory DB closes


@pytest.fixture
def client(db_session) -> TestClient:
    """Return a FastAPI TestClient with test database.

    Overrides the app's database dependency to use test DB.
    Production database is never touched during tests.
    """
    # Override database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Session cleanup handled by db_session fixture

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def seed_default_project_group(db_session):
    """Seed default Project (id=1), Group (id=1), GroupConfig, and StyleProfile (id=1) for every test.

    Storyboard.group_id is NOT NULL with a default fallback of 1,
    so every test DB needs these rows to exist.
    StyleProfile is set via GroupConfig (cascade).
    """
    from models.group import Group
    from models.group_config import GroupConfig
    from models.project import Project
    from models.sd_model import StyleProfile

    profile = StyleProfile(name="__test_infra__", is_default=False, is_active=False)
    db_session.add(profile)
    db_session.flush()

    project = Project(name="Default Project", style_profile_id=profile.id)
    db_session.add(project)
    db_session.flush()

    group = Group(project_id=project.id, name="Default Series")
    db_session.add(group)
    db_session.flush()

    config = GroupConfig(group_id=group.id, style_profile_id=profile.id)
    db_session.add(config)
    db_session.commit()

    yield

    # Cleanup handled by in-memory DB teardown


@pytest.fixture
def test_project(db_session):
    """Return the default test project (id=1)."""
    from models.project import Project
    return db_session.query(Project).first()


@pytest.fixture
def test_group(db_session):
    """Return the default test group (id=1)."""
    from models.group import Group
    return db_session.query(Group).first()


@pytest.fixture(autouse=True)
def init_tag_caches():
    """Initialize tag caches with mock data for all tests.

    Production caches are loaded from DB at startup; tests need mock data
    so that cache-dependent logic (skip tags, conflicts, aliases) works.
    """
    from services.keywords.core import TagFilterCache
    from services.keywords.db_cache import TagAliasCache, TagCategoryCache, TagRuleCache
    from services.prompt.prompt import get_token_category

    # --- TagFilterCache: skip tags ---
    TagFilterCache._initialized = True
    TagFilterCache._skip_tags = frozenset({
        "breasts", "medium_breasts", "large_breasts", "small_breasts", "huge_breasts",
        "child", "male_child", "female_child", "loli", "shota",
    })

    # --- TagRuleCache: conflict rules ---
    TagRuleCache._initialized = True
    TagRuleCache._conflicts = {
        # hair_length conflicts
        "short_hair": {"long_hair", "medium_hair", "very_long_hair"},
        "long_hair": {"short_hair", "medium_hair", "very_long_hair"},
        "medium_hair": {"short_hair", "long_hair", "very_long_hair"},
        "very_long_hair": {"short_hair", "long_hair", "medium_hair"},
        # camera shot conflicts (mutual exclusion among all camera tokens)
        "full_body": {"medium_shot", "close-up", "upper_body", "cowboy_shot", "portrait", "wide_shot", "from_above", "from_below", "side_view"},
        "upper_body": {"full_body", "cowboy_shot", "close-up", "portrait", "wide_shot", "from_above", "from_below", "side_view"},
        "cowboy_shot": {"full_body", "upper_body", "close-up", "portrait", "wide_shot", "from_above", "from_below", "side_view"},
        "close-up": {"full_body", "upper_body", "cowboy_shot", "portrait", "wide_shot", "from_above", "from_below", "side_view"},
        "portrait": {"full_body", "upper_body", "cowboy_shot", "close-up", "wide_shot", "from_above", "from_below", "side_view"},
        "wide_shot": {"full_body", "upper_body", "cowboy_shot", "close-up", "portrait", "from_above", "from_below", "side_view"},
        "medium_shot": {"full_body", "upper_body", "cowboy_shot", "close-up", "portrait", "wide_shot", "from_above", "from_below", "side_view"},
        # camera angle conflicts
        "from_above": {"from_below", "side_view", "full_body", "upper_body", "cowboy_shot", "close-up", "portrait", "wide_shot"},
        "from_below": {"from_above", "side_view", "full_body", "upper_body", "cowboy_shot", "close-up", "portrait", "wide_shot"},
        "side_view": {"from_above", "from_below", "full_body", "upper_body", "cowboy_shot", "close-up", "portrait", "wide_shot"},
        # expression conflicts (opposing emotions conflict)
        "smile": {"angry", "crying", "sad", "frown"},
        "angry": {"smile", "happy", "laughing", "crying", "sad"},
        "crying": {"smile", "happy", "laughing", "angry", "sad", "grin"},
        "laughing": {"crying", "sad", "angry", "frown"},
        "sad": {"smile", "happy", "laughing", "angry", "crying"},
        "frown": {"smile", "laughing", "happy"},
        "happy": {"sad", "angry", "crying", "frown"},
        # gaze conflicts (all gaze directions mutually exclusive)
        "looking_at_viewer": {"looking_away", "looking_down", "looking_up", "looking_back", "looking_to_the_side", "eyes_closed", "closed_eyes"},
        "looking_away": {"looking_at_viewer", "looking_down", "looking_up", "looking_back", "looking_to_the_side"},
        "looking_down": {"looking_at_viewer", "looking_away", "looking_up", "looking_back", "looking_to_the_side"},
        "looking_up": {"looking_at_viewer", "looking_away", "looking_down", "looking_back", "looking_to_the_side"},
        "looking_back": {"looking_at_viewer", "looking_away", "looking_down", "looking_up", "looking_to_the_side"},
        "looking_to_the_side": {"looking_at_viewer", "looking_away", "looking_down", "looking_up", "looking_back"},
        "eyes_closed": {"looking_at_viewer"},
        "closed_eyes": {"looking_at_viewer"},
        # pose conflicts
        "standing": {"sitting", "lying", "lying_down", "kneeling"},
        "sitting": {"standing", "lying", "lying_down"},
        "lying": {"standing", "sitting"},
        "lying_down": {"standing", "sitting"},
        "kneeling": {"standing"},
    }
    TagRuleCache._category_conflicts = {}

    # --- TagAliasCache: alias replacements ---
    TagAliasCache._initialized = True
    TagAliasCache._cache = {
        "medium_shot": "cowboy_shot",
        "medium shot": "cowboy_shot",
    }

    # --- TagCategoryCache: ensure NOT initialized so pattern matching is used ---
    TagCategoryCache._initialized = False
    TagCategoryCache._cache = {}

    # Clear lru_cache on get_token_category to prevent stale results
    get_token_category.cache_clear()

    yield

    # Teardown
    TagFilterCache._initialized = False
    TagFilterCache._skip_tags = frozenset()
    TagRuleCache._initialized = False
    TagRuleCache._conflicts = {}
    TagRuleCache._category_conflicts = {}
    TagAliasCache._initialized = False
    TagAliasCache._cache = {}
    TagCategoryCache._initialized = False
    TagCategoryCache._cache = {}
    get_token_category.cache_clear()


def create_test_storyboard(
    client,
    title: str | None = None,
    scenes: list | None = None,
) -> dict:
    """Create a test storyboard via API. Returns full response data.

    Usage:
        data = create_test_storyboard(client)
        sb_id = data["storyboard_id"]
    """
    import uuid

    payload = {
        "title": title or f"Test {uuid.uuid4().hex[:4]}",
        "description": "test",
        "group_id": 1,
        "scenes": scenes or [],
    }
    resp = client.post("/storyboards", json=payload)
    assert resp.status_code == 200, f"Storyboard creation failed: {resp.text}"
    return resp.json()

