# DESIGN.md — Design Principles & UI System

The workspace should feel **trustworthy and dense like Google Drive**, but **warm,
colorful and modern like Asana/Monday**. Productive, not playful; clear, not corporate.

## 1. Principles

1. **Content first, chrome second.** Files and folders are the hero. Navigation and
   toolbars stay quiet (neutral greys), color is reserved for actions, status, and identity.
2. **One primary action per view.** Each screen has a single, obvious "next step"
   rendered as the only filled-primary button. Everything else is secondary/ghost.
3. **Calm density.** Show a lot without clutter: generous row height (44–52px), 8px
   spacing grid, hairline dividers (`--line`) instead of heavy borders/cards everywhere.
4. **Soft, not flat, not skeuomorphic.** 10–12px radii, single subtle shadow elevation
   for floating surfaces (menus, modals, toasts). No drop-shadow on static rows.
5. **Identity through color.** Users get a deterministic avatar color from their id;
   share badges and presence reuse it. Color = who, not decoration.
6. **Responsive by default.** Every block works at 360px (phone) and 1440px+ (desktop).
   The file browser collapses from table → comfortable list on small screens. No
   horizontal scroll on phones.
7. **Localized & directional.** All copy goes through i18n. Layout is logical-property
   based (`margin-inline`, `padding-inline`) so RTL locales (ar, he, fa) mirror correctly.
8. **Accessible.** AA contrast minimum, visible focus ring (`--focus`), full keyboard
   path, `aria-*` on interactive blocks, 44px min tap target on mobile.

## 2. Design tokens

Defined as CSS custom properties in `frontend/src/styles/tokens.css`. Light theme is
the baseline; a dark theme overrides the same variables under `[data-theme="dark"]`.

### Color

```
--bg            #F7F8FA   app background
--surface       #FFFFFF   cards, sheets, rows
--surface-2     #F1F3F6   hover / subtle fill
--line          #E6E8EC   hairline dividers / borders
--text          #1B1F26   primary text
--text-muted    #5B6472   secondary text
--text-faint    #9AA2B1   tertiary / placeholders

--primary       #4C6FFF   brand action (indigo-blue)
--primary-700   #3A57D6   hover/pressed
--primary-50    #ECF0FF   tint backgrounds

--success       #1FB57A   editor / saved
--warning       #F5A623   reader / pending
--danger        #E5484D   destructive
--accent-purple #7C5CFC   secondary accent (Monday-ish)

--focus         #4C6FFF   focus ring color
```

Role colors (share levels): `owner → --primary`, `editor → --success`,
`reader → --text-muted`.

### Spacing — 8px grid

`--s-1:4px  --s-2:8px  --s-3:12px  --s-4:16px  --s-5:24px  --s-6:32px  --s-8:48px`

### Radius / elevation

```
--r-sm 8px   --r-md 10px   --r-lg 14px   --r-full 999px
--shadow-1  0 1px 2px rgba(16,24,40,.06)
--shadow-2  0 8px 24px rgba(16,24,40,.12)   (floating surfaces)
```

### Typography

System stack: `Inter, "Segoe UI", system-ui, -apple-system, sans-serif`.
Scale (size/line/weight):

```
display  24 / 32 / 700     page titles
h1       20 / 28 / 600
h2       16 / 24 / 600     section headers
body     14 / 20 / 400     default
small    13 / 18 / 400     meta, table secondary
caption  12 / 16 / 500     labels, badges (uppercase tracking .02em)
```

## 3. Building blocks (component catalog)

Implemented in `frontend/src/components/ui/`. Each is presentational, prop-driven,
i18n-aware, and themeable via tokens only (no hard-coded colors).

| Component | Purpose | Key props |
|-----------|---------|-----------|
| `AppShell` | Top bar + collapsible sidebar + content slot; responsive (sidebar → drawer on mobile) | `nav`, `user` |
| `BaseButton` | Actions | `variant: primary\|secondary\|ghost\|danger`, `size`, `icon`, `loading`, `block` |
| `BaseInput` | Text/email/password field with label, hint, error | `modelValue`, `type`, `label`, `error` |
| `BaseSelect` | Native-backed styled select (used by language picker) | `options`, `modelValue` |
| `BaseModal` | Centered dialog on mobile-safe sheet; focus-trapped | `open`, `title`, `size` |
| `BaseDrawer` | Slide-in panel (node details, sharing) | `open`, `side` |
| `DataTable` | Dense rows on desktop, card list on mobile; sortable header | `columns`, `rows`, `mobileCard` |
| `Avatar` | Deterministic colored initials; size variants; stack | `name`, `id`, `size` |
| `Badge` | Status/role pill | `tone: owner\|editor\|reader\|neutral\|success\|danger` |
| `Toast` / `useToast` | Transient feedback, top-right (top-center mobile) | `tone`, `message` |
| `Menu` | Contextual dropdown (row actions: open/share/rename/delete) | `items`, anchor |
| `EmptyState` | Friendly zero-data illustration + primary CTA | `title`, `action` |
| `Breadcrumbs` | Folder path; collapses middle on mobile | `path` |
| `FileIcon` | Format glyph + tint per type (doc/sheet/slide/other) | `format` |
| `LanguagePicker` | Searchable locale list w/ native names | `modelValue`, `locales` |
| `Spinner` / `Skeleton` | Loading affordances | `size` |
| `Tabs` | Section switch (admin user page: Bio / Stats / History) | `tabs`, `modelValue` |

## 4. Layout patterns

- **AppShell**: left sidebar (My files / Shared with me / Recent) on desktop ≥1024px;
  becomes a top hamburger drawer below that. Max content width 1200px, gutters 24px
  (16px on mobile).
- **File browser**: `DataTable` columns `Name · Owner · Modified · Shared · ⋯`. On
  mobile collapses to a two-line card: name + icon on top, meta + actions below.
- **Sharing**: `BaseDrawer` with user search (`Avatar` + name), role `BaseSelect`
  per grant, list of current grants with role `Badge` and remove.
- **Editor**: full-bleed CO `<iframe>` under a slim breadcrumb bar with back + title +
  share button. No SPA chrome competing with the editor toolbar.

## 5. Motion

Subtle and fast: 120–160ms ease-out for hovers/menus, 200ms for modals/drawers.
Respect `prefers-reduced-motion`. Never animate layout of file rows on data refresh.

## 6. Do / Don't

- ✅ Use `Badge` tones for roles everywhere a role appears (consistent color language).
- ✅ Keep one filled-primary button per screen.
- ✅ Use logical CSS properties for RTL safety.
- ❌ No raw hex in components — tokens only.
- ❌ No nested cards-in-cards. Prefer hairline `--line` separation.
- ❌ No blocking spinners for actions <400ms; use optimistic UI + `Toast`.
