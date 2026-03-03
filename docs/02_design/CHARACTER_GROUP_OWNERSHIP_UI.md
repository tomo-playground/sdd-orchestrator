# Character-Group 소유권 개편 UI/UX 설계

> **상태**: Phase 1-4 전체 완료
> **작성일**: 2026-03-02
> **관련 변경**: Character.style_profile_id 제거 → Group이 화풍 유일한 SSOT. Phase 3-4: 편집 시리즈 변경 + 목록 그룹화 + 캐릭터 복제

---

## 1. 설계 원칙

### 1.1 핵심 원칙
- **화풍 SSOT = Group**: 캐릭터는 화풍을 소유하지 않는다. Group이 유일한 소유자.
- **원천 UI 수정 원칙 준수**: 화풍 변경은 오직 GroupConfigEditor에서만 가능.
- **크로스 시리즈 = 별개 캐릭터**: 동일인이 다른 시리즈에 출연하면 별도 캐릭터 엔티티로 관리.

### 1.2 크로스 시리즈 결정 근거
현재 규모(시리즈 6개, 캐릭터 13명)와 화풍별 프리뷰/LoRA 차이를 고려하면,
"하나의 캐릭터가 여러 시리즈에 소속"하는 M:N 구조는 과설계다.

| 방안 | 장점 | 단점 |
|------|------|------|
| **A. M:N (junction table)** | 이론적으로 깔끔 | UI 복잡, 화풍별 프리뷰/LoRA 충돌, 과설계 |
| **B. 1:N (group_id FK)** | 단순, 화풍별 프리뷰 자연 분리 | 동일인 복사 필요 |
| **C. 원본+변형 (parent_id)** | 복사 자동화, 원본 추적 | 동기화 복잡 |

**선택: B안 (1:N) + "캐릭터 복제" 기능**

이유:
- 예민이(플랫)와 예민이(시네마틱)는 프리뷰, LoRA 조합, 프롬프트가 모두 다르다.
- 별도 엔티티가 실제 운영에 맞다. "복제" 버튼으로 생성 편의성을 보완한다.

---

## 2. 캐릭터 위저드 재설계

### 2.1 스텝 변경

**현재**: Style(0) → BasicInfo(1) → Appearance(2) → LoRA(3) → Prompts(4)
**제안**: Group(0) → BasicInfo(1) → Appearance(2) → LoRA(3) → Prompts(4)

Step 0이 "화풍 선택"에서 "시리즈 선택"으로 변경된다.
화풍은 선택한 시리즈로부터 자동 파생되어 읽기 전용 배지로 표시한다.

### 2.2 Step 0: 시리즈 선택 (GroupStep)

```
+------------------------------------------------------------------+
| Select Series                                                     |
| Choose which series this character belongs to.                    |
+------------------------------------------------------------------+
|                                                                    |
|  +-------------------------+  +-------------------------+          |
|  | 1분 상식                |  | 오늘의 이야기           |          |
|  | [v] Selected            |  |                         |          |
|  |                         |  |                         |          |
|  | [Palette] 플랫 애니메   |  | [Palette] 플랫 애니메   |          |
|  | 5 characters            |  | 5 characters            |          |
|  +-------------------------+  +-------------------------+          |
|                                                                    |
|  +-------------------------+  +-------------------------+          |
|  | 잠자리 동화             |  | 실화 탐구               |          |
|  |                         |  |                         |          |
|  | [Palette] 그림책        |  | [Palette] 실사           |          |
|  | 2 characters            |  | 2 characters            |          |
|  +-------------------------+  +-------------------------+          |
|                                                                    |
|  +-------------------------+  +-------------------------+          |
|  | 꿈꾸는 모험             |  | 감성 한 스푼            |          |
|  |                         |  |                         |          |
|  | [Palette] 수채화 판타지 |  | [Palette] 시네마틱 애니메|          |
|  | 2 characters            |  | 0 characters            |          |
|  +-------------------------+  +-------------------------+          |
|                                                                    |
+------------------------------------------------------------------+
```

