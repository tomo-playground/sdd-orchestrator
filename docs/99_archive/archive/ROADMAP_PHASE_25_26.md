# Roadmap Archive: Phase 25~26 P0+P1 + 안정화 작업 (2026-03-01)

## Phase 25: Director 자율 실행 계획
Express/Standard/Creator 프리셋 제거. Director가 토픽 분석 후 `execution_plan`으로 skip_stages 자율 결정. director_plan_lite/human_gate 노드 삭제, VALID_SKIP_STAGES에서 production 제거(항상 실행). recursion_limit 100 고정, context_tags 저장 누락 수정, FFmpeg null→zoompan 수정. 5커밋.

## Phase 26 P0+P1: Script 협업형 UX
P0: director_plan_gate interrupt 노드 추가(19→20노드), interaction_mode 3단계(full_auto/guided/hands_on), PipelineStepCard(노드별 스트리밍 메시지), PlanReviewCard(Director Plan 검토+수정). P1: 생성 후 대화형 씬 수정 — `POST /scripts/edit-scenes`(Gemini 단일 호출), SceneEditDiffCard(LCS 단어 단위 Before/After diff), Accept/Reject, 편집 모드 ChatInput. Backend 4파일 + Frontend 7파일.

---

## 03-01 안정화 및 개선 작업

- **Studio 워크플로우 감사 수정**: str(e) API 노출 전면 제거, SSE polling 폴백, VoicePreset 중앙화, Orphan GC 확장, finalize negative_prompt 직접 주입, 대화형 토픽 분석. 코드 리뷰 2회, 38파일.
- **감사 후속 안정화**: FFmpeg xfade offset 음수 방지, SD 가중치 태그 정규화, Cinematographer JSON 파싱 3단계(call_with_tools→call_direct→fallback), 캐스팅 dismiss 3-layer 버그 수정. 6커밋, 코드 리뷰 2회.
- **Danbooru 태그 품질 근본 수정**: `_apply_tag_aliases()` split 버그 수정(comma target 단일 토큰 버그), Cinematographer 템플릿 복합 포즈→분리 형식 + 금지 태그 확장, tag_aliases 18건 추가(복합 포즈 9, 복합 표현 4, 무효 태그 5), ORM 정합 수정, 테스트 9개. Storyboard 1059 전 씬 데이터 보정 완료.
