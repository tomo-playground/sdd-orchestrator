#!/usr/bin/env python3
import os
import re
import argparse
import sys

# Constants
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS_DIR = os.path.join(PROJECT_ROOT, ".claude", "agents")
AGENTS_FILE = os.path.join(PROJECT_ROOT, "AGENTS")
CLAUDE_FILE = os.path.join(PROJECT_ROOT, "CLAUDE.md")


def slugify(text: str) -> str:
    """Convert a string to a valid filename slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')


def create_agent_markdown(name: str, description: str, tools: str):
    """Creates the agent's markdown file in .claude/agents/."""
    slug = slugify(name)
    filepath = os.path.join(AGENTS_DIR, f"{slug}.md")

    if os.path.exists(filepath):
        print(f"⚠️ Agent file {filepath} already exists. Skipping file creation.")
        return filepath

    # Format tools as a JSON list string
    tools_list = [t.strip() for t in tools.split(',') if t.strip()]
    tools_str = str(tools_list).replace("'", '"')

    content = f"""---
name: {slug}
description: {description}
allowed_tools: {tools_str}
---

# {name}

당신은 프로젝트의 {name}입니다.

## 주요 역할
- {description}

## 규칙 및 행동 지침
- 이 에이전트의 구체적인 책임과 사용할 프롬프트를 여기에 정의하세요.
- 프로젝트 전체 가이드는 항상 `CLAUDE.md`를 우선으로 참고하세요.
"""

    os.makedirs(AGENTS_DIR, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Created agent profile: {filepath}")
    return filepath


def append_to_markdown_table(filepath: str, section_header: str, new_row: str):
    """Appends a new row to a markdown table under a specific section."""
    if not os.path.exists(filepath):
        print(f"❌ Cannot find file: {filepath}")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    target_idx = -1
    table_start_idx = -1
    table_end_idx = -1

    # Find the section header if provided, otherwise assume first table
    if section_header:
        for i, line in enumerate(lines):
            if line.strip().startswith(section_header):
                target_idx = i
                break
    else:
        target_idx = 0

    if target_idx == -1 and section_header:
        print(f"❌ Cannot find section '{section_header}' in {filepath}")
        return False

    # Find the table within or after the target section
    for i in range(target_idx, len(lines)):
        if lines[i].strip().startswith('|'):
            if table_start_idx == -1:
                table_start_idx = i
            table_end_idx = i
        elif table_start_idx != -1 and not lines[i].strip():
            # Empty line after table indicates end of table
            break

    if table_start_idx == -1:
        print(f"❌ Cannot find a markdown table in {filepath}")
        return False

    # Insert the new row at the end of the table
    # Check if the exact row already exists to avoid duplicates
    if any(new_row.strip() in l.strip() for l in lines[table_start_idx:table_end_idx + 1]):
         print(f"ℹ️ Agent already exists in table in {filepath}")
         return True
    
    lines.insert(table_end_idx + 1, new_row + "\n")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"✅ Updated table in: {filepath}")
    return True


def register_agent(name: str, description: str, commands: str):
    """Registers the agent in AGENTS and CLAUDE.md files."""
    # Build the row
    row = f"| **{name}** | {description} | {commands} |"

    # Update AGENTS (assuming there's only one main table, or it's under "Active Agents")
    append_to_markdown_table(AGENTS_FILE, "# Active Agents", row)

    # Update CLAUDE.md under "## Sub Agents"
    append_to_markdown_table(CLAUDE_FILE, "## Sub Agents", row)


def main():
    parser = argparse.ArgumentParser(description="Create and register a new Agent in the Shorts Producer project.")
    
    # Optional arguments, but if not provided, we will prompt interactively
    parser.add_argument("--name", help="Agent Name (e.g., Security Engineer)")
    parser.add_argument("--desc", help="Agent Description / Role (e.g., 보안 취약점 분석)")
    parser.add_argument("--commands", help="Agent Commands (e.g., `/review, /test`)", default="")
    parser.add_argument("--tools", help="Allowed Tools (e.g., `mcp__postgres__*, mcp__memory__*`)", default="")

    args = parser.parse_args()

    print("🚀 Shorts Producer Agent Creator 🚀")
    print("-" * 40)

    # Check if run non-interactively without parameters
    if not sys.stdin.isatty() and not args.name:
         print("❌ Error: Missing required arguments. Please provide --name and --desc or run interactively.")
         sys.exit(1)

    # Interactive prompts if arguments are missing
    name = args.name
    if not name:
        name = input("1. 에이전트 이름 (Agent Name) [예: SEO Expert]: ").strip()
    if not name:
        print("❌ 에이전트 이름은 필수입니다.")
        sys.exit(1)

    desc = args.desc
    if not desc:
        desc = input(f"2. '{name}'의 역할 (Role Description) [예: 웹사이트 SEO 분석 및 가이드 작성]: ").strip()
    if not desc:
        print("❌ 역할 설명은 필수입니다.")
        sys.exit(1)

    commands = args.commands
    if not commands and not args.name: # Only prompt if we are fully interactive
        try:
             commands = input("3. 사용할 명령어 목록 (Commands) [예: `/docs, /review`]: ").strip()
        except EOFError:
             commands = ""
    
    # Format commands to have backticks if they don't already
    formatted_commands = []
    if commands:
        for cmd in commands.split(','):
            cmd = cmd.strip()
            if cmd:
                if not cmd.startswith('`'):
                    cmd = f"`{cmd}`"
                formatted_commands.append(cmd)
    final_commands = ", ".join(formatted_commands) if formatted_commands else "None"


    tools = args.tools
    if not tools and not args.name:
        try:
           tools = input("4. 허용할 Tools (Allowed Tools) (쉼표로 구분) [예: mcp__memory__*, mcp__postgres__*]: ").strip()
        except EOFError:
           tools = ""

    print("-" * 40)
    print("⏳ 생성 중...")

    # 1. Create .md file
    create_agent_markdown(name, desc, tools)

    # 2. Register in tables
    register_agent(name, desc, final_commands)

    print("-" * 40)
    print("🎉 에이전트 생성이 완료되었습니다!")
    print("👉 다음 단계:")
    print(f"   `.claude/agents/{slugify(name)}.md` 파일을 열어 상세 프롬프트를 작성하세요.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 사용자에 의해 취소되었습니다.")
        sys.exit(1)
