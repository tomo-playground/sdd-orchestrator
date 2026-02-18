# UI Components Guide

Shorts Producer에서 사용하는 공통 UI 컴포넌트 가이드입니다. `app/components/ui` 디렉토리에 위치합니다.

## 1. Form Components

일관된 디자인과 UX를 위해 표준화된 폼 컴포넌트를 사용합니다.

### `Input`
기본 텍스트 입력 필드입니다.
- **Path**: `app/components/ui/Input.tsx`
- **Features**: Focus ring, Error state, Size variants.
- **Usage**:
  ```tsx
  import { Input } from "@/app/components/ui";
  <Input value={val} onChange={...} error={isError} />
  ```

### `Textarea`
멀티라인 텍스트 입력 필드입니다.
- **Path**: `app/components/ui/Textarea.tsx`
- **Features**: Focus ring, Error state, Auto-resize (optional).
- **Usage**:
  ```tsx
  import { Textarea } from "@/app/components/ui";
  <Textarea rows={3} value={script} onChange={...} />
  ```

### `TagAutocomplete`
태그 입력 시 자동 완성을 제공하는 입력 필드입니다.
- **Path**: `app/components/ui/TagAutocomplete.tsx`
- **Features**: 검색 기반 태그 추천, 드롭다운 선택.

## 2. Button & Badge

### `Button`
표준화된 버튼 컴포넌트입니다.
- **Path**: `app/components/ui/Button.tsx`
- **Features**: Variant (`primary`, `secondary`, `danger`, `ghost` 등), Size (`sm`, `md`, `lg`), Loading state, Icon support.
- **Usage**:
  ```tsx
  import { Button } from "@/app/components/ui";
  <Button variant="primary" size="md" onClick={...}>저장</Button>
  ```

### `Badge`
상태/카테고리를 나타내는 라벨입니다.
- **Path**: `app/components/ui/Badge.tsx`
- **Features**: Variant (`default`, `success`, `warning`, `error`, `info`), Size (`sm`, `md`).
- **Usage**:
  ```tsx
  import { Badge } from "@/app/components/ui";
  <Badge variant="success">완료</Badge>
  ```

## 3. Feedback & Overlay

사용자에게 상태를 알리거나 추가 정보를 제공합니다.

### `Modal`
표준 모달 다이얼로그입니다.
- **Path**: `app/components/ui/Modal.tsx`
- **Features**: Size variants (`sm`, `md`, `lg`, `xl`), 오버레이 백드롭 (blur), ESC 닫기.
- **Usage**:
  ```tsx
  import { Modal } from "@/app/components/ui";
  <Modal open={isOpen} onClose={close} title="제목" size="md">
    {children}
  </Modal>
  ```

### `ConfirmDialog`
중요한 작업 전 사용자 확인을 받습니다.
- **Path**: `app/components/ui/ConfirmDialog.tsx`
- **Features**: Danger variant (Red), Input field support.
- **Usage**:
  ```tsx
  import { useConfirm } from "@/app/components/ui/ConfirmDialog";
  const { confirm } = useConfirm();

  const handleDelete = async () => {
    if (await confirm({ title: "삭제", description: "정말 삭제하시겠습니까?", variant: "danger" })) {
      // delete logic
    }
  };
  ```

### `Toast`
일시적인 알림 메시지입니다.
- **Path**: `app/components/ui/Toast.tsx`
- **Usage**:
  ```tsx
  import { useUIStore } from "@/app/store/useUIStore";
  const showToast = useUIStore((s) => s.showToast);
  showToast("저장되었습니다", "success");
  ```

### `Tooltip`
호버 시 나타나는 도움말입니다.
- **Path**: `app/components/ui/Tooltip.tsx`
- **Usage**:
  ```tsx
  import { Tooltip } from "@/app/components/ui";
  <Tooltip content="설명 텍스트">
    <button>Hover Me</button>
  </Tooltip>
  ```

### `Popover`
클릭 시 나타나는 플로팅 패널입니다.
- **Path**: `app/components/ui/Popover.tsx`

### `CommandPalette`
`Cmd+K` 단축키로 실행하는 커맨드 팔레트입니다.
- **Path**: `app/components/ui/CommandPalette.tsx`

## 4. Display & Layout

### `Skeleton`
로딩 상태를 나타내는 플레이스홀더입니다.
- **Path**: `app/components/ui/Skeleton.tsx`
- **Exports**: `Skeleton` (단일), `SkeletonGrid` (그리드).
- **Usage**:
  ```tsx
  import { Skeleton } from "@/app/components/ui";
  <Skeleton className="h-4 w-20" />
  ```

### `EmptyState`
데이터가 없을 때 보여주는 안내 화면입니다.
- **Path**: `app/components/ui/EmptyState.tsx`
- **Features**: Icon, Title, Description, Action Button.
- **Usage**:
  ```tsx
  import EmptyState from "@/app/components/ui/EmptyState";
  <EmptyState icon={Film} title="씬이 없습니다" description="새로운 씬을 추가해보세요." />
  ```

### `LoadingSpinner`
로딩 인디케이터입니다.
- **Path**: `app/components/ui/LoadingSpinner.tsx`
- **Features**: Size variants (`sm`, `md`, `lg`).

### `ErrorMessage`
에러 상태를 표시하는 메시지 컴포넌트입니다.
- **Path**: `app/components/ui/ErrorMessage.tsx`

### `SectionDivider`
섹션 간 구분선입니다.
- **Path**: `app/components/ui/SectionDivider.tsx`

### `CollapsibleSection`
접기/펴기 가능한 섹션 컨테이너입니다.
- **Path**: `app/components/ui/CollapsibleSection.tsx`

### `CopyButton`
클릭 시 클립보드에 텍스트를 복사하는 버튼입니다.
- **Path**: `app/components/ui/CopyButton.tsx`

### `Footer`
페이지 하단 푸터입니다.
- **Path**: `app/components/ui/Footer.tsx`

## 5. Media Preview

### `ImagePreviewModal`
이미지 확대 미리보기 모달입니다.
- **Path**: `app/components/ui/ImagePreviewModal.tsx`

### `VideoPreviewModal`
비디오 미리보기 모달입니다.
- **Path**: `app/components/ui/VideoPreviewModal.tsx`

## 6. Barrel Export (`index.ts`)

`app/components/ui/index.ts`에서 주요 컴포넌트를 re-export합니다:

```typescript
export { Badge, Button, Modal, ConfirmDialog, useConfirm } from "...";
export { LoadingSpinner, Skeleton, SkeletonGrid, ErrorMessage } from "...";
export { SectionDivider, Toast, Tooltip, Input, Textarea } from "...";
export { VideoPreviewModal, ImagePreviewModal } from "...";
export { cx } from "./variants";
```

## 7. Design Tokens (`variants.ts`)

`app/components/ui/variants.ts`에서 디자인 토큰과 유틸리티를 중앙 관리합니다.

| 토큰 | 용도 |
|------|------|
| `cx()` | 조건부 클래스 병합 헬퍼 |
| `OVERLAY_CLASSES` | 모달/다이얼로그 백드롭 |
| `CARD_CLASSES` | 표준 카드 서피스 |
| `LABEL_CLASSES` | 섹션 헤더 라벨 |
| `FOCUS_RING` | 포커스 링 |
| `DISABLED_CLASSES` | 비활성 상태 |

상세 토큰 목록은 [STUDIO_DESIGN_GUIDE.md](STUDIO_DESIGN_GUIDE.md) 참조.
