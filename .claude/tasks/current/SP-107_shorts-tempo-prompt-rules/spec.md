---
id: SP-107
priority: P0
scope: backend
branch: feat/SP-107-shorts-tempo-prompt-rules
created: 2026-03-28
status: approved
approved_at: 2026-03-28
depends_on:
label: enhancement
---

## 상세 설계 (How)

> [design.md](./design.md) 참조 (설계 승인 후 작성)

## 무엇을 (What)
LangFuse Writer/Scriptwriter 프롬프트에 쇼츠 템포 규칙을 주입하여 AI가 생성하는 스크립트 자체를 빠르게 만든다.

## 왜 (Why)
SP-106(config 수치 튜닝)만으로는 한계가 있음. 텍스트가 길면 수치를 줄여봐야 TTS가 잘리거나 부자연스러워짐.
**근본 해결 = AI가 처음부터 짧고 임팩트 있는 텍스트를 생성하는 것.**
시연 피드백 "템포가 느리다"의 절반은 스크립트 자체의 문제.

## 변경 대상

### 1. Writer Planning 프롬프트 (LangFuse: `creative/writer_planning`)
씬당 글자 수 목표 + 리듬 패턴 + Hook 설계 원칙 + scene_distribution 가이드 주입.

### 2. Scriptwriter 프롬프트 (LangFuse: `storyboard/default` 시스템)
씬 분리 원칙 + 오프닝 금지 패턴 + CTA 형식 + 감탄사 씬 활용 규칙 주입.

## 주입할 규칙

### Writer Planning 노드

```
## Tempo Rules (CRITICAL for Korean Shorts)

씬당 글자 수 목표:
- Hook 씬: 6~10자 (임팩트, 한 호흡)
- 정보 씬: 11~14자 (핵심만 압축)
- 전환 씬: 4~8자 (감탄사, 연결)
- 클라이맥스 씬: 최대 18자 (예외적으로 허용)
- 14자 초과 씬은 반드시 분리 검토

씬 길이 리듬 패턴:
- 짧음(6~10자) → 보통(11~14자) 교대 반복
- 3씬 연속 같은 길이 금지
- 클라이맥스 직전 씬은 반드시 짧게(6~8자)

Hook 설계 원칙:
- 씬 1은 절대 인사/예고 금지
- 결론을 씬 1에 배치, 이유는 씬 2~3에
- 숫자 훅 / 역설 훅 / 상황 특정 훅 우선

scene_distribution 목표 (30초 기준):
intro: 2, rising: 5, climax: 3, resolution: 1
```

### Scriptwriter 노드

```
## Shorts Tempo Rules (CRITICAL)

씬 분리 원칙:
- 한 씬 = 한 문장 = 한 정보. 쉼표 나열 금지.
- "A이고 B입니다" → 씬 분리: "A예요" + "B예요"

오프닝 금지 패턴:
- "오늘은 ~을 알려드릴게요" 절대 금지
- "안녕하세요" 절대 금지
- 씬 1은 바로 Hook 또는 결론

CTA 형식:
- 마지막 씬: 10자 이하, 명령형
- "팔로우해요" / "저장해두세요" / "한번 써보세요"

감탄사 씬 활용:
- 정보 씬 2~3개마다 4~6자 감탄사 씬 삽입 권장
- "맞아요." / "진짜요?" / "근데요."
```

## 완료 기준 (DoD)

### Must (P0)
- [ ] Writer Planning 프롬프트에 Tempo Rules 블록 추가
- [ ] Scriptwriter 프롬프트에 Shorts Tempo Rules 블록 추가
- [ ] 기존 스토리보드 1개 이상 재생성하여 씬당 글자 수 감소 확인

### Should (P1)
- [ ] 일본어/영어 버전 Tempo Rules도 동일 수준으로 작성
- [ ] Writer Planning의 scene_distribution 기본값을 duration별로 명시

### Could (P2)
- [ ] Director 노드에 "Hook 씬" 개념 추가 (첫 씬은 1.0~1.5초 타겟)
- [ ] Critic 노드에 "14자 초과 씬 경고" 검증 규칙 추가

## 참조
- LangFuse 프롬프트 관리: `backend/services/agent/langfuse_prompt.py`
- Writer Planning 노드: `backend/services/agent/nodes/` (writer 관련)
- Scriptwriter 노드: `backend/services/agent/nodes/` (scriptwriter 관련)
- 스토리보드 작가 템포 가이드라인: SP-106 논의에서 도출

## 힌트
- LangFuse UI에서 프롬프트 버전만 올리면 되므로 코드 변경 최소
- SP-106(config 수치)보다 먼저 적용 권장 — 텍스트가 짧아진 상태에서 수치를 줄여야 TTS 잘림 방지
- `langfuse_prompt.py`의 템플릿명 매핑 확인 후 정확한 프롬프트 키 특정 필요
