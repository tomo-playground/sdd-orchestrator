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

## 2. Feedback & Overlay

사용자에게 상태를 알리거나 추가 정보를 제공합니다.

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

### `Skeleton`
로딩 상태를 나타내는 플레이스홀더입니다.
- **Path**: `app/components/ui/Skeleton.tsx`
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
  import { Film } from "lucide-react";

  <EmptyState
    icon={Film}
    title="씬이 없습니다"
    description="새로운 씬을 추가해보세요."
    action={<Button onClick={addScene}>씬 추가</Button>}
  />
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