**세부 사항**:
- 각 카드에 시리즈명, 화풍명(배지), 소속 캐릭터 수 표시
- 시리즈 미선택 시 다음 스텝 진행 불가 (`canProceed = group_id !== null`)
- 선택 시 해당 Group의 `style_profile_id` → `baseModel` 자동 파생 (LoRA 필터링용)
- "시리즈 없이 생성" 옵션은 제공하지 않음 (모든 캐릭터는 시리즈에 소속)

### 2.3 baseModel 파생 경로

```
GroupStep에서 시리즈 선택
  → Group.style_profile_id 확인
  → StyleProfile.sd_model_id → SDModel.base_model
  → wizardReducer에 styleBaseModel 저장
  → LoraStep에서 base_model 필터링
```

현재 StyleStep에서 `onSelect(id, baseModel)` 하던 것을 GroupStep에서 동일하게 처리한다.

### 2.4 Reducer 변경사항

```typescript
// 현재
| { type: "SET_STYLE_PROFILE"; id: number; baseModel: string | null }

// 변경
| { type: "SET_GROUP"; groupId: number; groupName: string;
    styleProfileId: number | null; baseModel: string | null }
```

WizardState 변경:
```typescript
// 제거
style_profile_id: number | null;

// 추가
group_id: number | null;
group_name: string | null;
style_profile_id: number | null;  // Group에서 파생 (읽기 전용)
```

### 2.5 Save 페이로드 변경

```typescript
// 현재
const payload = {
  style_profile_id: state.style_profile_id,
  ...
};

// 변경
const payload = {
  group_id: state.group_id,
  // style_profile_id 제거 — Backend가 group_id로부터 파생
  ...
};
```

---

## 3. 캐릭터 편집 페이지 재설계

### 3.1 헤더 변경

**현재**:
```
Characters / 예민이   [Palette 플랫 애니메]         [Delete] [Save]
```

**제안**:
```
Characters / 예민이                                  [Delete] [Save]
  소속: 1분 상식 (플랫 애니메) [시리즈 설정 >]
```

### 3.2 ASCII 와이어프레임

```
+------------------------------------------------------------------+
| [<- Characters] / 예민이                    [Delete]  [Save]      |
| 소속: 1분 상식 · 플랫 애니메  [시리즈 설정 열기]                  |
+------------------------------------------------------------------+
|                                                                    |
| +--Preview Panel--+  +--Detail Sections-----------------------+   |
| |                  |  |                                        |   |
| |   [Character     |  | BASIC INFO                            |   |
| |    Preview]      |  | +------------------------------------+|   |
| |                  |  | | Series  [1분 상식     v]            ||   |
| |   3:4 aspect     |  | |   Style: 플랫 애니메 (읽기 전용)   ||   |
| |                  |  | | Name    [예민이            ]        ||   |
| |                  |  | | Desc    [활발한 소녀...    ]        ||   |
| |                  |  | | Gender  (Female) (Male)             ||   |
| | [Regen][Enhance] |  | +------------------------------------+|   |
| | [Edit]           |  |                                        |   |
| +------------------+  | > Voice         Preset #3              |   |
|                       | > IP-Adapter    clip_face (0.65)       |   |
|                       | > Appearance    8 tags                 |   |
|                       | > LoRA          1 LoRA selected        |   |
|                       | > Prompts                              |   |
|                       +----------------------------------------+   |
+------------------------------------------------------------------+
```

### 3.3 BasicInfoSection 변경

**현재**: StyleProfile 선택 pill 버튼 (직접 편집 가능)
**제안**: 시리즈 드롭다운 + 화풍 읽기 전용 표시

