> **ARCHIVED (2026-03-17)**: 현재 코드와 불일치하여 아카이브됨. 현행 설계는 코드 및 CLAUDE.md를 참조.

# Manage Page: Sidebar Navigation Redesign

## Problem Statement

The current Manage page uses a horizontal tab bar with 10 flat items:
Tags, Style, Prompts, Eval, Insights, Assets, Presets, Voice, Settings, Trash.

Issues:
1. **Overcrowded** -- 10 horizontal tabs overflow on smaller screens, requiring `overflow-x-auto`.
2. **No grouping** -- Conceptually related items (e.g. Presets and Voice) sit far apart.
3. **No hierarchy** -- Everything is visually equal. Settings and Trash have the same weight as Tags.
4. **Inconsistent with Studio** -- Studio/Home pages already use a left sidebar (via `AppShell` + `Sidebar`), but Manage explicitly hides it (`showSidebar = !pathname.startsWith("/manage")`). This creates a jarring layout shift when navigating between Studio and Manage.

---

## Proposed Structure

### Category Grouping (3 groups + 2 standalone)

```
MANAGE SIDEBAR (w-56 / 224px)
================================

  CONTENT                         <- group label
  ├── Tags          (Tag)
  ├── Style         (Palette)
  └── Prompts       (FileText)

  QUALITY                         <- group label
  ├── Eval          (FlaskConical)
  └── Insights      (BarChart3)

  OUTPUT                          <- group label
  ├── Presets       (SlidersHorizontal)
  ├── Voice         (Mic)
  └── Assets        (FolderOpen)

  ─────────────────               <- divider

  Settings          (Settings)
  Trash             (Trash2)
```

### Grouping Rationale

| Group | Items | Why |
|-------|-------|-----|
| **Content** | Tags, Style, Prompts | Core creative building blocks. Tags define what goes into scenes, Style controls visual appearance, Prompts are the history of generated prompts. These are the elements a creator touches most. |
| **Quality** | Eval, Insights | Analytical / read-heavy pages for reviewing output quality. Both are consumption-oriented rather than configuration-oriented. |
| **Output** | Presets, Voice, Assets | Resources that affect rendering output. Presets configure render parameters, Voice defines TTS presets, Assets lists available BGM/fonts/LoRAs. |
| **Standalone** | Settings, Trash | Utility pages separated by a divider. Settings is system maintenance (storage, cache, Gemini config). Trash is soft-deleted items. These are used infrequently and belong below the fold. |

---

## Icon Mapping (lucide-react)

| Item | Icon | Import Name | Reasoning |
|------|------|-------------|-----------|
| Tags | `Tag` | `Tag` | Direct metaphor for tag management |
| Style | `Palette` | `Palette` | Art/visual style configuration |
| Prompts | `FileText` | `FileText` | Text-based prompt history records |
| Eval | `FlaskConical` | `FlaskConical` | Experimental testing / evaluation |
| Insights | `BarChart3` | `BarChart3` | Analytics and charts |
| Presets | `SlidersHorizontal` | `SlidersHorizontal` | Render parameter sliders |
| Voice | `Mic` | `Mic` | Audio / voice presets |
| Assets | `FolderOpen` | `FolderOpen` | File browser for media assets |
| Settings | `Settings` | `Settings` | Already used in AppShell for Manage link |
| Trash | `Trash2` | `Trash2` | Already used in Studio Sidebar |

---

## Layout Wireframe

### Desktop (>= 1024px)

```
+--[ Top Navbar: Home | Studio | Manage ]----+
|                                              |
|  +--[Sidebar]--+  +--[Content Area]-------+ |
|  |  w-56       |  |  flex-1               | |
|  |             |  |                       | |
|  |  CONTENT    |  |  (Active tab content  | |
|  |  > Tags     |  |   rendered here)      | |
|  |    Style    |  |                       | |
|  |    Prompts  |  |                       | |
|  |             |  |                       | |
|  |  QUALITY    |  |                       | |
|  |    Eval     |  |                       | |
|  |    Insights |  |                       | |
|  |             |  |                       | |
|  |  OUTPUT     |  |                       | |
|  |    Presets  |  |                       | |
|  |    Voice    |  |                       | |
|  |    Assets   |  |                       | |
|  |             |  |                       | |
|  |  ---------  |  |                       | |
|  |  Settings   |  |                       | |
|  |  Trash      |  |                       | |
|  +-------------+  +-----------------------+ |
+----------------------------------------------+
```

