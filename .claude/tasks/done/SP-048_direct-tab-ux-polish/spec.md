---
id: SP-048
priority: P1
scope: frontend
branch: fix/SP-048-direct-tab-ux-polish
created: 2026-03-22
status: done
approved_at: 2026-03-22
depends_on:
label: feat
---

## 무엇을 (What)
Direct 탭의 UX 미세 조정 — 액션 피드백 부재 2건 + 정보 불일치 3건 수정

## 왜 (Why)
e2e 리뷰에서 발견된 문제:
- 음성 톤/BGM 프리셋 클릭 시 적용 여부를 알 수 없음 (피드백 없음)
- "전체 적용 (7씬)" 버튼이 TTS 재생성인데 레이블만으로 알 수 없고, 실행 중 로딩 없음
- Speaker 드롭다운이 "Actor A/B"로 표시되어 Context Strip의 캐릭터 이름과 불일치
- Consistency 섹션이 "100% overall" + "No consistency data yet." 동시 표시 (모순)
- 화풍 정보가 Context Strip + DirectorControlPanel에 2중 표시

## 완료 기준 (DoD)
> AI가 이 목록으로 실패 테스트를 작성(RED)하고, 구현(GREEN)한다.

### 액션 피드백
- [x] DoD-1: 음성 톤 프리셋 클릭 시 `showToast("음성 톤: {label} 적용", "success")` 호출
- [x] DoD-2: BGM 분위기 프리셋 클릭 시 `showToast("BGM: {label} 적용", "success")` 호출
- [x] DoD-3: "전체 적용" 버튼 레이블이 TTS 재생성임을 명시
- [x] DoD-4: "전체 적용" 클릭 후 API 응답까지 버튼에 로딩 스피너 표시 + disabled 처리

### 정보 일관성
- [x] DoD-5: Speaker 드롭다운에 캐릭터 이름 표시 (characterAName이 있으면 "A: 재민", 없으면 "Actor A" fallback)
- [x] DoD-6: Consistency 데이터가 없을 때 overall 퍼센트를 "--"로 표시 (100% 아님)
- [x] DoD-7: DirectorControlPanel에서 화풍(Style Profile) 섹션 제거 (Context Strip에 이미 표시)

### 품질
- [x] 기존 테스트 regression 없음
- [x] 린트 통과

## 상세 설계 (How)
> [design.md](./design.md) 참조

## 영향 분석
- `DirectorControlPanel.tsx` — 음성톤/BGM 토스트, 화풍 섹션 제거, 전체적용 레이블+로딩
- `ScenesTab.tsx` — handleApplyAll 로딩 상태, DirectorControlPanel에 showToast/isApplying 전달
- `SceneEssentialFields.tsx` — store에서 캐릭터 이름 직접 읽기, Speaker option 텍스트 변경
- `ConsistencyPanel.tsx` — scenes 빈 배열 시 overall "--" 표시

## 제약 (Boundaries)
- 변경 파일 6개 이하 목표
- Backend 변경 없음 (순수 Frontend)
- SceneCard props 구조 변경 금지 (별도 리팩토링 태스크)

## 힌트
- `DirectorControlPanel.tsx:64-75` — handleEmotionClick / handleBgmClick에 showToast 추가
- `ScenesTab.tsx:130-165` — handleApplyAll에 loading state 추가
- Speaker dropdown: `SceneEssentialFields.tsx:70-78` 내 `<select>` option label 변경
- Consistency: `ConsistencyPanel.tsx:51-54` overall 표시 조건 분기
- 화풍 제거: `DirectorControlPanel.tsx:127-138` 블록 + 관련 import 삭제
