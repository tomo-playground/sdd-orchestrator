# SP-091 설계

## 구현 방법

### 1. `frontend/app/components/shell/SettingsShell.tsx` — Trash 탭 제거

- `TABS` 배열에서 `{ href: "/settings/trash", label: "Trash", icon: Trash2 }` 항목 삭제
- `Trash2` import 제거
- 결과: 탭 2개 (Render Presets, YouTube)

### 2. `frontend/app/components/shell/LibraryShell.tsx` — 하단 휴지통 링크 추가

- `Trash2` 아이콘 import 추가 (lucide-react)
- `SubNavShell`에 직접 하단 링크를 넣지 않음 (SubNavShell은 공용 컴포넌트)
- LibraryShell에서 SubNavShell을 감싸는 구조로 변경:
  - SubNavShell 하단(children 아래가 아닌 nav 영역 아래)에 구분선 + 휴지통 링크 배치
- **구체적 접근**: SubNavShell의 `tabs` prop 외에 `footerLink` optional prop 추가
  - 타입: `{ href: string; label: string; icon: LucideIcon }` (optional)
  - 탭바 nav 내부, 탭 목록 오른쪽 끝에 `ml-auto` 배치로 시각적 분리
  - 비활성 스타일 (TAB_INACTIVE) + 휴지통 아이콘
  - `pathname.startsWith(footerLink.href)` 시 TAB_ACTIVE 적용

### 3. `frontend/app/(service)/library/trash/page.tsx` — 신규 페이지

- 기존 `TrashTab` 컴포넌트를 재사용
- `settings/trash/page.tsx`와 동일 패턴:
  ```tsx
  "use client";
  import TrashTab from "../../../components/settings/TrashTab";
  export default function LibraryTrashPage() {
    return (
      <div className="px-8 py-6">
        <TrashTab />
      </div>
    );
  }
  ```

### 4. `frontend/app/(service)/settings/trash/page.tsx` — 삭제

- 파일 삭제 (리다이렉트로 대체)

### 5. `frontend/next.config.ts` — 리다이렉트 추가

- `redirects()` 배열에 추가:
  ```ts
  { source: "/settings/trash", destination: "/library/trash", permanent: true },
  ```

### 변경 파일 요약

| 파일 | 변경 | 유형 |
|------|------|------|
| `components/shell/SettingsShell.tsx` | Trash 탭 제거 | 수정 |
| `components/shell/LibraryShell.tsx` | footerLink로 휴지통 링크 전달 | 수정 |
| `components/shell/SubNavShell.tsx` | footerLink optional prop 추가 | 수정 |
| `(service)/library/trash/page.tsx` | 신규 페이지 (TrashTab 재사용) | 생성 |
| `(service)/settings/trash/page.tsx` | 삭제 | 삭제 |
| `next.config.ts` | redirect 규칙 추가 | 수정 |

## 테스트 전략

### 1. 빌드 테스트
- `next build` 성공 확인 (빌드 에러 0개)

### 2. 수동 검증 (Playwright 브라우저)
- `/library/trash` 접속 시 TrashTab 정상 렌더링
- `/settings/trash` 접속 시 `/library/trash`로 리다이렉트 확인
- Library 탭바에 휴지통 링크 표시 + 클릭 동작 확인
- Settings 탭바에 Trash 탭 미표시 확인 (Render Presets, YouTube 2개만)

### 3. 기존 테스트 확인
- `vitest run` 전체 통과 확인 (TrashTab 컴포넌트 테스트가 있다면 import 경로 변경 없으므로 영향 없음)