```typescript
// BasicInfoSection 내부
<div>
  <label>Series</label>
  <select value={form.group_id} onChange={...}>
    {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
  </select>
  <span className="text-xs text-zinc-400">
    Style: {derivedStyleName}
    <Link href="#" onClick={openGroupConfig}>시리즈 설정에서 변경</Link>
  </span>
</div>
```

**시리즈 변경 시 동작**:
1. 확인 다이얼로그 표시: "시리즈를 변경하면 화풍이 바뀝니다. 기존 LoRA가 호환되지 않을 수 있습니다."
2. 승인 시: group_id 변경 → LoRA 호환성 체크 → 비호환 LoRA 자동 제거
3. 프리뷰 이미지는 유지 (새 화풍으로 재생성 권유 토스트)

### 3.4 CharacterFormData 변경

```typescript
export type CharacterFormData = {
  group_id: number | null;           // 추가
  // style_profile_id 제거 — group에서 파생
  name: string;
  description: string;
  gender: ActorGender | null;
  // ... 나머지 동일
};
```

---

## 4. 캐릭터 목록 페이지 재설계

### 4.1 Group별 그룹화

**현재**: 플랫 그리드, 필터(All / Has LoRA / Has Preview)
**제안**: 시리즈별 섹션 구분 + 기존 필터 유지

### 4.2 ASCII 와이어프레임

```
+------------------------------------------------------------------+
| Characters (13)                              [+ New Character]    |
+------------------------------------------------------------------+
| [Search characters...]                                            |
| [All] [Has LoRA] [Has Preview]                                    |
+------------------------------------------------------------------+
|                                                                    |
| -- 1분 상식 · 플랫 애니메 (5) --------------------------          |
| +--------+ +--------+ +--------+ +--------+ +--------+            |
| |예민이  | |유카리  | |건우    | |미도리  | |하루    |            |
| |        | |        | |        | |        | |        |            |
| |  3:4   | |  3:4   | |  3:4   | |  3:4   | |  3:4   |            |
| | Female | | Female | | Male   | | Male   | | Male   |            |
| +--------+ +--------+ +--------+ +--------+ +--------+            |
|                                                                    |
| -- 잠자리 동화 · 그림책 (2) -------------------------             |
| +--------+ +--------+                                              |
| |수빈    | |지호    |                                              |
| | Female | | Male   |                                              |
| +--------+ +--------+                                              |
|                                                                    |
| -- 실화 탐구 · 실사 (2) ----------------------------              |
| +--------+ +--------+                                              |
| |유나    | |도윤    |                                              |
| | Female | | Male   |                                              |
| +--------+ +--------+                                              |
|                                                                    |
| -- 꿈꾸는 모험 · 수채화 판타지 (2) ------------------             |
| +--------+ +--------+                                              |
| |시온    | |수아    |                                              |
| | Male   | | Female |                                              |
| +--------+ +--------+                                              |
|                                                                    |
| -- 감성 한 스푼 · 시네마틱 애니메 (2) ----------------             |
| +--------+ +--------+                                              |
| |소라    | |하나    |                                              |
| | Female | | Female |                                              |
| +--------+ +--------+                                              |
|                                                                    |
+------------------------------------------------------------------+
```

### 4.3 세부 설계

**섹션 헤더**:
- 시리즈명, 화풍 배지, 캐릭터 수
- 클릭 시 해당 시리즈 필터링 (토글)
- 접기/펼치기 지원 (기본: 모두 펼침)

**필터 동작**:
- "All" 필터 시 시리즈별 섹션으로 그룹화
- "Has LoRA" / "Has Preview" 필터 시에도 섹션 구조 유지
- 검색 시 섹션 내에서 매칭된 카드만 표시 (빈 섹션 자동 숨김)

**CharacterCard 변경**:
- 기존 카드 디자인 유지 (이미 잘 설계됨)
- 하단 오버레이에 시리즈 배지 추가 (선택적, 플랫 뷰일 때만)

### 4.4 "시리즈에서 캐릭터 추가" 흐름

