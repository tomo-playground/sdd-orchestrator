# Frontend 코딩 표준 (TypeScript)

**최종 업데이트**: 2026-03-15

> `/review` 커맨드 Step 4 아키텍처 리뷰 체크리스트. 코드 작성 및 리뷰 시 필수 준수.

---

## 1. Null/Undefined 처리 — `??` 기본 원칙

`??` (nullish coalescing)를 기본으로 사용한다. `||` (logical OR)는 `0`, `false`, `""` 도 falsy로 처리하여 유효한 값을 덮어쓰는 버그를 유발한다.

| 연산자 | 처리 대상 | 허용 범위 |
|--------|----------|----------|
| `??` | `null`, `undefined` 만 | **기본 원칙** |
| `\|\|` | `0`, `false`, `""`, `null`, `undefined` | 빈 문자열·0이 항상 invalid인 문자열 필드만 |

```typescript
// ✅
duration: scene.duration ?? 3        // 0은 유효한 값
weight: scene.weight ?? 0.5          // 0.0도 유효
title: scene.title || "Untitled"     // 빈 문자열은 invalid

// ❌ — 0을 기본값으로 교체하는 버그
duration: scene.duration || 3
weight: scene.weight || 0.5
```

**특히 금지**: SD 파라미터(steps, cfg_scale, weight, seed)에 `||` 기본값 사용 금지.

---

## 2. 타입 반환 — `Record<string, unknown>` 금지

API 요청/응답 payload는 명시적 `interface`로 정의한다. `Record<string, unknown>`은 컴파일 타임에 누락 필드를 검출할 수 없어 런타임 버그로 이어진다.

```typescript
// ✅
interface SceneRequest {
  prompt: string;
  width: number;
  character_id: number | null;
  use_reference_only: boolean;
  // ...
}
function buildSceneRequest(...): SceneRequest { ... }

// ❌
function buildSceneRequest(...): Record<string, unknown> { ... }
```

**허용 예외**: 외부 라이브러리 바인딩, 동적 키 매핑 테이블 등 타입 정의가 구조적으로 불가능한 경우.

---

## 3. 타입 단언 — 이중 assertion 금지

`as unknown as T`는 TypeScript 타입 체커를 완전히 우회한다. 절대 사용 금지.

```typescript
// ✅ — Type Guard 함수
function isScene(s: unknown): s is Scene {
  return typeof s === "object" && s !== null && "id" in s;
}

// ✅ — 명시적 타입 좁히기
const scene = data as Scene;  // 타입 구조가 보장된 경우

// ❌
(s as unknown as Scene)
```

---

## 4. 에러 처리 — 표준 패턴

| 규칙 | 내용 |
|------|------|
| `getErrorMsg()` 사용 | `catch (error)` 블록에서 `getErrorMsg(error, "기본 메시지")` 필수 |
| axios 에러 분기 | `axios.isAxiosError(error)` 체크 후 처리 |
| 빈 핸들러 금지 | `.catch(() => {})` 금지 — 최소 `console.error()` 필수 |

```typescript
// ✅
} catch (error) {
  showToast(getErrorMsg(error, "저장 실패"), "error");
}

// ✅ axios 분기
} catch (error) {
  if (axios.isAxiosError(error) && error.code === "ECONNABORTED") {
    showToast("요청 시간이 초과됐습니다.", "error");
    return null;
  }
  showToast(getErrorMsg(error, "생성 실패"), "error");
}

// ❌
} catch { }
.catch(() => {})
```

---

## 5. Store 상태 접근 — 함수당 1회 원칙

각 store의 `getState()`는 **함수 시작부에서 1회만** 호출하고 로컬 변수에 캐시한다. 함수 중간 재호출은 다른 시점의 데이터를 읽어 일관성 버그를 유발한다.

