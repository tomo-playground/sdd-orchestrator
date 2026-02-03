#!/bin/bash
# Auto-lint hook: PostToolUse (Edit/Write)
# Runs ruff on Python files, prettier on TS/TSX files

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
INPUT=$(cat)

# Extract file_path from tool input
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Skip non-existent files (e.g. deleted)
if [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

# Python files → ruff
if [[ "$FILE_PATH" == *.py ]]; then
  cd "$PROJECT_DIR/backend"
  uv run ruff check --fix --quiet "$FILE_PATH" 2>/dev/null || true
  uv run ruff format --quiet "$FILE_PATH" 2>/dev/null || true
  exit 0
fi

# TypeScript/JavaScript files → prettier
if [[ "$FILE_PATH" == *.ts || "$FILE_PATH" == *.tsx || "$FILE_PATH" == *.js || "$FILE_PATH" == *.jsx ]]; then
  cd "$PROJECT_DIR/frontend"
  npx prettier --write --log-level silent "$FILE_PATH" 2>/dev/null || true
  exit 0
fi

exit 0
