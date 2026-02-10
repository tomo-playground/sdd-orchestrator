# Tests

## Database Isolation (Phase 6-4.26)

**✅ Production DB is NEVER touched during tests**

All tests use **SQLite in-memory database** for:
- **Speed**: No disk I/O (10x+ faster than PostgreSQL)
- **Isolation**: Each test gets a fresh, clean database
- **Safety**: Production PostgreSQL database is never affected

### How It Works

```python
# tests/conftest.py provides:

@pytest.fixture
def db_session():
    """Fresh SQLite in-memory DB for each test"""
    # Auto-creates all tables
    # Auto-destroys after test

@pytest.fixture
def client(db_session):
    """API client with test DB injected"""
    # Overrides app's get_db dependency
    # All API calls use test DB
```

### Running Tests

```bash
# 일상 개발 (가장 추천) - watch + 영향받는 테스트만 + 첫 실패 중단
uv run ptw -- --testmon -x -v

# 수동 실행 - 변경 코드에 영향받는 테스트만
uv run pytest --testmon -v

# 마지막 실패 테스트만 재실행
uv run pytest --lf -v

# 병렬 실행 (전체 테스트 빠르게)
uv run pytest -n auto -v

# 커밋 전 전체 실행 (VRT 제외)
uv run pytest --ignore=tests/vrt -v

# 특정 파일/테스트 실행
uv run pytest tests/test_db_isolation.py
uv run pytest tests/test_db_isolation.py::test_db_isolation_activity_logs

# Show print statements
uv run pytest -s
```

#### 플러그인 설명

| 플러그인 | 용도 | 명령어 |
|----------|------|--------|
| `pytest-testmon` | 변경 코드에 영향받는 테스트만 자동 선택 | `--testmon` |
| `pytest-watch` | 파일 변경 시 자동 재실행 (watch 모드) | `uv run ptw` |
| `pytest-xdist` | 병렬 실행 (CPU 코어 활용) | `-n auto` |

> **참고**: `--testmon` 첫 실행 시 `.testmondata` 파일 생성 (전체 테스트 실행). 이후부터 변경분만 실행.

### Writing Tests

```python
def test_my_feature(db_session):
    """Test using direct DB access."""
    # Create test data
    log = ActivityLog(storyboard_id=1, scene_id=0, ...)
    db_session.add(log)
    db_session.commit()

    # Test your logic
    result = db_session.query(ActivityLog).first()
    assert result.storyboard_id == 1

def test_my_api(client):
    """Test using API client."""
    # API calls automatically use test DB
    response = client.post("/activity-logs", json={...})
    assert response.status_code == 201
```

### Before (Phase 6-4.25)
- ❌ Tests wrote to production PostgreSQL
- ❌ Left 334 rows of garbage data
- ❌ Manual cleanup required after each test run

### After (Phase 6-4.26)
- ✅ Tests use isolated in-memory SQLite
- ✅ Zero garbage data in production
- ✅ Automatic cleanup after each test
- ✅ 10x faster test execution

## Test Types

### DB Isolation Tests
`test_db_isolation.py` - Verify test DB isolation works correctly

### VRT (Visual Regression Tests)
- `test_motion.py` - Motion effect validation
- `test_bgm.py` - BGM audio validation
- `test_prompt_*.py` - Prompt engine tests

### API Tests
- Use `client` fixture for endpoint testing
- All DB operations automatically isolated

## Troubleshooting

### "ModuleNotFoundError: No module named 'sqlalchemy'"
Ensure you're using the correct Python environment:
```bash
# Activate virtual environment (if using)
source venv/bin/activate

# Or use pyenv
pyenv shell 3.11.8

# Verify
python -c "import sqlalchemy; print('OK')"
```

### "Database is locked"
SQLite in-memory DB should never lock. If this happens:
1. Check if `TEST_DATABASE_URL` was changed to file-based SQLite
2. Verify `check_same_thread=False` in conftest.py

### Tests still writing to production DB
Check that:
1. `conftest.py` is loaded (should be automatic in `tests/` directory)
2. Test uses `db_session` or `client` fixture
3. No direct `SessionLocal()` calls in test code (use fixtures instead)
