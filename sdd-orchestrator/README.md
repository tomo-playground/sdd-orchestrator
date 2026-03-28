# SDD Orchestrator

Autonomous AI task execution engine for **Spec-Driven Development (SDD)**.

Humans write specs (DoD), AI handles design → TDD (RED→GREEN) → PR — autonomously.

## Quick Start

```bash
# Install
pip install sdd-orchestrator

# Initialize in your project
cd your-project
sdd init

# Configure
# Edit sdd.config.yaml with your GitHub repo, Sentry, etc.

# Run the orchestrator daemon
sdd-orchestrator
```

## What it does

The SDD Orchestrator runs a continuous cycle:

1. **Scans** your backlog and task specs
2. **Checks** open PRs, CI status, and Sentry errors
3. **Launches** approved tasks as autonomous Claude agents in git worktrees
4. **Merges** PRs that pass all quality gates (CI + review approved)
5. **Monitors** post-merge Sentry errors and auto-reverts on surge
6. **Notifies** via Slack with structured reports

## Architecture

```
sdd-orchestrator/
├── src/sdd_orchestrator/
│   ├── main.py           # Daemon event loop
│   ├── config.py          # Engine-level constants
│   ├── project_config.py  # YAML-driven project settings
│   ├── agents.py          # Claude Agent SDK options
│   ├── state.py           # SQLite state store
│   ├── rules.py           # Auto-merge/approve rules
│   ├── utils.py           # Agent query helper
│   ├── cli/               # `sdd init` command
│   ├── tools/             # MCP tools (11 tools)
│   ├── prompts/           # Agent system prompts
│   └── templates/         # `sdd init` templates
├── tests/                 # 17 test files
└── pyproject.toml
```

## Configuration

Create `sdd.config.yaml` in your project root (or run `sdd init`):

```yaml
project:
  github:
    owner: your-org
    repo: your-repo
    assignee: your-github-username
  sentry:
    org: your-sentry-org
    projects:
      - your-backend
      - your-frontend
  tasks:
    dir: .claude/tasks
    backlog: backlog.md

engine:
  cycle_interval: 180        # seconds between cycles
  max_parallel_runs: 2        # concurrent worktree slots
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SDD_PROJECT_ROOT` | Override project root (default: CWD) |
| `ORCH_AUTO_RUN` | Enable auto-launch of approved tasks (0/1) |
| `ORCH_AUTO_DESIGN` | Enable auto-design of pending tasks (0/1) |
| `SENTRY_AUTH_TOKEN` | Sentry API token for error monitoring |
| `SLACK_BOT_TOKEN` | Slack Bot token for notifications |
| `SLACK_APP_TOKEN` | Slack App token for Socket Mode |

## Task Lifecycle

```
backlog → pending → design → approved → running → done
```

- **pending**: Spec written, no design yet
- **design**: Design written, awaiting human approval
- **approved**: Ready to run — orchestrator launches worktree
- **running**: Implementation in progress
- **done**: Completed and merged

## License

MIT
