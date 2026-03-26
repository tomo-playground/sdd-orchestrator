# SP-094 설계

## 구현 방법

### 변경 파일 1: `frontend/tests/helpers/fixtures/studio.ts`

씬 fixture에 E2E 검증에 필요한 필드 보강:
- `id` (DB ID) 추가 — 씬별 고유 ID가 있어야 삭제/편집 후 검증 가능
- `client_id` 추가 — 프론트엔드 씬 식별자
- `scene_mode`, `isGenerating`, `debug_payload` 등 필수 필드 기본값 보강

### 변경 파일 2: `frontend/tests/helpers/mockApi.ts`

`mockStudioApis`에 Direct 탭 E2E용 추가 모킹:

| API | Method | Mock 응답 | 용도 |
|-----|--------|----------|------|
| `**/scene/generate` | POST | `{ image_url, image_asset_id, ... }` | 이미지 생성 트리거 확인 |
| `**/storyboards` | POST | `{ id: 1, ... }` | autoSave (신규) |
| `**/storyboards/{id}` | PUT | 200 OK + 저장된 storyboard | autoSave (업데이트), 프롬프트 편집 후 저장 |
| `**/preview/tts` | POST | `{ audio_url, duration, cache_key }` | TTS 미리보기 |

기존 `mockStudioApis`의 GET 라우트는 유지하고, POST/PUT 라우트를 추가하는 형태.
별도 헬퍼 함수 `mockDirectTabApis(page)` 추출도 가능하나, 기존 패턴(`mockStudioApis` 확장)을 우선 따른다.

### 변경 파일 3: `frontend/tests/vrt/studio-e2e.spec.ts`

기존 `test.describe("Studio Page")` 블록 안에 Direct 탭 시나리오 4개 추가:

**시나리오 10: 씬 선택 -> 이미지 생성 트리거 확인**
1. `page.goto("/studio?id=1")` (3개 씬이 있는 storyboard 로드)
2. Direct 탭 클릭
3. 씬 목록에서 첫 번째 씬이 표시되는지 확인 (SceneCard 렌더링)
4. "Generate" 버튼 클릭
5. `page.route`로 인터셉트한 `POST /scene/generate` 호출이 발생했는지 확인 (`requestPromise` 패턴)
6. mock 응답 후 `isGenerating` 상태가 해제되는지 확인

**시나리오 11: 씬 프롬프트 편집 -> 저장 확인**
1. `page.goto("/studio?id=1")` + Direct 탭 이동
2. Script textarea에 텍스트 수정 (기존 "Good morning everyone!" -> "Hello world!")
3. autoSave가 트리거되어 `PUT /storyboards/1` 호출 발생 확인
4. 수정된 텍스트가 textarea에 유지되는지 확인

**시나리오 12: 씬 삭제 -> 목록 갱신**
1. `page.goto("/studio?id=1")` + Direct 탭 이동
2. SceneActionBar의 메뉴 버튼(3dot) 클릭
3. "Delete Scene" 클릭
4. ConfirmDialog에서 "Delete" 확인
5. 씬 목록에서 해당 씬이 제거되었는지 확인 (씬 개수 감소)

**시나리오 13: TTS 미리보기 버튼 클릭 -> 오디오 상태 표시**
1. `page.goto("/studio?id=1")` + Direct 탭 이동
2. "미리듣기" 버튼 클릭
3. `POST /preview/tts` 호출 발생 확인
4. mock 응답 후 "재생" 버튼이 표시되는지 확인 (또는 AudioWaveform 표시)

### API 모킹 전략

모든 외부 API는 `page.route()` 인터셉트 방식:
- SD WebUI(`/scene/generate`) -> fixture JSON 즉시 반환
- TTS(`/preview/tts`) -> fixture JSON 즉시 반환
- autoSave(`POST/PUT /storyboards`) -> 기존 mock storyboard에 id 부여하여 반환
- API 호출 발생 확인은 `page.waitForRequest()` 또는 `let called = false; route.fulfill()` 패턴 사용

### 주의사항
- autoSave는 debounce(2초)가 있으므로 프롬프트 편집 테스트에서 `page.waitForTimeout` 또는 `waitForRequest` 필요
- 이미지 생성 시 `autoSaveStoryboard()`가 선행 호출되므로 POST/PUT storyboards mock이 반드시 필요
- ConfirmDialog는 포커스 트래핑이 있으므로 버튼 텍스트로 정확히 찾아야 함

---

## 테스트 전략

### E2E 테스트 (Playwright) — `studio-e2e.spec.ts` 확장

| # | 시나리오 | 검증 포인트 | 비고 |
|---|---------|-----------|------|
| 10 | 씬 이미지 생성 | Generate 버튼 -> API 호출 발생, 로딩 해제 | `waitForRequest` |
| 11 | 씬 프롬프트 편집+저장 | textarea 수정 -> autoSave PUT 호출 | debounce 대기 필요 |
| 12 | 씬 삭제 | 메뉴 -> Delete -> 확인 -> 씬 수 감소 | ConfirmDialog 2단계 |
| 13 | TTS 미리보기 | 미리듣기 클릭 -> API 호출 -> 재생 버튼 표시 | audio_url mock |

### 테스트 범위 한정
- **포함**: Direct 탭 핵심 4개 사용자 플로우 (DoD 범위)
- **제외**: 실제 이미지 생성 결과 검증, 실제 TTS 오디오 재생 검증, Gemini AI Edit 모달, 의상 변경 모달
- **이유**: Phase C 리팩토링의 회귀 방지가 목적이므로 "호출이 발생하고 UI가 반응하는지"까지만 검증

### 실행 방법
```bash
cd frontend && npx playwright test tests/vrt/studio-e2e.spec.ts
```
