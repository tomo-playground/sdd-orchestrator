# Direct 탭 연출 컨트롤 레이어 + 메뉴 정리

**상태**: 계획
**목표**: Direct 탭을 "결과 확인 + 연출 조정"의 단일 허브로 강화

---

## 배경

### 현재 문제
1. **TTS 음성 톤을 조정할 곳이 없음** — 생성 후 음성 감정을 바꿀 수 없음
2. **BGM/Voice 설정이 Stage + Publish에 산재** — 어디서 수정해야 할지 혼란
3. **SceneCard 정보 과부하** — 30+ props, UX Audit P1 마찰
4. **전체 톤 일괄 변경 불가** — 20씬이면 20번 개별 수정

### 디자인 철학
- **원천 UI 수정 원칙**: SSOT를 소유한 UI에서만 수정 허용
- **ChatGPT Canvas 패턴**: 채팅 + 결과물 2-pane
- **HeyGen Voice Director 패턴**: 전체 기본값 + 라인별 오버라이드
- **카드 기반 편집**: 숏폼 도구 업계 주류

### "연출 의도" vs "렌더 파라미터" 경계

| 구분 | 예시 | 원천 UI |
|------|------|---------|
| **연출 의도** | 음성 톤(밝게/긴장), BGM 분위기(경쾌/잔잔), 감정선 | **Direct 탭 연출 컨트롤** |
| **렌더 파라미터** | bgmVolume, audioDucking, 폰트 크기, layout | **Publish 탭** (기존 유지) |
| **에셋 준비** | 배경 생성, 캐릭터 할당, BGM prebuild | **Stage 탭** (기존 유지) |

---

## 설계

### emotion 프리셋 → voice_design_prompt 연결 정책

| 사용자 액션 | 동작 |
|-----------|------|
| 프리셋 클릭 (예: "밝게") | 1) 전체 씬 `context_tags.emotion` 일괄 변경 (이미지 연출 반영) |
| | 2) 전체 씬 `voice_design_prompt` 초기화 (null) |
| | 3) TTS Designer 재실행 → 새 emotion 기반 voice_design 자동 생성 |
| "전체 적용" 클릭 | confirm dialog 표시 ("N씬 TTS 재생성, 약 M분 소요") → prebuild API |

### BGM 프리셋 SSOT

| 항목 | 저장 위치 | API |
|------|----------|-----|
| bgmMood | `useRenderStore.bgmMood` | 기존 유지 |
| bgmPrompt | `useRenderStore.bgmPrompt` | 기존 유지 |
| 프리셋 선택 | UI 상태만 (persist 불필요) | `/stage/bgm-prebuild` 재활용 |

### Direct 탭 레이아웃

```
+-- Direct 탭 (ScenesTab.tsx) --------------------------+
|                                                        |
| +-- 연출 컨트롤 패널 (NEW) --------------------------+ |
| |                                                    | |
| |  음성 톤:  [밝게] [차분] [긴장] [감성] [커스텀]     | |
| |  BGM:     [경쾌] [잔잔] [긴박] [로맨틱] [커스텀]    | |
| |  화풍:    플랫 애니메 (시리즈 설정)  읽기 전용       | |
| |                                                    | |
| |  Phase 2: 자연어 조정 입력                          | |
| |                                                    | |
| |  [전체 적용] (confirm: "9씬 TTS 재생성, 약 2분")    | |
| +----------------------------------------------------+ |
|                                                        |
| +-- 씬 카드 (간소화) --------------------------------+ |
| | [이미지] "대사..."                                  | |
| | 음성: [감정 오버라이드] [프리뷰] [재생성]            | |
| | 상세 설정 [접이식]                                  | |
| +----------------------------------------------------+ |
|                                                        |
| +-- 타임라인 ----------------------------------------+ |
| | [1][2][3][4][5][6][7][8][9]  총 30초                | |
| +----------------------------------------------------+ |
+--------------------------------------------------------+
```

---

## Sprint 구성

### Sprint 1: 연출 컨트롤 레이어 (핵심)