Key measurements:
- Sidebar: `w-56` (224px), matching the existing Studio Sidebar's expanded width of `w-64`.
- Content area: `flex-1`, with `max-w-5xl` preserved from current layout.
- Sidebar background: `bg-white` with `border-r border-zinc-200`, matching Studio Sidebar.

### Tablet (768px - 1023px)

Sidebar collapses to icon-only mode (`w-14`, 56px). Each item shows only its icon with a `title` tooltip.

```
+--[ Top Navbar ]---------------------------+
|                                            |
|  +--+  +--[Content Area]----------------+ |
|  |ic|  |  flex-1                         | |
|  |  |  |                                 | |
|  |Ta|  |  (Full width content)           | |
|  |Pa|  |                                 | |
|  |FT|  |                                 | |
|  |  |  |                                 | |
|  |Fl|  |                                 | |
|  |Ba|  |                                 | |
|  |  |  |                                 | |
|  |Sl|  |                                 | |
|  |Mi|  |                                 | |
|  |Fo|  |                                 | |
|  +--+  +---------------------------------+ |
+--------------------------------------------+
```

### Mobile (< 768px)

Sidebar disappears entirely. A horizontal scrollable pill bar appears at the top of the content area (similar to the current implementation but with only the category icons for initial navigation, then sub-items).

Alternative: a bottom sheet or hamburger-triggered drawer. Given that the Manage page is an admin/configuration screen primarily used on desktop, the collapsed icon sidebar at tablet is sufficient. Mobile can fall back to the current horizontal tabs as a pragmatic choice.

---

## Component Architecture

### New Files

```
frontend/app/manage/
├── ManageSidebar.tsx         <- New sidebar component
├── ManageLayout.tsx          <- New layout wrapper (sidebar + content)
└── page.tsx                  <- Updated to use ManageLayout
```

### ManageSidebar.tsx -- Data Structure

```typescript
type ManageNavItem = {
  id: ManageTab;
  label: string;
  icon: LucideIcon;
};

type ManageNavGroup = {
  label: string;
  items: ManageNavItem[];
};

const NAV_GROUPS: ManageNavGroup[] = [
  {
    label: "Content",
    items: [
      { id: "tags",    label: "Tags",    icon: Tag },
      { id: "style",   label: "Style",   icon: Palette },
      { id: "prompts", label: "Prompts", icon: FileText },
    ],
  },
  {
    label: "Quality",
    items: [
      { id: "evaluation", label: "Eval",     icon: FlaskConical },
      { id: "insights",   label: "Insights", icon: BarChart3 },
    ],
  },
  {
    label: "Output",
    items: [
      { id: "presets", label: "Presets", icon: SlidersHorizontal },
      { id: "voice",   label: "Voice",  icon: Mic },
      { id: "assets",  label: "Assets", icon: FolderOpen },
    ],
  },
];

const STANDALONE_ITEMS: ManageNavItem[] = [
  { id: "settings", label: "Settings", icon: Settings },
  { id: "trash",    label: "Trash",    icon: Trash2 },
];
```

### Active State Visual Treatment

```
Inactive item:
  text-zinc-500 hover:bg-zinc-50 hover:text-zinc-700

Active item:
  bg-zinc-100 font-medium text-zinc-900
  (left-side 2px accent bar: border-l-2 border-zinc-900)

Group label:
  text-[10px] font-bold tracking-[0.15em] text-zinc-400 uppercase
  px-4 pt-5 pb-1
```

The left accent bar (2px solid dark) on the active item provides instant scanability. This mirrors the pattern used by VS Code, Linear, and Notion sidebars.

---

## AppShell Integration

### Current Behavior (AppShell.tsx line 19)

```typescript
const showSidebar = !pathname.startsWith("/manage");
```

