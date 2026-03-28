"""Unit tests for project_config.py — ProjectConfig, YAML loading, prompt loading."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from orchestrator.project_config import (
    ProjectConfig,
    _build_config,
    _load_yaml_file,
    get_project_config,
    load_prompt,
)


class TestProjectConfigDefaults:
    """ProjectConfig defaults match the original hard-coded values."""

    def test_default_github(self):
        cfg = ProjectConfig()
        assert cfg.gh_repo_owner == "tomo-playground"
        assert cfg.gh_repo_name == "shorts-producer"
        assert cfg.gh_issue_assignee == "stopper2008"

    def test_default_sentry(self):
        cfg = ProjectConfig()
        assert cfg.sentry_org == "tomo-playground"
        assert "shorts-producer-backend" in cfg.sentry_projects

    def test_default_tasks(self):
        cfg = ProjectConfig()
        assert cfg.tasks_dir == ".claude/tasks"
        assert cfg.backlog_file == "backlog.md"

    def test_derived_properties(self):
        cfg = ProjectConfig()
        assert cfg.gh_repo_url == "https://github.com/tomo-playground/shorts-producer"
        assert cfg.repo_full_name == "tomo-playground/shorts-producer"
        assert cfg.repo_ssh_url == "git@github.com:tomo-playground/shorts-producer.git"

    def test_path_properties(self):
        cfg = ProjectConfig()
        assert cfg.backlog_path.name == "backlog.md"
        assert cfg.tasks_current_dir.name == "current"
        assert cfg.tasks_done_dir.name == "done"


class TestBuildConfig:
    """_build_config parses YAML dict into ProjectConfig."""

    def test_full_yaml(self):
        data = {
            "project": {
                "github": {
                    "owner": "acme",
                    "repo": "my-app",
                    "assignee": "dev01",
                },
                "sentry": {
                    "org": "acme-org",
                    "projects": ["app-backend", "app-frontend"],
                },
                "tasks": {
                    "dir": ".sdd/tasks",
                    "backlog": "queue.md",
                },
            }
        }
        cfg = _build_config(data)
        assert cfg.gh_repo_owner == "acme"
        assert cfg.gh_repo_name == "my-app"
        assert cfg.gh_issue_assignee == "dev01"
        assert cfg.sentry_org == "acme-org"
        assert cfg.sentry_projects == ("app-backend", "app-frontend")
        assert cfg.tasks_dir == ".sdd/tasks"
        assert cfg.backlog_file == "queue.md"

    def test_partial_yaml_uses_defaults(self):
        data = {"project": {"github": {"owner": "custom-owner"}}}
        cfg = _build_config(data)
        assert cfg.gh_repo_owner == "custom-owner"
        assert cfg.gh_repo_name == "shorts-producer"  # default

    def test_empty_dict(self):
        cfg = _build_config({})
        assert cfg.gh_repo_owner == "tomo-playground"

    def test_non_dict_sections_use_defaults(self):
        data = {"project": {"github": "not-a-dict", "sentry": ["a", "b"]}}
        cfg = _build_config(data)
        assert cfg.gh_repo_owner == "tomo-playground"
        assert cfg.sentry_org == "tomo-playground"

    def test_env_overrides_yaml(self):
        data = {"project": {"github": {"owner": "yaml-owner"}}}
        with patch.dict(os.environ, {"SDD_GH_OWNER": "env-owner"}):
            cfg = _build_config(data)
        assert cfg.gh_repo_owner == "env-owner"


class TestLoadYamlFile:
    """_load_yaml_file finds and parses sdd.config.yaml."""

    def test_file_found(self, tmp_path):
        yaml_content = {"project": {"github": {"owner": "test"}}}
        yaml_path = tmp_path / "sdd.config.yaml"
        yaml_path.write_text(yaml.dump(yaml_content), encoding="utf-8")

        with patch("orchestrator.project_config._PROJECT_ROOT", tmp_path):
            result = _load_yaml_file()
        assert result["project"]["github"]["owner"] == "test"

    def test_file_not_found(self, tmp_path):
        with patch("orchestrator.project_config._PROJECT_ROOT", tmp_path):
            result = _load_yaml_file()
        assert result == {}

    def test_invalid_yaml(self, tmp_path):
        yaml_path = tmp_path / "sdd.config.yaml"
        yaml_path.write_text(": invalid: yaml: [", encoding="utf-8")

        with patch("orchestrator.project_config._PROJECT_ROOT", tmp_path):
            result = _load_yaml_file()
        assert result == {}

    def test_non_mapping_yaml_returns_empty(self, tmp_path):
        yaml_path = tmp_path / "sdd.config.yaml"
        yaml_path.write_text("- item1\n- item2\n", encoding="utf-8")

        with patch("orchestrator.project_config._PROJECT_ROOT", tmp_path):
            result = _load_yaml_file()
        assert result == {}

    def test_alternative_path(self, tmp_path):
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        yaml_content = {"project": {"github": {"owner": "alt"}}}
        (sdd_dir / "config.yaml").write_text(yaml.dump(yaml_content), encoding="utf-8")

        with patch("orchestrator.project_config._PROJECT_ROOT", tmp_path):
            result = _load_yaml_file()
        assert result["project"]["github"]["owner"] == "alt"


class TestGetProjectConfig:
    """get_project_config returns cached config."""

    def test_returns_project_config(self, tmp_path):
        get_project_config.cache_clear()
        with patch("orchestrator.project_config._PROJECT_ROOT", tmp_path):
            cfg = get_project_config()
        assert isinstance(cfg, ProjectConfig)
        get_project_config.cache_clear()

    def test_caching(self, tmp_path):
        get_project_config.cache_clear()
        with patch("orchestrator.project_config._PROJECT_ROOT", tmp_path):
            cfg1 = get_project_config()
            cfg2 = get_project_config()
        assert cfg1 is cfg2
        get_project_config.cache_clear()


class TestLoadPrompt:
    """load_prompt reads .md files and applies template substitution."""

    def test_loads_and_substitutes(self, tmp_path):
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "test.md").write_text(
            "Project: ${gh_repo_owner}/${gh_repo_name}", encoding="utf-8"
        )

        get_project_config.cache_clear()
        try:
            with (
                patch("orchestrator.project_config._PROMPTS_DIR", prompts_dir),
                patch("orchestrator.project_config._PROJECT_ROOT", tmp_path),
            ):
                result = load_prompt("test")
            assert result == "Project: tomo-playground/shorts-producer"
        finally:
            get_project_config.cache_clear()

    def test_missing_file_returns_empty(self, tmp_path):
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        with patch("orchestrator.project_config._PROMPTS_DIR", prompts_dir):
            result = load_prompt("nonexistent")
        assert result == ""

    def test_unknown_variable_preserved(self, tmp_path):
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "test.md").write_text("${unknown_var}", encoding="utf-8")

        get_project_config.cache_clear()
        try:
            with (
                patch("orchestrator.project_config._PROMPTS_DIR", prompts_dir),
                patch("orchestrator.project_config._PROJECT_ROOT", tmp_path),
            ):
                result = load_prompt("test")
            assert result == "${unknown_var}"
        finally:
            get_project_config.cache_clear()


class TestConfigCompatLayer:
    """config.py __getattr__ compatibility layer works."""

    def test_gh_repo_owner_via_config(self):
        get_project_config.cache_clear()
        from orchestrator import config

        assert config.GH_REPO_OWNER == "tomo-playground"
        get_project_config.cache_clear()

    def test_backlog_path_via_config(self):
        get_project_config.cache_clear()
        from orchestrator import config

        assert isinstance(config.BACKLOG_PATH, Path)
        assert config.BACKLOG_PATH.name == "backlog.md"
        get_project_config.cache_clear()

    def test_sentry_projects_returns_list(self):
        get_project_config.cache_clear()
        from orchestrator import config

        projects = config.SENTRY_PROJECTS
        assert isinstance(projects, list)
        assert "shorts-producer-backend" in projects
        get_project_config.cache_clear()

    def test_prompts_via_config(self):
        get_project_config.cache_clear()
        from orchestrator import config

        prompt = config.LEAD_AGENT_SYSTEM_PROMPT
        assert "SDD Orchestrator Lead Agent" in prompt
        get_project_config.cache_clear()

    def test_unknown_attr_raises(self):
        from orchestrator import config

        with pytest.raises(AttributeError, match="NO_SUCH_ATTR"):
            _ = config.NO_SUCH_ATTR