| # | 항목 | 파일 | 설명 |
|---|------|------|------|
| 1-1 | `DirectorControlPanel` 컴포넌트 | `components/studio/DirectorControlPanel.tsx` (NEW) | 음성 톤 + BGM 프리셋 UI |
| 1-2 | Direct 탭에 패널 배치 | `components/studio/ScenesTab.tsx` | 씬 리스트 위에 패널 삽입 |
| 1-3 | 음성 톤 프리셋 → emotion 일괄 변경 action | `store/useStoryboardStore.ts` | `setGlobalEmotion(emotion)` action |
| 1-4 | voice_design_prompt 초기화 + TTS prebuild | API 호출 | 기존 `/preview/tts` 활용 또는 일괄 API |
| 1-5 | BGM 프리셋 → bgmPrompt 변경 | `store/useRenderStore.ts` | 기존 setter 활용 |
| 1-6 | "전체 적용" confirm dialog | UI | 씬 수 + 예상 시간 표시 |

### Sprint 2: 씬 카드 간소화 + 우측 패널 정리

| # | 항목 | 설명 |
|---|------|------|
| 2-1 | SceneCard 핵심 정보만 표시 | 이미지 + 대사 + 감정 + 프리뷰 버튼 |
| 2-2 | 상세 정보 접이식 (CollapsibleSection 활용) | 프롬프트, 태그, 환경 등 숨김 |
| 2-3 | 감정 오버라이드 드롭다운 | 전체 톤과 다르게 개별 씬 변경 |
| 2-4 | 우측 패널 역할 정리 | 사용되지 않는 탭 제거 또는 통합 |

### Sprint 3: 설정 경계 재정의 (Sprint 1-2 완료 후)

| # | 항목 | 설명 |
|---|------|------|
| 3-1 | Stage BGM → 읽기 전용 + "Direct에서 변경" 링크 | prebuild는 Stage에 유지 |
| 3-2 | Publish BGM/Voice → "연출 의도"만 Direct 이동, "렌더 파라미터"는 유지 | bgmVolume/audioDucking = Publish 유지 |
| 3-3 | 연출 의도 vs 렌더 파라미터 SSOT 문서화 | CLAUDE.md 반영 |

### Sprint 4: 자연어 연출 조정 (Phase 2)

| # | 항목 | 설명 |
|---|------|------|
| 4-1 | 연출 컨트롤 내 미니 채팅 | 자연어 입력 UI |
| 4-2 | Backend: 연출 조정 API | 자연어 → TTS/Sound Designer 재실행 |
| 4-3 | Before/After 프리뷰 | 변경 전후 비교 재생 |
| 4-4 | 적용/원복 UX | 변경 확정 또는 롤백 |

---

## 병렬 작업 가능성

| Sprint | 의존성 | 다른 스레드 충돌 |
|--------|--------|-----------------|
| Sprint 1 | 없음 (Frontend 신규 컴포넌트) | 없음 — Phase 38(Backend observability)과 파일 겹침 없음 |
| Sprint 2 | Sprint 1 병행 가능 | SceneCard.tsx 수정 — 다른 스레드와 동시 수정 주의 |
| Sprint 3 | Sprint 1 완료 후 | Stage/Publish 컴포넌트 수정 — 충돌 가능, 순차 권장 |
| Sprint 4 | Sprint 1 완료 후 | Backend API 신규 — ComfyUI 전환과 시기 조율 필요 |

### 현재 다른 스레드 작업 (충돌 체크)

| 스레드 | 영향 파일 | 충돌 위험 |
|--------|----------|----------|
| Phase 38 (LangFuse Scoring) | `observability.py`, `review.py`, `config_pipelines.py`, 테스트 파일 | 없음 (Backend only) |
| 테스트 정비 | `tests/*.py`, `routers/*.py` | 없음 (Sprint 1은 Frontend) |

**결론: Sprint 1은 즉시 착수 가능, 다른 스레드와 충돌 없음.**

---

## 완료 기준 (DoD)

### Sprint 1
- [ ] Direct 탭 상단에 연출 컨트롤 패널 표시
- [ ] 음성 톤 프리셋 → 전체 씬 emotion + voice_design 초기화
- [ ] BGM 프리셋 → bgmPrompt/bgmMood 변경
- [ ] "전체 적용" confirm dialog + TTS 재생성
- [ ] 새로고침 후 프리셋 상태 복구 (Zustand persist)
- [ ] AutoRun 비파괴 검증 (연출 변경 후 Auto Run 정상)
- [ ] 빌드 PASS + ESLint PASS

### Sprint 2
- [ ] SceneCard 핵심 정보만 기본 표시
- [ ] 상세 정보 접이식 동작
- [ ] 감정 오버라이드 드롭다운 동작
- [ ] VRT 베이스라인 갱신
