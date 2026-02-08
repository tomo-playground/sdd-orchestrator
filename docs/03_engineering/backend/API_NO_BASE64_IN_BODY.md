# API 요청 body에 base64/data URL 금지

> 요청 body에 `data:` URL(base64 이미지)을 넣으면 payload가 수 MB~수십 MB가 되어 413, 타임아웃, Network Error가 발생합니다. **저장/검증/렌더 등 일반 API에는 이미지 URL(HTTP)만 보내거나, data:일 때는 호출하지 않습니다.**

## 원칙

- **보내지 말 것**: `image_url` / `image_b64` 필드에 `data:image/...;base64,...` 문자열을 넣어서 보내지 않는다.
- **허용**: 백엔드가 fetch할 수 있는 **HTTP(S) URL**만 전달하거나, 이미지가 아직 저장되지 않았으면 **해당 API 호출을 하지 않는다**.

## 적용 위치 (Frontend)

| 위치 | API | 방어 방법 |
|------|-----|-----------|
| `storyboardActions` | PUT/POST `/storyboards` | `image_url` 필드 자체를 payload에서 제거. `image_asset_id`로 참조 |
| `styleProfileActions` | PUT `/storyboards/:id` | 동일하게 `image_url` 제거, `image_asset_id` 사용 |
| `autopilotActions` (Validate) | POST `/scene/validate-and-auto-edit` | `scene.image_url`이 data:면 해당 씬 스킵; HTTP면 `image_url`로 전송 |
| `sceneActions` (수동 검증) | POST `/scene/validate-and-auto-edit` | data:면 "먼저 저장하세요" 토스트 후 호출 안 함; HTTP면 `image_url`로 전송 |
| `imageActions.validateImageCandidate` | POST `/scene/validate-and-auto-edit` | 인자로 받은 URL이 data:면 API 호출 안 함 (즉시 `null` 반환) |
| `imageActions.handleEditWithGemini` | POST `/scene/edit-with-gemini` | `scene.image_url`이 data:면 "먼저 저장하세요" 토스트 후 호출 안 함 |
| `imageActions.handleSuggestEditWithGemini` | POST `/scene/suggest-edit` | 동일 |
| `RenderTab` (렌더) | POST `/video/create-async` | 씬 중 하나라도 `image_url`이 data:면 "이미지를 저장한 뒤 렌더하세요" 토스트 후 요청 안 함 |
| `imageActions` (activity log) | POST `/activity-logs` | `image_url`이 data:면 `null`로 보냄 (백엔드도 data: 시 스킵) |

## base64가 남아 있는 것이 맞는 곳

- **이미지 생성/업로드 전용 API**: `/scene/generate`, `/scene/generate-batch` **응답**, `/image/store` **요청** — 이미지 바이너리를 주고받는 계약이므로 base64 사용.
- **프론트 플로우**: 생성 결과를 `data:` URL로 만들어 **즉시** `storeSceneImage()`로 보내고, 성공 시 `scene.image_url`을 저장된 HTTP URL로 교체. 실패 시에만 스토어에 data:가 남을 수 있음 → 위 표의 방어로 다른 API body에는 실리지 않음.

## 관련 코드

- `frontend/app/store/actions/storyboardActions.ts`: `sanitizeCandidatesForDb()` — candidates에서 `image_url` 제거 후 저장
- `backend/services/storyboard.py`: `create_scenes()` 내 `image_asset_id` 직접 설정 우선, `image_url` fallback 시 `data:` 무시
- `backend/services/image.py`: `load_image_bytes()` — data: URL은 디코딩 지원 (로컬 처리용); **요청 body에 긴 문자열을 실어 보내는 것은 금지**
