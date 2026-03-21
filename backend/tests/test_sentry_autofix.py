"""Sentry Autofix 파이프라인 검증 테스트.

sentry-autofix.yml 워크플로우의 구조와 설정을 검증한다.
실제 GitHub API 호출은 E2E 수동 테스트로 검증.
"""

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/sentry-autofix.yml"
PATROL_PATH = REPO_ROOT / "scripts/sentry-patrol.sh"


@pytest.fixture
def workflow():
    """YAML safe_load는 'on'을 True로 파싱하므로 raw 로더 사용."""
    with open(WORKFLOW_PATH) as f:
        # yaml.safe_load treats 'on' as True (boolean), use BaseLoader to preserve keys
        return yaml.load(f, Loader=yaml.BaseLoader)  # noqa: S506


class TestSentryAutofixWorkflow:
    """sentry-autofix.yml 워크플로우 구조 검증."""

    def test_workflow_file_exists(self):
        assert WORKFLOW_PATH.exists(), "sentry-autofix.yml이 존재해야 함"

    def test_issues_trigger(self, workflow):
        """issues labeled 이벤트로 트리거되는지."""
        assert "issues" in workflow["on"]

    def test_issues_labeled_type(self, workflow):
        """labeled 타입만 트리거하는지."""
        assert "labeled" in workflow["on"]["issues"]["types"]

    def test_workflow_dispatch_trigger(self, workflow):
        """수동 실행(workflow_dispatch)도 지원하는지."""
        assert "workflow_dispatch" in workflow["on"]

    def test_sentry_label_condition(self, workflow):
        """sentry 라벨이 붙은 이슈만 처리하는지."""
        job = workflow["jobs"]["autofix"]
        assert "sentry" in job["if"]

    def test_runs_on_self_hosted(self, workflow):
        """self-hosted sdd 러너에서 실행되는지."""
        runs_on = workflow["jobs"]["autofix"]["runs-on"]
        assert "self-hosted" in runs_on
        assert "sdd" in runs_on

    def test_timeout(self, workflow):
        """30분 타임아웃 설정."""
        assert int(workflow["jobs"]["autofix"]["timeout-minutes"]) == 30

    def test_concurrency_group(self, workflow):
        """이슈별 동시성 그룹 설정."""
        concurrency = workflow["concurrency"]
        assert "sentry-autofix" in concurrency["group"]
        assert concurrency["cancel-in-progress"] == "false"

    def test_permissions(self, workflow):
        """필요 권한이 모두 설정되어 있는지."""
        perms = workflow["permissions"]
        assert perms["contents"] == "write"
        assert perms["pull-requests"] == "write"
        assert perms["issues"] == "write"

    def test_claude_code_action_used(self, workflow):
        """claude-code-action이 사용되는지."""
        steps = workflow["jobs"]["autofix"]["steps"]
        claude_steps = [s for s in steps if "anthropics/claude-code-action" in str(s.get("uses", ""))]
        assert len(claude_steps) == 1

    def test_prompt_includes_tdd(self, workflow):
        """프롬프트에 TDD(실패 테스트 먼저) 지시가 포함되는지."""
        steps = workflow["jobs"]["autofix"]["steps"]
        claude_step = next(s for s in steps if "anthropics/claude-code-action" in str(s.get("uses", "")))
        prompt = claude_step["with"]["prompt"]
        assert "테스트" in prompt

    def test_prompt_includes_fixes_ref(self, workflow):
        """프롬프트에 Fixes # 이슈 링크 지시가 포함되는지."""
        steps = workflow["jobs"]["autofix"]["steps"]
        claude_step = next(s for s in steps if "anthropics/claude-code-action" in str(s.get("uses", "")))
        prompt = claude_step["with"]["prompt"]
        assert "Fixes #" in prompt

    def test_prompt_includes_manual_fix_fallback(self, workflow):
        """수정 불가 시 needs-manual-fix 라벨 지시가 포함되는지."""
        steps = workflow["jobs"]["autofix"]["steps"]
        claude_step = next(s for s in steps if "anthropics/claude-code-action" in str(s.get("uses", "")))
        prompt = claude_step["with"]["prompt"]
        assert "needs-manual-fix" in prompt

    def test_branch_naming(self, workflow):
        """fix/sentry- 브랜치 네이밍 지시가 포함되는지."""
        steps = workflow["jobs"]["autofix"]["steps"]
        claude_step = next(s for s in steps if "anthropics/claude-code-action" in str(s.get("uses", "")))
        prompt = claude_step["with"]["prompt"]
        assert "fix/sentry-" in prompt


class TestSentryPatrolIntegration:
    """sentry-patrol.sh가 autofix 트리거에 맞는 라벨을 생성하는지."""

    def test_patrol_adds_sentry_label(self):
        """sentry-patrol.sh가 'sentry' 라벨을 추가하는지."""
        content = PATROL_PATH.read_text()
        assert '--label "$GITHUB_LABEL"' in content or "--label sentry" in content.lower()

    def test_patrol_adds_bug_label(self):
        """sentry-patrol.sh가 'bug' 라벨도 추가하는지."""
        content = PATROL_PATH.read_text()
        assert '--label "bug"' in content

    def test_patrol_github_label_is_sentry(self):
        """GITHUB_LABEL 변수가 'sentry'인지."""
        content = PATROL_PATH.read_text()
        assert 'GITHUB_LABEL="sentry"' in content