```typescript
// ✅
export async function generateSceneImageFor(scene: Scene) {
  const sbState = useStoryboardStore.getState();       // 시작부 1회
  const { storyboardId } = useContextStore.getState(); // 시작부 1회
  const { showToast } = useUIStore.getState();         // 시작부 1회

  // sbState 재사용
  const { hiResEnabled, characterLoras } = sbState;
}

// ❌ — 함수 중간 재호출 (다른 시점 데이터)
const scene1 = useStoryboardStore.getState().scenes[0];
await saveStoryboard();  // 상태 변경 가능
const scene2 = useStoryboardStore.getState().scenes[0];  // 다른 값!
```

**예외**: 상태 변경 후 최신값이 반드시 필요한 경우, 주석으로 이유를 명시한다.
```typescript
await updateScene(clientId, patch);
// Re-fetch: updateScene이 내부적으로 상태를 교체하므로 최신 ref 필요
const updated = useStoryboardStore.getState().scenes.find(...);
```

---

## 6. 타입 정의 위치

| 타입 범위 | 위치 | 예시 |
|----------|------|------|
| 공용 (2개 이상 파일) | `app/types/index.ts` 또는 `app/types/*.ts` | `Scene`, `Storyboard` |
| 파일 내부 전용 | 파일 **최상단** 선언 | `type GenerateOpts` |
| 함수 내부 | **금지** | — |

**`interface` vs `type`**:
- 객체 구조 → `interface` (확장 가능)
- union / intersection / primitive 조합 → `type`

```typescript
// ✅ 파일 상단 선언
type GenerateOpts = { scene: Scene; silent: boolean };
async function generateSync(opts: GenerateOpts) { ... }

// ❌ 함수 내부 정의
async function generateSync() {
  type GenerateOpts = { ... };  // 금지
}
```

---

## 7. 비즈니스 로직 공유 — SSOT 원칙

동일한 도메인 로직(payload 구성, 파라미터 계산 등)은 **반드시 공통 함수 하나**로 추출한다. 두 경로가 같은 일을 다른 코드로 하면 한쪽 수정 시 누락 버그가 발생한다.

```typescript
// ✅ — 공통 빌더, 호출자에서 import
export function buildSceneRequest(scene, sbState, storyboardId): SceneRequest { ... }

// imageGeneration.ts (SSOT)
const req = { ...buildSceneRequest(scene, sbState, storyboardId), ...overrides };

// autopilotActions.ts — generateSceneImageFor() 경유로 buildSceneRequest 자동 사용
```

**적용 완료**: `buildSceneRequest()` — `imageGeneration.ts` SSOT.

---

## 리뷰 체크리스트

---

## 8. Zustand Store 초기값 — 안전 기본값 원칙

Generation 관련 boolean 초기값은 반드시 **`false`(비활성)**으로 설정한다. Backend `/presets` API의 `GenerationDefaults`가 SSOT이며, `applyGenerationDefaults()`가 런타임에 올바른 값을 반영한다.

```typescript
// ✅ 안전 기본값 — /presets 로드 전에도 부작용 없음
useControlnet: false,
useIpAdapter: false,
hiResEnabled: false,
multiGenEnabled: false,

// ❌ Backend SSOT와 불일치 위험
useControlnet: true,  // Backend가 False인데 Frontend가 true → 정책 위반
```

**이유**: `resolveSceneControlnet(scene, global)`에서 씬 값이 `null`이면 Store 초기값이 fallback으로 사용됨. 초기값이 `true`이면 Backend 정책(OFF)과 반대로 동작.

---

## 리뷰 체크리스트

```
[ ] 숫자/boolean 필드에 || 기본값 사용하지 않았는가? (→ ?? 사용)
[ ] payload 반환 함수가 Record<string, unknown> 이 아닌 interface 를 반환하는가?
[ ] as unknown as T 이중 assertion이 없는가?
[ ] catch 블록에 getErrorMsg() 또는 console.error() 가 있는가?
[ ] getState() 가 함수 시작부에서만 호출되는가?
[ ] 타입 정의가 함수 내부에 중첩되어 있지 않은가?
[ ] 동일한 로직이 두 곳 이상에 복사되어 있지 않은가?
[ ] Zustand Store generation boolean 초기값이 false(안전 기본값)인가?
```