섹션 헤더 우측에 `[+ 추가]` 버튼:
```
-- 감성 한 스푼 · 시네마틱 애니메 (2) --------- [+ 추가]
```

클릭 시 위저드 진입, Step 0(시리즈 선택)이 해당 시리즈로 사전 선택된 상태.
URL: `/library/characters/new?group_id=12`

---

## 5. GroupConfigEditor 연동

### 5.1 캐릭터 관리 섹션 추가

GroupConfigEditor 모달에 "소속 캐릭터" 읽기 전용 목록을 추가한다.

```
+--GroupConfigEditor Modal-----------------------------------------+
| 시리즈 설정                                              [x]     |
+------------------------------------------------------------------+
| 시리즈 이름  [1분 상식          ]                                 |
| 설명         [재미있는 상식...  ]                                 |
+------------------------------------------------------------------+
| DEFAULTS                                                          |
| Render Preset    [Default Preset  v]                              |
| Style Profile    [플랫 애니메    v]                               |
| Narrator Voice   [Preset #3      v]                               |
+------------------------------------------------------------------+
| CHARACTERS (5)                                   [캐릭터 관리 >]  |
| +------+ +------+ +------+ +------+ +------+                     |
| |예민이| |유카리| |건우  | |미도리| |하루  |                     |
| +------+ +------+ +------+ +------+ +------+                     |
+------------------------------------------------------------------+
|                                    [Cancel]  [Save]               |
+------------------------------------------------------------------+
```

**세부 사항**:
- 캐릭터 목록은 **읽기 전용** 미니 아바타 (이름 + 프리뷰 썸네일)
- "캐릭터 관리" 링크 클릭 시 `/library/characters?group=12` 로 이동
- 이 섹션은 GroupConfig의 정보 제공 목적이며, 캐릭터 추가/제거는 하지 않음
- **화풍 변경 시 경고**: "이 시리즈에 5명의 캐릭터가 소속되어 있습니다. 화풍을 변경하면 프리뷰 이미지 재생성이 필요할 수 있습니다."

---

## 6. 캐릭터 복제 기능

### 6.1 용도
동일 캐릭터를 다른 시리즈에서 사용할 때 (크로스 시리즈).
예: "1분 상식"의 예민이 → "감성 한 스푼"으로 복제.

### 6.2 UI 위치
캐릭터 편집 페이지 헤더의 액션 영역:

```
[<- Characters] / 예민이               [Duplicate] [Delete] [Save]
```

### 6.3 복제 다이얼로그

```
+--Duplicate Character--------------------------------------------+
| "예민이"를 다른 시리즈로 복제합니다.                             |
|                                                                   |
| 대상 시리즈  [감성 한 스푼 (시네마틱 애니메)  v]                 |
| 새 이름      [예민이                           ]                 |
|                                                                   |
| 복제 항목:                                                       |
| [v] 이름, 설명, 성별                                             |
| [v] 외형 태그 (Appearance)                                       |
| [v] 프롬프트 (Custom / Reference)                                |
| [ ] LoRA (대상 시리즈와 baseModel이 다를 수 있음)                |
| [ ] 프리뷰 이미지 (화풍이 다르므로 재생성 권장)                  |
|                                                                   |
|                                         [Cancel] [Duplicate]      |
+------------------------------------------------------------------+
```

**동작**:
1. 대상 시리즈 선택 (현재 시리즈 제외)
2. baseModel 호환성 자동 체크 → LoRA 복사 가능 여부 표시
3. 복제 후 새 캐릭터 편집 페이지로 이동
4. "프리뷰 재생성을 권장합니다" 토스트 표시

---

## 7. 데이터 모델 변경 요약

### 7.1 Character 타입 변경

```typescript
// frontend/app/types/index.ts
export type Character = {
  id: number;
  group_id: number | null;              // 추가
  group_name: string | null;            // 추가 (응답 전용)
  // style_profile_id: number | null;   // 제거 (group에서 파생)
  // style_profile_name: string | null; // 제거
  name: string;
  // ... 나머지 동일
};
```

