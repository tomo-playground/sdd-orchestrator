# 에이전트 생성 가이드 (How to Create an Agent)

> [!TIP]
> **CLI를 사용한 빠른 생성**: 
> 새로운 에이전트를 만들 때는 수동 작업 대신 다음 명령어를 사용하면 파일 생성 및 시스템 등록(`AGENTS`, `CLAUDE.md`)이 자동으로 수행됩니다.
> ```bash
> python scripts/create_agent.py
> ```

이 가이드는 Shorts Producer 프로젝트에서 Gemini(LLM) 기반의 에이전트를 새롭게 정의하고 시스템에 통합하는 방법을 설명합니다. 우리 프로젝트에는 크게 두 가지 유형의 에이전트가 존재합니다.

---

## 1. 에이전트 유형 분류

| 유형 | 위치 | 목적 | 특징 |
|------|------|------|------|
| **Pipeline Agent** | `backend/services/agent/nodes/` | 영상 제작 자동화 | LangGraph 노드로 동작, 특정 작업(Script, Visual 등) 전담 |
| **Coding Agent (Persona)** | `.claude/agents/` | 개발 협업 및 자동화 | 개발 페르소나 정의, 명령(`/command`) 및 도구(MCP) 할당 |

---

## 2. Coding Agent (Persona) 구성 방법
> **Note**: 에이전트의 '성격'과 '전문 영역'(예: Tech Lead, DBA)을 정의할 때 사용합니다.

### 2.1 페르소나 정의 파일 생성
`.claude/agents/` 디렉토리에 에이전트명으로 MD 파일을 생성합니다. (예: `security-expert.md`)

**파일 구조 예시:**
```yaml
---
name: security-expert
description: 보안 취약점 분석 및 보안 코드 리뷰 전담
allowed_tools: ["mcp__postgres__*", "mcp__memory__*"]
---

# Security Expert Agent
당신은 프로젝트의 보안 전문가입니다. ...
```

### 2.2 시스템 등록 (SSOT 업데이트)
다음 파일들에 새로운 에이전트를 등록하여 모든 AI가 인지할 수 있게 합니다.
1. **`CLAUDE.md`**: `## Sub Agents` 섹션에 이름, 역할, 커맨드 추가
2. **`AGENTS`**: 프로젝트 루트의 에이전트 목록 테이블에 추가

---

## 3. Pipeline Agent (Autonomous) 구성 방법
> **Note**: LangGraph 파이프라인의 자동화 단계를 추가할 때 사용합니다.

### 3.1 노드 구현 (`backend/services/agent/nodes/`)
`ScriptState`를 입력받아 상태를 업데이트하는 비동기 함수를 작성합니다.

```python
async def my_agent_node(state: ScriptState) -> dict:
    # 로직 구현 (Gemini 호출 등)
    return {"new_field": "result"}
```

### 3.2 그래프 통합 (`backend/services/agent/script_graph.py`)
`StateGraph`에 노드를 등록하고 엣지(Edge)로 연결합니다.

### 3.3 상태 및 검증 모델 등록
- **`state.py`**: `ScriptState`에 결과 필드 추가
- **`llm_models.py`**: Gemini 응답 검증을 위한 Pydantic 모델 정의

---

## 4. Gemini(Tech Lead)가 에이전트를 만드는 법
제가(Gemini) 새로운 에이전트를 만들거나 역할을 수행할 때는 다음과 같은 원칙을 따릅니다:
1. **페르소나 인지**: `.claude/agents/`의 지침을 읽고 자신의 현재 역할(예: Tech Lead)을 결정합니다.
2. **도구 활용**: 정의된 `allowed_tools`를 사용하여 전문 분야의 작업을 수행합니다.
3. **확장**: 사용자가 새로운 전문가가 필요하다고 하면 위 매뉴얼에 따라 `.claude/agents/`에 새로운 지침을 작성하고 시스템에 등록합니다.
