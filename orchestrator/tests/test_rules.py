"""Unit tests for orchestrator decision rules."""

from __future__ import annotations

from orchestrator.rules import can_auto_approve, can_auto_merge

# ── Tests: can_auto_merge (SP-067) ────────────────────────


class TestCanAutoMerge:
    def test_all_pass(self):
        pr = {"ci_status": "success", "review": "APPROVED"}
        ok, reason = can_auto_merge(pr)
        assert ok is True
        assert "passed" in reason.lower()

    def test_ci_failure(self):
        pr = {"ci_status": "failure", "review": "APPROVED"}
        ok, reason = can_auto_merge(pr)
        assert ok is False
        assert "CI" in reason

    def test_ci_pending(self):
        pr = {"ci_status": "pending", "review": "APPROVED"}
        ok, reason = can_auto_merge(pr)
        assert ok is False
        assert "CI" in reason

    def test_no_review(self):
        pr = {"ci_status": "success", "review": None}
        ok, reason = can_auto_merge(pr)
        assert ok is False
        assert "review" in reason.lower()

    def test_changes_requested(self):
        pr = {"ci_status": "success", "review": "CHANGES_REQUESTED"}
        ok, reason = can_auto_merge(pr)
        assert ok is False
        assert "Changes requested" in reason

    def test_review_pending(self):
        pr = {"ci_status": "success", "review": "REVIEW_REQUIRED"}
        ok, reason = can_auto_merge(pr)
        assert ok is False

    def test_empty_dict(self):
        ok, reason = can_auto_merge({})
        assert ok is False


# ── Fixtures: can_auto_approve (SP-068) ───────────────────

SIMPLE_DESIGN = """\
# SP-099 상세 설계

## 변경 파일 요약

| 파일 | 변경 | 신규 |
|------|------|------|
| `orchestrator/config.py` | 상수 추가 | |
| `orchestrator/agents.py` | 함수 추가 | |
| `orchestrator/tools/foo.py` | | 신규 |

---

## DoD별 구현 방법
Some design content here.
"""

BLOCKER_DESIGN = """\
# SP-100 상세 설계

## 변경 파일 요약

| 파일 | 변경 | 신규 |
|------|------|------|
| `orchestrator/config.py` | 상수 추가 | |

**BLOCKER**: DB 스키마 변경이 필요하여 사람 승인 필수.
"""

DB_CHANGE_DESIGN = """\
# SP-101 상세 설계

## 변경 파일 요약

| 파일 | 변경 | 신규 |
|------|------|------|
| `backend/models/storyboard.py` | 컬럼 추가 | |
| `backend/alembic/versions/001.py` | | 신규 |
| `orchestrator/config.py` | 상수 추가 | |
"""

MANY_FILES_DESIGN = """\
# SP-102 상세 설계

## 변경 파일 요약

| 파일 | 변경 | 신규 |
|------|------|------|
| `orchestrator/config.py` | 변경 | |
| `orchestrator/agents.py` | 변경 | |
| `orchestrator/rules.py` | 변경 | |
| `orchestrator/tools/a.py` | | 신규 |
| `orchestrator/tools/b.py` | | 신규 |
| `orchestrator/tools/c.py` | | 신규 |
| `orchestrator/tools/d.py` | | 신규 |
"""

DEP_CHANGE_DESIGN = """\
# SP-103 상세 설계

## 변경 파일 요약

| 파일 | 변경 | 신규 |
|------|------|------|
| `orchestrator/config.py` | 상수 추가 | |
| `pyproject.toml` | 의존성 추가 | |
"""

NO_TABLE_DESIGN = """\
# SP-104 상세 설계

Some design with no proper table.
"""


# ── Tests: can_auto_approve (SP-068) ──────────────────────


class TestCanAutoApprove:
    def test_simple_task_approved(self):
        approved, reason = can_auto_approve(SIMPLE_DESIGN)
        assert approved is True
        assert "3 files" in reason

    def test_reject_blocker(self):
        approved, reason = can_auto_approve(BLOCKER_DESIGN)
        assert approved is False
        assert "BLOCKER" in reason

    def test_reject_db_change(self):
        approved, reason = can_auto_approve(DB_CHANGE_DESIGN)
        assert approved is False
        assert "DB schema" in reason

    def test_reject_too_many_files(self):
        approved, reason = can_auto_approve(MANY_FILES_DESIGN)
        assert approved is False
        assert "too many files" in reason
        assert "7" in reason

    def test_reject_new_dependency(self):
        approved, reason = can_auto_approve(DEP_CHANGE_DESIGN)
        assert approved is False
        assert "dependency" in reason

    def test_reject_no_table(self):
        approved, reason = can_auto_approve(NO_TABLE_DESIGN)
        assert approved is False
        assert "cannot parse" in reason

    def test_exact_threshold_passes(self):
        """6 files should pass (MAX_AUTO_APPROVE_FILES=6)."""
        design = """\
## 변경 파일 요약

| 파일 | 변경 |
|------|------|
| `a.py` | x |
| `b.py` | x |
| `c.py` | x |
| `d.py` | x |
| `e.py` | x |
| `f.py` | x |
"""
        approved, reason = can_auto_approve(design)
        assert approved is True

    def test_package_lock_rejected(self):
        design = """\
## 변경 파일 요약

| 파일 | 변경 |
|------|------|
| `a.py` | x |
| `package-lock.json` | x |
"""
        approved, reason = can_auto_approve(design)
        assert approved is False
        assert "dependency" in reason
