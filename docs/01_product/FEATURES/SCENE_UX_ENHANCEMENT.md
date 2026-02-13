# Scene UX Enhancement (Phase 7-6)

**출처**: Figma 프로토타입 vs 현행 UI 비교 분석 (2026-02-13)
**원칙**: "Simple by default, Powerful when needed"
**상태**: 진행중 (Phase A 완료 2026-02-13)

---

## Phase A: Quick Wins

### A-1. 씬 완성도 도트

**What**: SceneFilmstrip의 각 씬 썸네일 하단에 4개 상태 도트 표시.

| 도트 | 기준 | 색상 |
|------|------|------|
| 대본 | `scene.script` 존재 여부 | green / red |
| 이미지 | `scene.image` 또는 후보 이미지 존재 | green / red |
| 검증 | `match_rate >= 70%` | green (>=70) / amber (50~69) / red (<50) / gray (미생성) |
| 액션 | `character_actions` 1개 이상 | green / gray (N/A) |

**Why**: 현재는 씬 목록에서 어떤 씬이 완성되었고 어떤 씬이 미완인지 한눈에 파악 불가. 도트로 즉시 진행 상태 확인.

**수락 기준**:
- [x] SceneFilmstrip 각 씬에 4-dot 렌더링
- [x] 데이터 변경 시 실시간 반영 (추가 API 없음, 기존 store 데이터 활용)
- [x] 빌드 PASS

### A-2. 프로젝트 인사이트 패널

**What**: SceneSidePanel 상단에 읽기 전용 집계 패널 표시.

| 지표 | 계산 |
|------|------|
| 총 길이 | `sum(scene.duration)` |
| 씬 완성도 | 대본+이미지 완비 씬 / 전체 씬 |
| 이미지 생성률 | 이미지 보유 씬 / 전체 씬 |
| 평균 Match Rate | `avg(scene.match_rate)` (생성된 씬만) |
| 렌더 준비 | 모든 씬 대본+이미지 완비 시 "Ready" |

**Why**: 스토리보드 전체 진행 상황을 한눈에 파악. 렌더링 가능 여부 즉시 판단.

**수락 기준**:
- [x] 5개 지표 표시 (compact 카드 레이아웃)
- [x] 기존 storyboard/scene 데이터에서 프론트엔드 계산 (추가 API 없음)
- [x] 빌드 PASS

### A-3. 대본 글자수/읽기시간

**What**: SceneFormFields 대본 입력란 하단에 인라인 메타데이터 표시.

**형식**: `18자 · 읽기 2.3초 · 권장 범위`

| 항목 | 계산 |
|------|------|
| 글자수 | `script.length` (공백 제외 옵션) |
| 읽기시간 | 한국어: 초당 4자 / 일본어: 초당 5자 / 영어: 초당 2.5단어 |
| 권장 범위 | 15~30자 (한국어 기준), 범위 내 = 체크, 초과 = 경고 |

**Why**: 쇼츠 영상 특성상 씬당 대본 길이가 핵심. 현재는 감으로 작성 중.

**수락 기준**:
- [x] 글자수 + 읽기시간 + 범위 판정 표시 (Korean/Japanese/English 3개 언어)
- [x] 범위 초과 시 amber 경고 뱃지 (red가 아님 - 강제하지 않음)
- [x] 빌드 PASS

---

## Phase B: Feature

### B-4. 씬 편집 탭 분리

**What**: SceneCard 내부를 3개 탭으로 분리.

| 탭 | 포함 컴포넌트 |
|----|-------------|
| 대본 | SceneFormFields (script, duration) + 글자수 표시 + 노트 |
| 비주얼 | SceneImagePanel (이미지, 후보, match_rate) + 프롬프트 표시 |
| 고급 | SceneCharacterActions + SD 파라미터 + 검증 결과 |

**Why**: 현재 SceneCard에 모든 편집 요소가 한 화면에 나열되어 있어 스크롤이 길고 집중도 낮음.

**수락 기준**:
- [ ] 3탭 전환 (기본 = 대본 탭)
- [ ] 탭 상태 유지 (씬 전환 시 마지막 활성 탭 기억)
- [ ] 기존 컴포넌트 재배치 수준 (신규 컴포넌트 최소화)
- [ ] 빌드 PASS

### B-5. 노트 & 메모

**What**: 씬별 자유 텍스트 메모 기능.

**Backend**:
- `scenes` 테이블에 `notes` 컬럼 추가 (`Text`, nullable)
- Alembic 마이그레이션 생성
- 기존 PATCH `/scenes/{id}` API에 `notes` 필드 추가

**Frontend**:
- 대본 탭 하단에 textarea (placeholder: "이 씬에 대한 메모...")
- autoSave 연동 (기존 씬 저장 로직과 통합)

**Why**: 제작 과정에서 씬별 아이디어, 수정 사항, 참고 URL 등을 기록할 곳이 없음.

**수락 기준**:
- [ ] DB 마이그레이션 + DBA 리뷰 통과
- [ ] API PATCH 지원 + response_model 포함
- [ ] 프론트엔드 textarea + autoSave 연동
- [ ] 빌드 PASS + 신규 테스트

### B-6. 씬별 AI 재생성

**What**: 특정 씬만 Gemini에게 재생성 요청. 전체 스토리보드 컨텍스트(다른 씬들의 흐름)를 유지하면서 선택한 씬만 업데이트.

**모달 UI**:
- 수정 지시 텍스트 입력 (예: "더 긴장감 있게", "배경을 밤으로 변경")
- 재생성 범위 체크박스: 대본 / 비주얼 프롬프트 / 캐릭터 액션
- "재생성" 버튼 → Gemini API 호출 → 결과 미리보기 → 적용/취소

**Backend API**: `POST /storyboard/{id}/scenes/{scene_id}/regenerate`

```json
{
  "instruction": "더 긴장감 있게 수정해줘",
  "scope": ["script", "visual", "actions"],
  "context_scenes": [/* 주변 씬 요약 - 자동 */]
}
```

**Gemini 호출 전략**:
- 전체 스토리보드의 씬 목록을 컨텍스트로 전달
- 대상 씬만 재생성 지시 (나머지는 참조용)
- 기존 씬 데이터와 Gemini 응답을 범위별로 병합

**Why**: 현재는 특정 씬이 마음에 안 들면 전체 스토리보드를 재생성하거나 수동 편집만 가능. 부분 재생성으로 생산성 대폭 향상.

**수락 기준**:
- [ ] API: scope 파라미터에 따라 부분 재생성 + 기존 데이터 병합
- [ ] Gemini 컨텍스트: 전체 씬 흐름 유지 (앞뒤 씬 참조)
- [ ] 모달: 지시 텍스트 + 범위 선택 + 결과 미리보기
- [ ] 적용 전 diff 확인 가능 (변경 전/후 비교)
- [ ] 에러 시 기존 씬 데이터 보존 (롤백 안전)
- [ ] 빌드 PASS + 신규 테스트 (API + Gemini mock)

---

## 의존성

| 항목 | 선행 조건 |
|------|----------|
| A-1 완성도 도트 | 없음 (기존 데이터 활용) |
| A-2 인사이트 패널 | 없음 |
| A-3 글자수/읽기시간 | 없음 |
| B-4 탭 분리 | 없음 (컴포넌트 재배치) |
| B-5 노트 | B-4 탭 분리 (대본 탭에 배치) |
| B-6 AI 재생성 | 없음 (독립 기능, 단 B-4 후 비주얼 탭에 버튼 배치 권장) |
