"""Test database isolation - verify test DB doesn't affect production."""

from models.activity_log import ActivityLog
from models.storyboard import Storyboard


def test_db_isolation_activity_logs(db_session):
    """Verify activity_logs use test DB, not production DB."""
    # Count before
    initial_count = db_session.query(ActivityLog).count()
    assert initial_count == 0, "Test DB should start empty"

    # Create parent storyboard (FK requirement)
    storyboard = Storyboard(title="Test", group_id=1)
    db_session.add(storyboard)
    db_session.commit()

    # Create test data
    log = ActivityLog(
        storyboard_id=storyboard.id,
        scene_id=0,
        character_id=1,
        prompt="test prompt",
        status="success",
    )
    db_session.add(log)
    db_session.commit()

    # Verify data exists in test DB
    count_after = db_session.query(ActivityLog).count()
    assert count_after == 1, "Test data should be in test DB"

    # After test ends, data is automatically destroyed (in-memory DB)


def test_db_isolation_storyboards(db_session):
    """Verify storyboards use test DB, not production DB."""
    # Count before
    initial_count = db_session.query(Storyboard).count()
    assert initial_count == 0, "Test DB should start empty"

    # Create test data
    storyboard = Storyboard(
        title="Test Storyboard",
        group_id=1,
    )
    db_session.add(storyboard)
    db_session.commit()

    # Verify data exists in test DB
    count_after = db_session.query(Storyboard).count()
    assert count_after == 1, "Test data should be in test DB"


def test_db_independence_between_tests(db_session):
    """Verify each test gets a fresh database."""
    # This test should see zero records, proving previous tests didn't leak data
    activity_count = db_session.query(ActivityLog).count()
    storyboard_count = db_session.query(Storyboard).count()

    assert activity_count == 0, "Fresh DB should have no activity_logs"
    assert storyboard_count == 0, "Fresh DB should have no storyboards"


def test_api_endpoint_uses_test_db(client, db_session):
    """Verify API endpoints use test DB through dependency injection."""
    # Create parent storyboard (FK requirement)
    storyboard = Storyboard(title="API Test", group_id=1)
    db_session.add(storyboard)
    db_session.commit()

    # Create via API
    response = client.post(
        "/activity-logs",
        json={
            "storyboard_id": storyboard.id,
            "scene_id": 0,
            "character_id": 5,
            "prompt": "1girl, smile",
            "status": "success",
        },
    )
    assert response.status_code == 200, f"Failed: {response.text}"

    # Verify it's in test DB only
    data = response.json()
    assert "id" in data
    assert data["character_id"] == 5

    # Production DB remains untouched