### 7.2 API 변경 예상

| 엔드포인트 | 변경 |
|-----------|------|
| `POST /characters` | `style_profile_id` 제거, `group_id` 필수 |
| `PUT /characters/:id` | `group_id` 변경 허용, `style_profile_id` 제거 |
| `GET /characters` | 응답에 `group_id`, `group_name` 포함 |
| `GET /characters/:id` | 응답에 `group_id`, `group_name` 포함 |
| `POST /characters/:id/duplicate` | 신규: 캐릭터 복제 |

---

## 8. 마이그레이션 전략

### 8.1 데이터 마이그레이션
기존 캐릭터의 `style_profile_id` → 소속 시리즈 매핑:
- 동일 `style_profile_id`를 가진 Group으로 자동 매핑
- 매핑 불가 시 (다중 후보) 수동 지정 필요

### 8.2 UI 마이그레이션 단계
1. **Phase 1**: Character 타입에 `group_id` 추가 (nullable), 기존 `style_profile_id` 유지
2. **Phase 2**: 위저드 GroupStep 추가, 편집 페이지에 시리즈 드롭다운 추가
3. **Phase 3**: `style_profile_id` 필드 제거, 모든 UI에서 Group 경유로 전환
4. **Phase 4**: 목록 페이지 시리즈별 그룹화, 복제 기능

---

## 9. 접근성 체크리스트

- [ ] GroupStep 카드: `role="radio"` + `aria-checked`
- [ ] 시리즈 드롭다운: `aria-label="소속 시리즈"`, 키보드 탐색
- [ ] 읽기 전용 화풍 표시: `aria-label="화풍: 플랫 애니메 (시리즈 설정에서 변경)"`
- [ ] 섹션 접기/펼치기: `aria-expanded` 상태 관리
- [ ] 복제 다이얼로그: 포커스 트랩, ESC 닫기

---

## 10. 컴포넌트 계층 구조 (핸드오프)

### 10.1 신규 컴포넌트

```
builder/steps/GroupStep.tsx          — Step 0 (시리즈 선택 카드 그리드)
builder/components/GroupCard.tsx     — 시리즈 선택 카드
[id]/DuplicateDialog.tsx             — 캐릭터 복제 모달
```

### 10.2 수정 컴포넌트

```
builder/CharacterWizard.tsx          — Step 라벨/흐름 변경
builder/wizardReducer.ts             — group_id 상태 추가, style_profile_id 파생
builder/steps/StyleStep.tsx          — 삭제 또는 GroupStep으로 대체
[id]/page.tsx                        — 헤더 배지 변경, Duplicate 버튼 추가
[id]/CharacterDetailSections.tsx     — BasicInfoSection: 시리즈 드롭다운
page.tsx (목록)                      — 시리즈별 그룹화 로직
CharacterCard.tsx                    — group_name 배지 (선택적)
GroupConfigEditor.tsx                — 소속 캐릭터 읽기 전용 섹션
```

### 10.3 상태 관리 요구사항

- wizardReducer: `SET_GROUP` 액션 추가 (`groupId`, `groupName`, `styleProfileId`, `baseModel`)
- useCharacterEdit: `group_id` 필드 추가, 시리즈 변경 시 LoRA 호환성 체크 로직
- useCharacters 훅: Group 정보 포함 응답 처리

### 10.4 반응형 브레이크포인트

| 컴포넌트 | Mobile (<640) | Tablet (640-1024) | Desktop (1024+) |
|----------|---------------|-------------------|-----------------|
| GroupStep 카드 | 1열 | 2열 | 3열 |
| 목록 섹션 카드 | 2열 | 3열 | 4-5열 |
| DuplicateDialog | 전체 너비 | 480px 모달 | 480px 모달 |
