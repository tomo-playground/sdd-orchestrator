"""Jinja2 템플릿 → LangFuse Prompt Management 일괄 업로드.

사용법:
    cd backend && python scripts/upload_prompts_to_langfuse.py

동작:
    1. templates/ 디렉토리의 모든 .j2 파일을 읽음
    2. A등급: chat 타입 (system + user 메시지 분리)
    3. B등급: text 타입 (가시성 전용)
    4. LangFuse API로 업로드 (production 라벨)

옵션:
    --dry-run: 업로드 없이 매핑만 출력
    --grade A: A등급만 업로드
    --grade all: 전체 업로드 (기본값)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# backend/ 를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from config_pipelines import (  # noqa: E402
    CREATIVE_LEADER_MODEL,
    DIRECTOR_MODEL,
    REVIEW_MODEL,
)
from services.agent.langfuse_prompt import LANGFUSE_MANAGED_TEMPLATES  # noqa: E402

# 노드별 모델 매핑 (config_pipelines.py SSOT)
NODE_MODEL_MAP: dict[str, str] = {
    "director": DIRECTOR_MODEL,
    "director-plan": DIRECTOR_MODEL,
    "director-checkpoint": DIRECTOR_MODEL,
    "director-evaluate": DIRECTOR_MODEL,
    "review-unified": REVIEW_MODEL,
    "review-evaluate": REVIEW_MODEL,
    "review-reflection": REVIEW_MODEL,
    "narrative-review": REVIEW_MODEL,
    "concept-architect": CREATIVE_LEADER_MODEL,
}
DEFAULT_MODEL = "gemini-2.5-flash"

MANAGED_PATHS: set[str] = set(LANGFUSE_MANAGED_TEMPLATES)

# A등급 프롬프트의 system_instruction (노드 하드코딩에서 추출)
# LangFuse 폴더 기반 이름 사용. 빈 문자열 = LangFuse에 이미 system이 설정됨.
# 이 dict는 upload 시 fallback으로만 사용. 실제 system instruction은 LangFuse SSOT.
SYSTEM_INSTRUCTIONS: dict[str, str] = {
    # pipeline/ — 파이프라인 메인 노드
    "pipeline/director": "",  # LangFuse에서 관리
    "pipeline/director/plan": "",
    "pipeline/director/checkpoint": "",
    "pipeline/director/evaluate": "",
    "pipeline/writer/script": "",
    "pipeline/writer/planning": "",
    "pipeline/cinematographer": "",
    "pipeline/tts-designer": "",
    "pipeline/sound-designer": "",
    "pipeline/review/unified": "",
    "pipeline/review/evaluate": "",
    "pipeline/review/reflection": "",
    "pipeline/review/narrative": "",
    # storyboard/ — 스토리보드 생성
    "storyboard/default": "",
    "storyboard/dialogue": "",
    "storyboard/narrated": "",
    "storyboard/confession": "",
    # tool/ — 보조 도구
    "tool/analyze-topic": "",
    "tool/concept-architect": "",
    "tool/devils-advocate": "",
    "tool/copyright-reviewer": "",
    "tool/material-analyst": "",
    "tool/reference-analyst": "",
    "tool/location-planner": "",
    "tool/scene-expand": "",
    "tool/edit-scenes": "",
    "tool/explain": "",
    "tool/validate-image-tags": "",
}


def to_langfuse_name(template_path: str) -> str:
    """템플릿 경로 → LangFuse 프롬프트 이름 (폴더 기반)."""
    from services.agent.langfuse_prompt import _TEMPLATE_TO_LANGFUSE

    if template_path in _TEMPLATE_TO_LANGFUSE:
        return _TEMPLATE_TO_LANGFUSE[template_path]
    # fallback
    name = template_path
    if name.startswith("creative/"):
        name = name[len("creative/") :]
    name = name.removesuffix(".j2")
    return name.replace("_", "-")


def _build_prompt_payload(lf_name: str, content: str, is_managed: bool) -> tuple[list | str, str]:
    """(prompt_data, type) 튜플을 반환한다.

    A등급: chat 타입 [system, user] / B등급: text 타입.
    """
    if not is_managed:
        return content, "text"

    sys_text = SYSTEM_INSTRUCTIONS.get(lf_name, "")
    messages: list[dict[str, str]] = []
    if sys_text:
        messages.append({"role": "system", "content": sys_text})
    messages.append({"role": "user", "content": content})
    return messages, "chat"


def collect_templates(templates_dir: Path, grade: str) -> list[tuple[str, str, str]]:
    """(relative_path, langfuse_name, content) 리스트를 반환한다."""
    results = []
    for j2_file in sorted(templates_dir.rglob("*.j2")):
        rel = str(j2_file.relative_to(templates_dir))
        if grade == "A" and rel not in MANAGED_PATHS:
            continue
        lf_name = to_langfuse_name(rel)
        content = j2_file.read_text(encoding="utf-8")
        results.append((rel, lf_name, content))
    return results


def upload(dry_run: bool = False, grade: str = "all") -> None:
    """LangFuse에 프롬프트를 업로드한다."""
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    if not templates_dir.exists():
        print(f"[ERROR] templates 디렉토리 없음: {templates_dir}")
        sys.exit(1)

    templates = collect_templates(templates_dir, grade)
    print(f"\n{'=' * 60}")
    print(f"  LangFuse Prompt Upload — {len(templates)}개 템플릿 ({grade}등급)")
    print(f"{'=' * 60}\n")

    for rel, lf_name, content in templates:
        model = NODE_MODEL_MAP.get(lf_name, DEFAULT_MODEL)
        is_a = rel in MANAGED_PATHS
        grade_label = "M" if is_a else "F"
        ptype = "chat" if is_a else "text"
        sys_text = SYSTEM_INSTRUCTIONS.get(lf_name, "")
        sys_info = f" sys={len(sys_text)}자" if sys_text else ""
        lines = content.count("\n") + 1
        print(f"  [{grade_label}:{ptype:4s}] {rel:45s} → {lf_name:30s} ({lines}줄{sys_info}, model={model})")

    if dry_run:
        print(f"\n  [DRY-RUN] 총 {len(templates)}개 — 업로드 건너뜀\n")
        return

    from langfuse import Langfuse

    lf = Langfuse()

    uploaded = 0
    skipped = 0
    errors = 0

    for rel, lf_name, content in templates:
        model = NODE_MODEL_MAP.get(lf_name, DEFAULT_MODEL)
        is_a = rel in MANAGED_PATHS
        prompt_data, prompt_type = _build_prompt_payload(lf_name, content, is_a)
        try:
            lf.create_prompt(
                name=lf_name,
                prompt=prompt_data,
                labels=["production"],
                config={"model": model},
                type=prompt_type,
            )
            uploaded += 1
            print(f"  ✓ {lf_name} ({prompt_type})")
        except Exception as e:
            err_str = str(e)
            if "already exists" in err_str.lower():
                skipped += 1
                print(f"  - {lf_name} (이미 존재)")
            else:
                errors += 1
                print(f"  ✗ {lf_name}: {err_str[:100]}")

    lf.flush()
    print(f"\n  결과: 업로드 {uploaded} / 스킵 {skipped} / 에러 {errors}\n")


def main():
    parser = argparse.ArgumentParser(description="Jinja2 → LangFuse Prompt 업로드")
    parser.add_argument("--dry-run", action="store_true", help="업로드 없이 매핑만 출력")
    parser.add_argument("--grade", choices=["A", "all"], default="all", help="업로드 대상 등급")
    args = parser.parse_args()
    upload(dry_run=args.dry_run, grade=args.grade)


if __name__ == "__main__":
    main()
