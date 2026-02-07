"""Test database isolation - verify test DB doesn't affect production."""

from models.activity_log import ActivityLog
from models.character import Character
from models.scene import Scene
from models.storyboard import Storyboard


def _setup_hierarchy(db_session):
    """Create minimal hierarchy: storyboard→scene+character.

    Project(id=1) and Group(id=1) are already seeded by conftest's
    seed_default_project_group autouse fixture.
    """
    storyboard = Storyboard(title="Test", group_id=1)
    db_session.add(storyboard)
    db_session.flush()
    scene = Scene(storyboard_id=storyboard.id, order=0, script="s0")
    db_session.add(scene)
    character = Character(name="Test Char")
    db_session.add(character)
    db_session.flush()
    return storyboard, scene, character


def test_db_isolation_activity_logs(db_session):
    """Verify activity_logs use test DB, not production DB."""
    initial_count = db_session.query(ActivityLog).count()
    assert initial_count == 0, "Test DB should start empty"

    storyboard, scene, character = _setup_hierarchy(db_session)

    log = ActivityLog(
        storyboard_id=storyboard.id,
        scene_id=scene.id,
        character_id=character.id,
        prompt="test prompt",
        status="success",
    )
    db_session.add(log)
    db_session.commit()

    count_after = db_session.query(ActivityLog).count()
    assert count_after == 1, "Test data should be in test DB"


def test_db_isolation_storyboards(db_session):
    """Verify storyboards use test DB, not production DB."""
    initial_count = db_session.query(Storyboard).count()
    assert initial_count == 0, "Test DB should start empty"

    # Project(id=1) and Group(id=1) already seeded by conftest autouse fixture
    storyboard = Storyboard(title="Test Storyboard", group_id=1)
    db_session.add(storyboard)
    db_session.commit()

    count_after = db_session.query(Storyboard).count()
    assert count_after == 1, "Test data should be in test DB"


def test_db_independence_between_tests(db_session):
    """Verify each test gets a fresh database."""
    activity_count = db_session.query(ActivityLog).count()
    storyboard_count = db_session.query(Storyboard).count()

    assert activity_count == 0, "Fresh DB should have no activity_logs"
    assert storyboard_count == 0, "Fresh DB should have no storyboards"


def test_api_endpoint_uses_test_db(client, db_session):
    """Verify API endpoints use test DB through dependency injection."""
    storyboard, scene, character = _setup_hierarchy(db_session)
    db_session.commit()

    response = client.post(
        "/activity-logs",
        json={
            "storyboard_id": storyboard.id,
            "scene_id": scene.id,
            "character_id": character.id,
            "prompt": "1girl, smile",
            "status": "success",
        },
    )
    assert response.status_code == 200, f"Failed: {response.text}"

    data = response.json()
    assert "id" in data
    assert data["character_id"] == character.id