The Studio `Sidebar` (project/group/storyboard browser) is hidden when on `/manage`. This is correct -- the Manage page has its own navigation context.

### Proposed Change

The Manage page will render its own `ManageSidebar` inside the content area, rather than modifying `AppShell`. This keeps the two sidebars independent:

```
AppShell
├── TopNav (Home | Studio | Manage)
├── [Studio Sidebar -- hidden on /manage]
└── Content Area
    └── ManagePage
        ├── ManageSidebar   <- NEW, Manage-specific
        └── Active Tab Content
```

This approach avoids touching `AppShell.tsx` or the existing `Sidebar.tsx`. The Manage page simply wraps its own content in a `flex` row with its sidebar on the left.

---

## UX Improvements Beyond Reorganization

### 1. URL-Based Tab State

Currently the active tab is stored in React state only (`useState<ManageTab>("tags")`). If a user refreshes the page, they always land on "Tags". Proposed: sync with URL search params.

```
/manage?tab=tags
/manage?tab=evaluation
/manage?tab=settings
```

This enables:
- Deep linking to specific settings pages
- Browser back/forward navigation between tabs
- Sharing links to specific manage sections

### 2. Badge Indicators

Show counts or status badges on sidebar items to surface actionable information:

| Item | Badge | When |
|------|-------|------|
| Tags | pending count | `pendingTags.length > 0` (unapproved tags) |
| Trash | item count | `trashItems.length > 0` |
| Insights | "New" dot | New quality data since last visit |

```
  Tags          (Tag)       [3]    <- 3 pending tags
  Trash         (Trash2)    [12]   <- 12 items in trash
```

### 3. Keyboard Navigation

- `ArrowUp` / `ArrowDown` to move between sidebar items when sidebar is focused
- `Enter` to select
- Number keys `1-9` to jump to items (when sidebar is focused)
- `Cmd+[` / `Cmd+]` to move to previous/next tab

### 4. Collapsible Groups

Groups can be collapsed with a chevron toggle. State is persisted in `localStorage` under `manage-nav-collapsed` key.

```
  CONTENT              [v]     <- click to collapse
  > Tags
    Style
    Prompts

  QUALITY              [>]     <- collapsed
                                  (items hidden)
```

This is useful for users who primarily use one section (e.g., always in Content, rarely in Quality).

### 5. Page Titles

Each section should show a clear title and brief description at the top of the content area:

```
+--[Content Area]----------------------------+
|                                            |
|  Tags                                      |
|  Manage tag database and approve pending   |
|  tags from Gemini suggestions.             |
|                                            |
|  [Tab-specific content below...]           |
+--------------------------------------------+
```

This helps orientation, especially when arriving via deep link.

---

## Migration Path

### Phase 1: Sidebar Layout (minimal change)

1. Create `ManageSidebar.tsx` with grouped navigation.
2. Create `ManageLayout.tsx` wrapper (`flex` row with sidebar + content).
3. Update `page.tsx` to use `ManageLayout` instead of the current horizontal tabs.
4. All existing tab components remain untouched.
5. Add `?tab=` URL synchronization.

### Phase 2: Polish

1. Add badge indicators (pending tags count, trash count).
2. Add collapsible groups with localStorage persistence.
3. Add keyboard navigation.
4. Add page titles/descriptions for each section.

### Phase 3: Responsive

1. Add icon-only collapsed mode for tablet breakpoint.
2. Evaluate mobile behavior (keep horizontal tabs or add drawer).

---

## Visual Style Reference

The sidebar should match the existing Studio Sidebar visual language:
- Background: `bg-white`
- Border: `border-r border-zinc-200`
- Text: `text-xs` for items, `text-[10px]` for group labels
- Hover: `hover:bg-zinc-50 hover:text-zinc-700`
- Active: `bg-zinc-100 font-medium text-zinc-900`
- Icons: `h-4 w-4` (slightly larger than Studio Sidebar's `h-3.5 w-3.5` for readability)
- Item padding: `px-3 py-2` with `gap-2.5` between icon and label
- Group label: uppercase tracking with `text-zinc-400`
