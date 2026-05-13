# Code Audit Librarian — Frontend Design Blueprint

**Status:** Ready for AI Coding Agent Execution  
**Tech Stack:** Vue 3 + Composition API + Vite + Tailwind CSS  
**Design Philosophy:** Minimalist, modern, dark-theme-first, inspired by Linear, Vercel, and Supabase  
**Build Order:** Read this entire document before writing code.

---

## Table of Contents

1. [Design Philosophy & Aesthetic Direction](#design-philosophy--aesthetic-direction)
2. [Global Design System](#global-design-system)
3. [View 1: Entry/Homepage](#view-1-entryhomepage)
4. [View 2: Analyzing State (Pipeline Visualization)](#view-2-analyzing-state-pipeline-visualization)
5. [View 3: Global Dashboard (Overview)](#view-3-global-dashboard-overview)
6. [View 4: Split-Pane Explorer (Core UX)](#view-4-split-pane-explorer-core-ux)
7. [View 5: File Detail View (Right Pane)](#view-5-file-detail-view-right-pane)
8. [View 6: Global Utilities (Search & Filtering)](#view-6-global-utilities-search--filtering)
9. [Component Hierarchy](#component-hierarchy)
10. [State Management & Data Flow](#state-management--data-flow)
11. [Interaction Patterns & Animations](#interaction-patterns--animations)
12. [Accessibility & Performance Considerations](#accessibility--performance-considerations)

---

## Design Philosophy & Aesthetic Direction

### Guiding Principles

**Minimalist Clarity**  
- Signal-to-noise ratio maximized. Every element earns its place.
- Whitespace is active, not passive. Dense data is never cramped.
- Typography hierarchy is steep: distinct sizes create instant visual scannability.

**Dark Theme First**  
- Primary background: `#0F0F0F` (near-black, reduces eye strain during long audits)
- Elevated surfaces: `#1A1A1A`, `#252525` (subtle depth without glare)
- High contrast text ensures accessibility (WCAG AA+ minimum).

**Code-Centric Visual Language**  
- Monospace typography emphasizes code snippets and file paths (consistent with developer tools like VS Code, Linear, Vercel).
- Color-coded severity and issue categories echo terminal output and linting tools.
- Line numbers and code highlights reinforce the "audit report" nature of the tool.

**Progressive Information Disclosure**  
- Summary-first: dashboard shows birds-eye metrics before drilling into file details.
- Expansion on demand: tabs, accordions, collapsibles prevent cognitive overload.
- Lazy loading: file detail pane doesn't render until a file is selected.

**Inspiration from Linear, Vercel, Supabase**
- **Linear**: Clean table-based lists, issue severity badges, keyboard shortcuts, command palette (Cmd+K).
- **Vercel**: Elegant project pickers, progressive deploy/build status indicators, real-time logs.
- **Supabase**: Dark, minimal dashboard, structured table views, tabbed details sections.

---

## Global Design System

### Color Palette

#### Neutrals (Foundation)
```
--color-bg-primary:        #0F0F0F    (main background)
--color-bg-secondary:      #1A1A1A    (elevated surfaces, cards)
--color-bg-tertiary:       #252525    (hover states, subtle separation)
--color-bg-hover:          #323232    (interactive elements on hover)

--color-text-primary:      #FFFFFF    (body text, high contrast)
--color-text-secondary:    #A8A8A8    (secondary info, metadata)
--color-text-tertiary:     #707070    (disabled, de-emphasized)

--color-border:            #2D2D2D    (dividers, outlines)
--color-border-subtle:     #1F1F1F    (minimal separation)
```

#### Status & Severity Colors (with semantic meaning)
```
--color-severity-critical: #FF5E5E   (High severity - critical bugs, red alerts)
--color-severity-high:     #FF8A00   (High severity - important issues, orange)
--color-severity-medium:   #FFB800   (Medium severity - warnings, amber)
--color-severity-low:      #4ADE80   (Low severity - info, green)
--color-severity-info:     #60A5FA   (Informational, blue)

--color-status-success:    #10B981   (completed, passed)
--color-status-warning:    #F59E0B   (in progress, caution)
--color-status-error:      #EF4444   (failed, error)
--color-status-pending:    #6B7280   (not started, pending)
```

#### Accent Colors (for emphasis and call-to-action)
```
--color-accent-primary:    #3B82F6   (CTAs, highlighted selections, active states)
--color-accent-secondary:  #8B5CF6   (secondary actions, hover states)
--color-accent-hover:      #60A5FA   (lighter shade for hover)
```

#### Category Colors (for issue type identification)
```
--color-category-ai:       #A78BFA   (AI Issues - purple)
--color-category-eslint:   #34D399   (ESLint Flags - teal)
--color-category-a11y:     #FBBF24   (Accessibility - amber)
--color-category-api:      #60A5FA   (API Calls - blue)
```

### Typography

#### Font Stack
```
--font-display:   "Sohne", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
                  (bold, used for headings; fallback to system fonts)

--font-body:      "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
                  (body text, UI labels, clear and readable)

--font-mono:      "Menlo", "Monaco", "Courier New", monospace
                  (code snippets, file paths, line numbers)
```

#### Size Scale
```
--text-xs:        12px / 0.75rem   (metadata, timestamps, small labels)
--text-sm:        14px / 0.875rem  (secondary text, annotations)
--text-base:      16px / 1rem      (body text, default UI text)
--text-lg:        18px / 1.125rem  (section headers, card titles)
--text-xl:        20px / 1.25rem   (sub-section headers)
--text-2xl:       28px / 1.75rem   (page titles, dashboard headings)
--text-3xl:       32px / 2rem      (major section titles)
--text-4xl:       40px / 2.5rem    (hero/primary headings)
```

#### Line Height & Letter Spacing
```
--leading-tight:    1.2    (headings)
--leading-normal:   1.5    (body text)
--leading-relaxed:  1.75   (prose, descriptions)

--tracking-tight:   -0.02em (headings, compressed)
--tracking-normal:   0em    (default)
--tracking-wide:     0.05em (metadata, secondary text)
```

#### Font Weights
```
Regular:   400
Medium:    500
Semibold:  600
Bold:      700
```

### Spacing Scale

Derived from `8px` base unit (divisible, scales across all breakpoints):

```
--space-0:      0
--space-1:      4px    (minimal spacing, nested elements)
--space-2:      8px    (default, standard gaps)
--space-3:      12px   (comfortable spacing)
--space-4:      16px   (standard padding, margins)
--space-5:      20px   (section separation)
--space-6:      24px   (generous spacing)
--space-7:      28px   (component spacing)
--space-8:      32px   (major sections)
--space-10:     40px   (full-page margins)
--space-12:     48px   (large layout shifts)
--space-16:     64px   (page-level gaps)
```

### Shadows & Elevation

```
--shadow-sm:      0 1px 2px 0 rgba(0, 0, 0, 0.25)
--shadow-base:    0 4px 6px -1px rgba(0, 0, 0, 0.3)
--shadow-lg:      0 10px 15px -3px rgba(0, 0, 0, 0.4)
--shadow-xl:      0 20px 25px -5px rgba(0, 0, 0, 0.5)

Elevation levels:
  Level 0: No shadow (primary surface, #0F0F0F)
  Level 1: --shadow-sm (#1A1A1A, cards, modals)
  Level 2: --shadow-base (#252525, popovers, dropdowns)
  Level 3: --shadow-lg (floating elements, focus states)
```

### Border Radius

```
--rounded-none:      0
--rounded-sm:        4px   (subtle corners)
--rounded-base:      6px   (default, most elements)
--rounded-lg:        8px   (cards, modals)
--rounded-xl:        12px  (larger surfaces)
--rounded-2xl:       16px  (hero sections, major containers)
--rounded-full:      9999px (pills, rounded badges)
```

### Breakpoints

```
xs:  ≤ 480px   (mobile)
sm:  ≤ 768px   (tablet, small desktop)
md:  ≤ 1024px  (desktop)
lg:  ≤ 1440px  (widescreen)
xl:  > 1440px  (ultra-wide)

Primary breakpoint for split-pane: `md` (1024px)
Below md: stack vertically, hide left sidebar initially.
```

---

## View 1: Entry/Homepage

### Purpose
The user launches the tool. They see a clean, minimal interface that invites them to either:
1. Start a new audit on a project directory
2. View previously completed audit runs

### Mental Model
"Show me my projects and recent audits in one glance. Let me start a new scan quickly."

### Layout Map

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│              CODE AUDIT LIBRARIAN                               │
│              (Logo + Minimal Branding)                          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  LEFT SECTION (40%)          RIGHT SECTION (60%)               │
│                                                                 │
│  ┌─────────────────────┐  ┌──────────────────────────────────┐ │
│  │  Recent Audits      │  │  Quick Start                      │ │
│  │  ──────────────     │  │  ──────────────                   │ │
│  │  [2024-01-15]       │  │                                  │ │
│  │  MyProject v1.0     │  │  [Project Directory Input]       │ │
│  │  • 42 files         │  │  /path/to/vue-project           │ │
│  │  • 128 issues       │  │                                  │ │
│  │  • ✓ completed      │  │  [Browse...] [Analyze Now →]     │ │
│  │                     │  │                                  │ │
│  │  ──────────────     │  │  or drag a folder here           │ │
│  │  [2024-01-10]       │  │                                  │ │
│  │  WebApp v2.1        │  │                                  │ │
│  │  • 156 files        │  │                                  │ │
│  │  • 342 issues       │  │                                  │ │
│  │  • ✓ completed      │  │                                  │ │
│  │                     │  │                                  │ │
│  └─────────────────────┘  └──────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Structure

```
HomePage
├── Header
│   ├── Logo + Title ("Code Audit Librarian")
│   └── Minimal navigation (Settings icon, Docs link)
├── Main Content Grid (2 columns on md+, 1 column on sm-)
│   ├── RecentAuditsPanel (Left, sticky)
│   │   ├── Section Title
│   │   └── AuditCard (repeating)
│   │       ├── Timestamp
│   │       ├── Project Name
│   │       ├── File Count Badge
│   │       ├── Issue Count Badge
│   │       ├── Status Indicator (completed/in_progress/failed)
│   │       └── Click Handler → Navigate to Dashboard
│   └── QuickStartSection (Right)
│       ├── Section Title
│       ├── ProjectPathInput (with paste/drag support)
│       ├── ActionButtons
│       │   ├── Browse... (file dialog)
│       │   └── Analyze Now (disabled if no path)
│       └── DropZone Overlay (on drag-over state)
└── Footer
    └── Brief tagline + version
```

### Visual Design Details

#### Header
- **Background:** `#0F0F0F`
- **Logo:** Monospace text, font-weight 700, font-size 2rem, color `#FFFFFF`
- **Branding Subtitle:** "Vue.js Codebase Analysis Tool", size `xs`, color `#A8A8A8`
- **Spacing:** Padding `space-8` vertical and horizontal from edges

#### RecentAuditsPanel
- **Container:** Background `#1A1A1A`, border `1px solid #2D2D2D`, border-radius `rounded-lg`, padding `space-6`
- **Title:** Font-size `lg`, weight `600`, color `#FFFFFF`, margin-bottom `space-4`
- **Card (individual audit):**
  - **Background:** `#252525` on default, `#323232` on hover
  - **Padding:** `space-4`
  - **Border-radius:** `rounded-base`
  - **Transition:** All 200ms ease-out
  - **Timestamp:** Size `xs`, color `#707070`, weight 500
  - **Project Name:** Size `lg`, weight 600, color `#FFFFFF`, margin `space-2` top
  - **Metadata Row:** 
    - File count badge: background `#1A1A1A`, text `#60A5FA`, size `sm`, weight 500
    - Issue count badge: background `#1A1A1A`, text `#FF8A00`, size `sm`, weight 500
    - Separation: `space-2` between badges
  - **Status Indicator:** 
    - Completed: checkmark icon `✓`, color `#10B981`, size `sm`
    - In Progress: spinner animation, color `#F59E0B`
    - Failed: × icon, color `#EF4444`
  - **Hover Behavior:** 
    - Slight lift (transform: translateY(-2px))
    - Cursor changes to pointer
    - Border color shifts to `#3B82F6` (subtle accent)

#### QuickStartSection
- **Container:** Similar styling to RecentAuditsPanel
- **Title:** Matching typography
- **Input Field (ProjectPathInput):**
  - **Background:** `#1A1A1A`
  - **Border:** `1px solid #2D2D2D`, on focus: `1px solid #3B82F6`
  - **Padding:** `space-3` vertical, `space-4` horizontal
  - **Font:** Monospace, size `sm`, color `#FFFFFF`
  - **Placeholder:** Color `#707070`
  - **Focus:** Box-shadow `0 0 0 3px rgba(59, 130, 246, 0.1)`
  - **Transition:** Border 200ms ease-out
- **Button Group:**
  - **Browse Button (Secondary):**
    - Background: `transparent`, border `1px solid #2D2D2D`
    - Text: `#A8A8A8`, weight 500, size `base`
    - Padding: `space-2` vertical, `space-4` horizontal
    - Hover: Background `#252525`, border color `#3B82F6`
  - **Analyze Button (Primary):**
    - Background: `#3B82F6` (enabled) or `#4B5563` (disabled)
    - Text: `#FFFFFF`, weight 600, size `base`
    - Padding: `space-3` vertical, `space-4` horizontal
    - Hover: Background `#60A5FA` (if enabled)
    - Disabled: Cursor `not-allowed`, opacity `0.5`
    - Icon: Right-aligned arrow "→"

#### DropZone Overlay (when dragging over)
- **Overlay:** Background `rgba(59, 130, 246, 0.1)`, border `2px dashed #3B82F6`
- **Animation:** Fade in/out 150ms ease
- **Text:** "Drop project folder here", color `#3B82F6`, weight 500

### Interaction & State Flows

**User Flow 1: Select Recent Audit**
1. User clicks on a recent audit card.
2. Card shows hover state (lift + border color shift).
3. On click, fetch audit metadata and redirect to Dashboard for that run_id.

**User Flow 2: Start New Audit**
1. User clicks "Browse..." → file picker opens (native OS dialog).
2. User selects a directory.
3. Path fills in the input field.
4. User clicks "Analyze Now" → validate path, show loading state on button, redirect to Analyzing state.

**User Flow 3: Drag & Drop**
1. User drags a folder over QuickStartSection.
2. DropZone overlay appears (fade in, dashed border).
3. On drop, validate as a directory, fill input, proceed like User Flow 2.

### Empty States

**No Recent Audits:**
- RecentAuditsPanel shows a placeholder message: "No audits yet. Get started by analyzing a project!"
- Placeholder is centered, size `sm`, color `#707070`

**Invalid Directory:**
- Input shows red border momentarily (200ms).
- Error message appears below input: "Directory not found or invalid path", size `xs`, color `#FF5E5E`

---

## View 2: Analyzing State (Pipeline Visualization)

### Purpose
While the backend runs (Scouting → ESLint → AI Analysis → Synthesis), show the user a beautiful, engaging loading screen. The pipeline progresses visibly, so they know work is happening.

### Mental Model
"I can see exactly what stage the audit is at. No spinning mystery. The tool feels responsive and professional."

### Layout Map

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                   Analyzing Project                             │
│                   /path/to/my/project                           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                                                             │ │
│  │                   PIPELINE PROGRESS                        │ │
│  │                                                             │ │
│  │  [PHASE 1]       [PHASE 2]       [PHASE 3]       [PHASE 4] │ │
│  │   SCOUT          ESLINT          AI ANALYSIS      SYNTHESIS │ │
│  │   ✓ DONE         ▸ IN PROGRESS   ◦ PENDING       ◦ PENDING  │ │
│  │                                                             │ │
│  │   Connected line flow showing progression                 │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Progress Details                                           │ │
│  │  ──────────────────────────────────────────────────────────│ │
│  │  Phase: AI Analysis                                         │ │
│  │  Current File: src/components/UserModal.vue (24/156 files) │ │
│  │  ▓▓▓▓▓▓▓▓░░░░░░░░░ 15% complete                            │ │
│  │                                                             │ │
│  │  Last 5 Findings:                                           │ │
│  │  • UserModal.vue: [HIGH] Prop validation missing            │ │
│  │  • UserForm.vue: [MEDIUM] Unhandled promise                 │ │
│  │  • API.js: [LOW] Deprecated API endpoint                    │ │
│  │  • Utils.js: [INFO] Large utility bundle                    │ │
│  │  • Card.vue: [HIGH] Missing accessibility attributes       │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│               [Cancel Analysis]  [Minimize & Continue]         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Structure

```
AnalyzingState
├── Header
│   ├── Title ("Analyzing Project")
│   ├── Subtitle (project path)
│   └── Elapsed Time Counter
├── PipelineProgressVisual
│   ├── PhaseCard (×4: Scout, ESLint, AI Analysis, Synthesis)
│   │   ├── Phase Title (uppercase, monospace)
│   │   ├── Status Icon (✓ done, ▸ in progress, ◦ pending)
│   │   └── Status Text
│   ├── ConnectorLine (SVG connecting phases horizontally)
│   └── AnimatedFlow (visual progression indicator)
├── ProgressDetailsPanel
│   ├── Current Phase Label
│   ├── Current File Info
│   ├── ProgressBar (visual percentage)
│   ├── ProgressText (e.g., "24 / 156 files")
│   └── RecentFindingsList
│       └── FindingItem (×5 most recent)
│           ├── Severity Badge (color-coded)
│           ├── File + Issue Summary
│           └── Timestamp
├── ActionButtons (bottom)
│   ├── Cancel Analysis (secondary, destructive)
│   └── Minimize & Continue (secondary, navigates away while keeping analysis running)
└── Toast/Notification (if analysis completes while minimized)
```

### Visual Design Details

#### Header
- **Title:** Font-size `3xl`, weight 700, color `#FFFFFF`
- **Subtitle:** Font-size `base`, color `#A8A8A8`, font monospace, margin-top `space-2`
- **Elapsed Time:** Font-size `sm`, color `#707070`, positioned top-right

#### PipelineProgressVisual (Container)
- **Background:** `#1A1A1A`, border `1px solid #2D2D2D`, border-radius `rounded-lg`
- **Padding:** `space-8` all sides
- **Layout:** Horizontal flex, items centered, gap `space-6` between cards
- **On mobile (sm):** Stack vertically, gap `space-4`

#### PhaseCard
- **Container:** Width 22% (on md+), background `#252525`, border `2px solid #2D2D2D`, border-radius `rounded-base`, padding `space-4`
- **States:**
  - **Completed:** Background `#1A4D2E` (dark green), border `2px solid #10B981`, glow effect with box-shadow `0 0 12px rgba(16, 185, 129, 0.2)`
  - **In Progress:** Background `#4D3D1A` (dark amber), border `2px solid #F59E0B`, animation (see Interaction Patterns)
  - **Pending:** Background `#2D3A4D` (dark blue-gray), border `2px solid #2D2D2D`
- **Title:** Font-size `sm`, weight 600, color `#FFFFFF`, letter-spacing `tracking-wide`, all-caps, margin-bottom `space-3`
- **Status Icon:**
  - **Completed:** Unicode checkmark "✓", size `lg`, color `#10B981`
  - **In Progress:** Animated spinner or pulsing dot, color `#F59E0B`, size `lg`
  - **Pending:** Unfilled circle "◦", size `base`, color `#707070`
- **Status Text:** Font-size `xs`, color matching icon color, margin-top `space-2`

#### ConnectorLine
- **SVG line connecting phases horizontally**
- **Line color:** `#2D2D2D` (gray) for pending phases, `#10B981` (green) for completed phases, `#F59E0B` (amber) for in-progress
- **Stroke-width:** 2px
- **Animation:** For in-progress connection, animate dash pattern (marching ants effect, 1s loop)

#### ProgressDetailsPanel
- **Container:** Background `#1A1A1A`, border `1px solid #2D2D2D`, border-radius `rounded-lg`, padding `space-6`
- **Sections:**

  **Current Phase Label:**
  - Font-size `sm`, color `#A8A8A8`, weight 500, margin-bottom `space-2`
  - Text: e.g., "Phase: AI Analysis (3 of 4)"

  **Current File Info:**
  - Font-size `base`, weight 600, color `#FFFFFF`
  - Monospace for file path: color `#60A5FA`
  - File progress: e.g., "src/components/UserModal.vue (24 / 156 files)", color `#A8A8A8`, font-size `sm`

  **ProgressBar:**
  - **Container:** Background `#252525`, height `8px`, border-radius `rounded-full`, border `1px solid #2D2D2D`, overflow hidden
  - **Fill:** Background linear-gradient from `#3B82F6` to `#8B5CF6`, animated fill width (0 to 100%), transition `width 500ms ease-out`
  - **Percentage text (optional):** Right-aligned below bar, size `xs`, color `#A8A8A8`

  **RecentFindingsList:**
  - **Container:** Margin-top `space-6`, max-height `12rem`, overflow-y auto
  - **Finding Item:**
    - Layout: Row with gap `space-3`
    - **Severity Badge:** Pill-shaped, bg color matching severity, text `#FFFFFF`, size `xs`, weight 600, min-width `50px` (center-aligned)
    - **File + Issue:** Flex column, flex-grow 1
      - File: Monospace, size `sm`, weight 500, color `#60A5FA`
      - Issue summary: Size `sm`, color `#FFFFFF`, weight 400, margin-top `space-1`
    - **Timestamp:** Size `xs`, color `#707070`, right-aligned
    - **Divider:** Border-bottom `1px solid #2D2D2D` between items (except last)

#### ActionButtons (Bottom)
- **Layout:** Flex row, gap `space-3`, centered, margin-top `space-8`
- **Cancel Button (Secondary, Destructive):**
  - Background: `transparent`, border `1px solid #FF5E5E`
  - Text: `#FF5E5E`, weight 500
  - Hover: Background `rgba(255, 94, 94, 0.1)`, border color `#FF8A00`
  - Padding: `space-2` vertical, `space-4` horizontal
- **Minimize Button (Secondary):**
  - Background: `transparent`, border `1px solid #3B82F6`
  - Text: `#3B82F6`, weight 500
  - Hover: Background `rgba(59, 130, 246, 0.1)`
  - Padding: `space-2` vertical, `space-4` horizontal

### Interaction & Animation Details

**Pipeline Animation:**
- Phases progress: When backend emits event (e.g., "eslint_complete"), JavaScript updates phase status and triggers animations.
- **Phase completion animation:** Border color transitions from gray → green, background shifts to dark green tint, glow effect fades in (400ms ease-out).
- **Phase start animation:** Border color shifts from gray → amber, background to dark amber tint, pulsing glow starts (infinite 2s ease-in-out).

**Progress Bar:**
- Updates every 500ms as files are processed.
- Smooth width transition (500ms ease-out).
- If progress "jumps" (e.g., from 40% to 80%), animate smoothly anyway (no abrupt jump).

**Recent Findings List:**
- New findings appear at the top with a subtle fade-in animation (200ms ease-out).
- Max 5 items displayed. Older items fade out and are removed.
- Scroll auto-focuses to top if list grows beyond visible area.

**WebSocket or Server-Sent Events (SSE) Integration:**
- Backend emits progress updates every 1–2 seconds.
- Frontend subscribes to updates and reactively updates the UI.
- If connection drops, show a warning: "Connection interrupted. Retrying...", color `#F59E0B`, size `xs`.

### Minimize & Continue Behavior

- **User clicks "Minimize & Continue"** → Navigate to Dashboard.
- **Backend continues running in background.**
- **Frontend periodically polls** (every 5 seconds) the `/api/audit_runs/{run_id}` endpoint to check if analysis is complete.
- **When complete,** show a toast notification: "✓ Analysis complete! Refresh dashboard for latest findings.", color `#10B981`, position bottom-right, auto-dismiss after 5s or click to dismiss.

---

## View 3: Global Dashboard (Overview)

### Purpose
The main landing page after a complete scan. Executives and developers at a glance: How many issues? What severity? Which files are the worst offenders? What should I tackle first?

### Mental Model
"I see the full picture immediately. High-level metrics, aggregate trends, and actionable priorities."

### Layout Map

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Project: MyProject]    [Last Scan: 2024-01-15 14:32]   [Re-Audit] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  EXECUTIVE SYNTHESIS (AI-Generated Insights)                  │ │
│  │  ───────────────────────────────────────────────────────────  │ │
│  │  "This codebase has strong component architecture but shows  │ │
│  │   consistency gaps in error handling. Priority: implement    │ │
│  │   standardized try-catch patterns and centralize API error   │ │
│  │   handling."                                                 │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐   │
│  │ Total Issues     │ │ Critical Issues  │ │ A11y Defects     │   │
│  │ 128              │ │ 12               │ │ 23               │   │
│  │ ▼ 15 from prev   │ │ ▲ 3 from prev    │ │ ▼ 8 from prev    │   │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘   │
│                                                                     │
│  ┌───────────────────────────────────┐ ┌─────────────────────┐   │
│  │  Issues by Severity               │ │ Issues by Category  │   │
│  │  (Pie Chart)                      │ │ (Bar Chart)         │   │
│  │                                   │ │                     │   │
│  │        [13%]                      │ │ AI Issues    ●● 34  │   │
│  │       ╱       ╲                   │ │ ESLint      ●●● 67  │   │
│  │      │  HIGH   │  [25%]           │ │ A11y        ●● 23   │   │
│  │      │  28%    │                  │ │ API Calls   ●●● 4   │   │
│  │       ╲       ╱                   │ │                     │   │
│  │        [62%]                      │ │                     │   │
│  │      MEDIUM/LOW                   │ │                     │   │
│  └───────────────────────────────────┘ └─────────────────────┘   │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Worst Offenders (Files with Most Issues)                     │ │
│  │  ─────────────────────────────────────────────────────────── │ │
│  │                                                               │ │
│  │  1. UserModal.vue              ●●● 18 issues  [H:4 M:10 L:4] │ │
│  │  2. DataTable.vue              ●● 14 issues   [H:2 M:9 L:3]  │ │
│  │  3. APIService.js              ●●● 16 issues  [H:6 M:7 L:3]  │ │
│  │  4. FormValidator.js           ●● 12 issues   [H:1 M:8 L:3]  │ │
│  │  5. Dashboard.vue              ●●● 15 issues  [H:3 M:9 L:3]  │ │
│  │                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  [View All Files] [Export Report]                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Structure

```
Dashboard
├── Header
│   ├── Project Name (left)
│   ├── Last Scan Timestamp + Status (center)
│   └── Re-Audit Button (right)
├── ExecutiveSynthesisPanel
│   ├── Title
│   └── AI-Generated Summary Text (prose)
├── MetricsGrid (3 columns)
│   ├── MetricCard (×3)
│   │   ├── Label
│   │   ├── Large Number
│   │   └── TrendIndicator (▲ or ▼ + delta)
├── ChartsSection (2 columns)
│   ├── SeverityChart (Pie Chart)
│   │   ├── Title
│   │   └── Pie Chart with legend
│   └── CategoryChart (Bar Chart)
│       ├── Title
│       └── Bar Chart
├── WorstOffendersPanel
│   ├── Title
│   ├── TableView (5 rows)
│   │   └── Row
│   │       ├── Rank (1–5)
│   │       ├── File Name (clickable)
│   │       ├── Issue Count Badge
│   │       ├── Issue Severity Breakdown (H: M: L:)
│   │       └── Click Handler → Navigate to split-pane + select file
│   └── BottomActions
│       ├── View All Files Link
│       └── Export Report Button
└── Footer
    └── Last refreshed timestamp
```

### Visual Design Details

#### Header
- **Container:** Background `#1A1A1A`, border-bottom `1px solid #2D2D2D`, padding `space-6`, height `auto`
- **Layout:** Flex row, space-between
- **Project Name (Left):**
  - Font-size `xl`, weight 600, color `#FFFFFF`
- **Timestamp + Status (Center):**
  - Font-size `sm`, color `#A8A8A8`, weight 500
  - Status indicator (green dot + "Complete" or amber dot + "In Progress")
- **Re-Audit Button (Right):**
  - Background: `#3B82F6`, text `#FFFFFF`, weight 600
  - Padding: `space-2` vertical, `space-4` horizontal
  - Hover: Background `#60A5FA`
  - Border-radius: `rounded-base`

#### ExecutiveSynthesisPanel
- **Container:** Background `#1A1A1A`, border `1px solid #2D2D2D`, border-left `4px solid #8B5CF6` (accent), border-radius `rounded-lg`, padding `space-6`, margin-bottom `space-8`
- **Title:** Font-size `lg`, weight 600, color `#FFFFFF`, margin-bottom `space-3`
- **Summary Text:**
  - Font-size `base`, line-height `leading-relaxed`, color `#A8A8A8`
  - Weight 400
  - Max-width `65ch` for readability
  - Line spacing generous (relaxed leading for prose)

#### MetricsGrid
- **Container:** Display grid, grid-template-columns `repeat(auto-fit, minmax(220px, 1fr))`, gap `space-6`, margin-bottom `space-8`
- **MetricCard:**
  - **Container:** Background `#1A1A1A`, border `1px solid #2D2D2D`, border-radius `rounded-lg`, padding `space-6`
  - **Hover:** Border color → `#3B82F6`, box-shadow `--shadow-sm`
  - **Label:** Font-size `sm`, color `#A8A8A8`, weight 500, margin-bottom `space-2`
  - **Number:** Font-size `4xl`, weight 700, color `#FFFFFF`, font monospace, margin-bottom `space-2`
  - **Trend:**
    - Layout: Flex row, align-center, gap `space-1`
    - Icon: ▲ or ▼ (Unicode arrow)
    - Delta text: Font-size `sm`, weight 600
    - **If positive (increase):** Color `#10B981` (green, improvement for low counts, concern for high counts)
    - **If negative (decrease):** Color `#FF5E5E` (red, concern for high counts, improvement for low counts)
    - Contextual logic: High issues decreasing = good; total files increasing = context-dependent.

#### ChartsSection
- **Container:** Display grid, grid-template-columns `1fr 1fr`, gap `space-6`, margin-bottom `space-8`
- **On mobile (sm):** Single column

#### SeverityChart (Pie Chart)
- **Container:** Background `#1A1A1A`, border `1px solid #2D2D2D`, border-radius `rounded-lg`, padding `space-6`
- **Title:** Font-size `lg`, weight 600, color `#FFFFFF`, margin-bottom `space-4`
- **Pie Chart:**
  - Library: Recharts (Vue 3 integration)
  - Segments colored by severity:
    - High: `#FF5E5E`
    - Medium: `#FFB800`
    - Low: `#4ADE80`
  - Donut-style (inner radius 60%, outer radius 100%)
  - Legend below: Font-size `sm`, color `#A8A8A8`, item spacing `space-4`
  - Tooltip on hover: Show exact count and percentage
  - Animation: Segments rotate in on page load (1s ease-out)

#### CategoryChart (Bar Chart)
- **Container:** Background `#1A1A1A`, border `1px solid #2D2D2D`, border-radius `rounded-lg`, padding `space-6`
- **Title:** Font-size `lg`, weight 600, color `#FFFFFF`, margin-bottom `space-4`
- **Bar Chart:**
  - Library: Recharts
  - Categories: AI Issues, ESLint, Accessibility, API Calls
  - Bar colors: Use category colors (`--color-category-*`)
  - X-axis labels: Size `xs`, color `#707070`
  - Y-axis: Show counts, grid lines subtle (`#2D2D2D`)
  - Bars: Rounded caps on top
  - Tooltip: On hover, show category, count, and percentage
  - Animation: Bars scale up on page load (800ms ease-out)

#### WorstOffendersPanel
- **Container:** Background `#1A1A1A`, border `1px solid #2D2D2D`, border-radius `rounded-lg`, padding `space-6`, margin-bottom `space-8`
- **Title:** Font-size `lg`, weight 600, color `#FFFFFF`, margin-bottom `space-4`
- **Table (not a true HTML table, but a list styled as rows):**
  - Each row: Flex row, align-center, padding `space-4`, border-bottom `1px solid #2D2D2D`
  - Last row: No border-bottom
  - Hover: Background `#252525`, cursor pointer, transition 200ms
  - Columns (left to right):
    1. **Rank:** Width 40px, text-align center, font monospace, color `#A8A8A8`, weight 600
    2. **File Name:** Flex-grow 1, font monospace, size `sm`, weight 500, color `#60A5FA`, text-decoration underline on hover
    3. **Issue Count Badge:** Background matching severity, text `#FFFFFF`, font size `sm`, weight 600, min-width 60px, text-align center
    4. **Severity Breakdown:** Flex row, gap `space-2`, font-size `xs`, color `#A8A8A8`
       - Example: "H: 4 M: 10 L: 4"
       - Abbreviations in monospace
- **ClickHandler:** Clicking a row navigates to split-pane explorer and auto-selects that file (see View 4).

#### BottomActions
- **Layout:** Flex row, gap `space-4`, justify-end, margin-top `space-6`
- **View All Files Link:**
  - Text: "View All Files", color `#3B82F6`, weight 500, size `sm`
  - Hover: Color `#60A5FA`, text-decoration underline
  - Click: Navigate to split-pane explorer
- **Export Report Button:**
  - Background: `transparent`, border `1px solid #3B82F6`, text `#3B82F6`, weight 500
  - Padding: `space-2` vertical, `space-4` horizontal
  - Hover: Background `rgba(59, 130, 246, 0.1)`
  - Click: Trigger PDF/JSON export (backend generates, frontend downloads)

#### Footer
- **Text:** "Last refreshed: [timestamp]", font-size `xs`, color `#707070`, text-align right, margin-top `space-6`

### Data Aggregation Logic (Backend → Frontend)

**Executive Summary:**
- Endpoint: `GET /api/audit_runs/{run_id}/synthesis`
- Returns: `{ synthesis_text: "..." }`
- Fallback: If synthesis not available, show placeholder: "Analysis complete. Review findings below."

**Metrics:**
- Endpoint: `GET /api/audit_runs/{run_id}/metrics`
- Returns: `{ total_issues: 128, critical_count: 12, a11y_count: 23, trend_delta: { total: -15, critical: +3, a11y: -8 } }`

**Severity Breakdown:**
- Endpoint: `GET /api/audit_runs/{run_id}/severity_distribution`
- Returns: `{ high: 36, medium: 79, low: 13 }`

**Category Breakdown:**
- Endpoint: `GET /api/audit_runs/{run_id}/category_distribution`
- Returns: `{ ai_issues: 34, eslint: 67, accessibility: 23, api_calls: 4 }`

**Worst Offenders:**
- Endpoint: `GET /api/audit_runs/{run_id}/worst_offenders?limit=5`
- Returns: Array of files sorted by issue count, top 5 with severity breakdown

---

## View 4: Split-Pane Explorer (Core UX)

### Purpose
The heart of the interaction experience. Left sidebar (always-visible file list with search, sort, badges). Right pane (dynamic, loads file details on selection). This layout is inspired by Linear's issue sidebar + VS Code's explorer pane.

### Mental Model
"I scan the full list, find what matters, click a file, and see everything about it. Fast navigation, visual feedback at every step."

### Layout Map

```
┌──────────────────────────────────┬────────────────────────────────────────┐
│  FILES & ISSUES (Left Pane)      │  FILE DETAIL (Right Pane)              │
│  ──────────────────────────────  │  ────────────────────────────────────  │
│                                  │                                        │
│  [Search…]  [▼ Sort]  [↔ Filters]│ [UserModal.vue] [Menu]                 │
│                                  │                                        │
│  ┌─ ALERTS & ERRORS ────┐        │ ┌── Metrics Grid ──────────────┐       │
│  │ 23 critical issues   │        │ │ Methods: 8 │ Imports: 3    │       │
│  │ ▼ (collapsible)      │        │ │ A. Issues: 2 │ API Calls: 1 │       │
│  │                      │        │ └──────────────────────────────┘       │
│  │ UserModal.vue        │        │                                        │
│  │ ●●● 4 issues        │        │ [AI Issues] [ESLint] [A11y] [API] [+]  │
│  │ ┌─ HIGH ────────┐   │        │ ──────────────────────────────────     │
│  │ │ ✗ Prop valid  │   │        │                                        │
│  │ │ ✗ Missing ref │   │        │ 1. Missing prop validation             │
│  │ │ ✗ Unhandled   │   │        │    Severity: HIGH                      │
│  │ │   error       │   │        │    Files expect props but don't define  │
│  │ └───────────────┘   │        │    schema with Vue's prop validator.    │
│  │ ┌─ MEDIUM ──────┐   │        │                                        │
│  │ │ ! Type issue  │   │        │    File: UserModal.vue                 │
│  │ │ ! Ref unused  │   │        │    Line: 24                            │
│  │ └───────────────┘   │        │                                        │
│  │ ┌─ LOW ─────────┐   │        │    Code Snippet:                       │
│  │ │ → Info        │   │        │    22  export default {                │
│  │ │ → Comment     │   │        │    23    props: {                      │
│  │ │               │   │        │ >> 24      userId: String,   ← FOCUS  │
│  │ │               │   │        │    25      userName: String,           │
│  │ │               │   │        │    26    }                             │
│  │ │               │   │        │    27  }                               │
│  │ └───────────────┘   │        │                                        │
│  │                      │        │ 2. Unhandled promise rejection         │
│  │ DataTable.vue        │        │    ...                                 │
│  │ ●●● 2 issues        │        │                                        │
│  │ ┌─ HIGH ────────┐   │        │                                        │
│  │ │ ✗ WCAG: Alt   │   │        │                                        │
│  │ │   missing     │   │        │                                        │
│  │ │ ✗ Keyboard    │   │        │                                        │
│  │ │   nav issue   │   │        │                                        │
│  │ └───────────────┘   │        │                                        │
│  │                      │        │                                        │
│  │ >>> Scroll down...   │        │ [< Prev] [Next >]                      │
│  │                      │        │                                        │
│  └──────────────────────┘        │                                        │
│                                  │                                        │
└──────────────────────────────────┴────────────────────────────────────────┘
```

### Component Structure

```
SplitPaneExplorer
├── Header (shared across panes)
│   ├── Left section: Title (Optional "Files & Issues" or breadcrumb)
│   ├── Right section: [Collapse/Expand Sidebar Toggle] (mobile only)
│   └── Divider
│
├── LeftPane (FileExplorer)
│   ├── ControlsBar
│   │   ├── SearchInput (with clear button)
│   │   ├── SortDropdown
│   │   └── FilterButton (opens filter panel)
│   ├── FilterPanel (conditional slide-over)
│   │   ├── CheckboxGroup: Severity (High, Medium, Low, Info)
│   │   ├── CheckboxGroup: Category (AI Issues, ESLint, A11y, API)
│   │   ├── Toggle: "Files with issues only"
│   │   └── ApplyFilters / ClearFilters buttons
│   ├── FileTreeView (virtualized list for performance)
│   │   └── FileNode (repeating)
│   │       ├── CollapsibleHeader
│   │       │   ├── Filename (monospace, truncated)
│   │       │   ├── Issue Badge (count + severity color)
│   │       │   └── Expand/Collapse Icon (if has issues)
│   │       └── IssueCategoryGroup (nested, visible if expanded)
│   │           ├── SeverityCategory (High, Medium, Low, Info)
│   │           │   ├── Category Icon
│   │           │   ├── Issue Count
│   │           │   └── ExpandCollapse
│   │           └── IssueItem (if expanded)
│   │               ├── Icon (severity-specific)
│   │               ├── Issue Summary (truncated)
│   │               ├── Hover: Highlight in right pane
│   │               └── Click: Jump to issue in right pane
│   └── PaginationPlaceholder ("Scroll for more...")
│
├── Divider (vertical, draggable on desktop for pane resize)
│
└── RightPane (FileDetailView)
    ├── Header
    │   ├── File Name + Path
    │   ├── Breadcrumb or navigation (< / >)
    │   └── Menu (options, close)
    ├── MetricsGrid (see View 5 for details)
    ├── TabBar
    │   ├── Tab: AI Issues
    │   ├── Tab: ESLint Flags
    │   ├── Tab: Accessibility Defects
    │   ├── Tab: API Calls
    │   └── Tab: +More (if additional data exists)
    └── TabContent (see View 5 for detailed tab layout)
```

### Visual Design Details

#### LeftPane Container
- **Width:** 28% on md+, 100% on sm (with toggle to minimize)
- **Background:** `#0F0F0F` (primary background, distinct from secondary)
- **Border-right:** `1px solid #2D2D2D` (on md+)
- **Overflow:** Auto, vertical scrolling

#### ControlsBar
- **Padding:** `space-4` top/bottom/sides
- **Layout:** Flex column, gap `space-2`
- **Sticky:** Position sticky, top 0, z-index 10, background `#0F0F0F`

#### SearchInput
- **Width:** 100%, font-size `sm`
- **Placeholder:** "Search files & issues..."
- **Background:** `#1A1A1A`, border `1px solid #2D2D2D`
- **Padding:** `space-2` vertical, `space-3` horizontal
- **Border-radius:** `rounded-base`
- **Focus:** Border color → `#3B82F6`, box-shadow `0 0 0 3px rgba(59, 130, 246, 0.1)`
- **Clear Button (×):** Appears when input has text, positioned inside field on right, cursor pointer, color `#707070`

#### SortDropdown
- **Button:** Background `transparent`, border `1px solid #2D2D2D`, text `#A8A8A8`, size `sm`, weight 500
- **Dropdown Menu:** Background `#1A1A1A`, border `1px solid #2D2D2D`, border-radius `rounded-base`, shadow `--shadow-base`
- **Sort Options:**
  - By file name (A-Z)
  - By issue count (descending)
  - By highest severity
  - By category

#### FilterButton
- **Button:** Background `transparent`, border `1px solid #2D2D2D`, text `#A8A8A8`, size `sm`, weight 500, icon + text
- **On filter active:** Border color → `#3B82F6`, text → `#3B82F6` (visual indicator)

#### FilterPanel (Slide-over)
- **Position:** Absolute, right edge of left pane or full-screen on mobile
- **Width:** 250px (on md+), 100% (on sm)
- **Background:** `#1A1A1A`
- **Border:** `1px solid #2D2D2D`
- **Padding:** `space-4`
- **Animation:** Slide in from right (200ms ease-out)
- **Title:** "Filters", font-size `lg`, weight 600, margin-bottom `space-4`
- **CheckboxGroup:**
  - **Label:** Font-size `sm`, weight 500, color `#A8A8A8`, margin-bottom `space-2`
  - **Checkboxes (each):**
    - Container: Flex row, align-center, gap `space-2`, margin-bottom `space-2`, cursor pointer
    - Checkbox: Custom styled (not default HTML), width/height 16px, border `1px solid #2D2D2D`, checked: background `#3B82F6`, transition 150ms
    - Label: Font-size `sm`, color `#FFFFFF`, weight 400
- **Buttons (bottom):**
  - **Apply:** Background `#3B82F6`, text `#FFFFFF`, weight 600, width 100%, margin-top `space-4`, padding `space-2` vertical
  - **Clear:** Background `transparent`, border `1px solid #2D2D2D`, text `#A8A8A8`, weight 500, width 100%, margin-top `space-2`

#### FileTreeView (Virtualized List)
- **Container:** Flex column, flex-grow 1, overflow-y auto
- **Each FileNode:**
  - **CollapsibleHeader:**
    - Padding: `space-3` vertical, `space-4` horizontal
    - Hover: Background `#1A1A1A`, cursor pointer
    - Layout: Flex row, align-center, gap `space-2`
    - **Expand Icon:** Width 16px, transition 200ms (rotate 90° when expanded)
    - **Filename:** Font monospace, size `sm`, weight 500, color `#FFFFFF`, truncate (text-overflow ellipsis)
    - **Path Hint (optional):** Font-size `xs`, color `#707070`, weight 300 (appears on hover)
    - **Issue Badge:** Background color by severity (high: `#FF5E5E`, medium: `#FFB800`, low: `#4ADE80`, mixed: `#FF8A00`), text `#FFFFFF`, size `xs`, weight 600, min-width 30px, text-align center, border-radius `rounded-full`
    - **Active State:** Border-left `3px solid #3B82F6`, background `#1A1A1A`
  - **IssueCategoryGroup (nested, visible if expanded):**
    - Padding-left: `space-6` (indent)
    - **Category Subheader:** Font-size `xs`, weight 600, color matching category (e.g., `#FF5E5E` for HIGH), uppercase, letter-spacing `tracking-wide`, margin-top `space-2`
    - **IssueItem (nested further):**
      - Padding: `space-2` vertical, `space-3` horizontal
      - Hover: Background `#252525`, cursor pointer
      - Layout: Flex row, align-center, gap `space-2`
      - **Icon:** Unicode symbol (✗ for error, ! for warning, → for info), size `sm`, color matching severity
      - **Text:** Font-size `sm`, weight 400, color `#A8A8A8`, truncate
      - **Click Handler:** Highlights this issue in right pane (smooth scroll if needed)

#### Divider (Vertical)
- **Width:** 4px on desktop, `cursor: col-resize` when hovering
- **Background:** `#2D2D2D` on normal, `#3B82F6` on drag
- **Draggable:** JavaScript handles resize, min-width left pane: 200px, min-width right pane: 300px

#### RightPane Container
- **Width:** 72% on md+, hidden on sm unless toggled visible
- **Background:** `#0F0F0F`
- **Flex-grow:** 1
- **Overflow:** Auto

### Interaction Flows

**User Flow 1: Search & Filter**
1. User types in SearchInput.
2. Frontend filters file list in real-time (debounced 200ms).
3. Files matching search term or with matching issues remain visible, others fade out.
4. If no results, show placeholder: "No files match your search."

**User Flow 2: Sort Files**
1. User clicks SortDropdown.
2. Dropdown menu appears.
3. User selects a sort option.
4. File list re-orders (transition 300ms ease-out).

**User Flow 3: Apply Filters**
1. User clicks FilterButton.
2. FilterPanel slides in from the right.
3. User selects checkboxes (severity, category, etc.).
4. User clicks "Apply Filters".
5. FilterPanel slides out, file list updates (files not matching filters are hidden or grayed out).

**User Flow 4: Select a File**
1. User clicks on a file in the FileTreeView.
2. File node highlights (left border appears, background shifts to `#1A1A1A`).
3. Right pane loads the file detail view (see View 5).
4. Tab bar shows tabs for available sections (AI Issues, ESLint, etc.).
5. If file has no issues in a category, that tab is disabled or hidden.

**User Flow 5: Expand/Collapse Category**
1. User clicks expand icon on a file node or category.
2. Nested issues appear/disappear (animate height, opacity 200ms ease-out).
3. Icon rotates 90° (if expanding).

**User Flow 6: Resize Panes (Desktop)**
1. User clicks and drags the vertical divider.
2. Left pane shrinks, right pane expands (or vice versa).
3. On release, update local storage with new widths.
4. On next visit, restore saved widths.

### Mobile Behavior (< md breakpoint)

- **LeftPane:** Full-screen overlay initially hidden. Toggle button in header shows/hides it.
- **RightPane:** Full-screen, visible by default.
- **Divider:** Not visible on mobile.
- **Stacked Layout:** If user needs to compare, they can swipe between panes or use browser back/forward.

---

## View 5: File Detail View (Right Pane)

### Purpose
When a file is selected in the explorer, the right pane becomes a detailed analysis canvas. Metrics at the top, then tabbed sections for each issue category. Each issue displays severity, description, and the exact code snippet.

### Mental Model
"I selected a file. Now I see everything about it: how complex, what issues, where they are in the code, and what to fix."

### Layout Map

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  [< Back]  UserModal.vue  [Menu ↓]                             │
│  src/components/UserModal.vue                                  │
│                                                                │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ METRICS GRID                                              │ │
│  │ ─────────────────────────────────────────────────────── │ │
│  │  Methods: 8    │ Imports: 3    │ API Calls: 1             │ │
│  │  A. Issues: 2  │ L. Issues: 7  │ Complexity: 8/10         │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                │
│  [AI Issues]  [ESLint]  [Accessibility]  [API Calls]           │
│  ──────────────────────────────────────────────────────────   │
│                                                                │
│  AI Issues (2 findings)                                        │
│  ──────────────────────                                        │
│                                                                │
│  1. Missing prop validation                                   │
│     HIGH SEVERITY                                             │
│     The component accepts props but doesn't validate them...   │
│                                                                │
│     File: src/components/UserModal.vue                        │
│     Line: 24                                                  │
│                                                                │
│     Code:                                                     │
│     22  export default {                                      │
│     23    props: {                                            │
│ ──> 24      userId: String,   ← Issue here                   │
│     25      userName: String,                                 │
│     26    }                                                   │
│     27  }                                                     │
│                                                                │
│     [View in editor ↗]                                        │
│                                                                │
│  ───────────────────────────────────────────────────────────  │
│                                                                │
│  2. Unhandled async operation in lifecycle hook              │
│     HIGH SEVERITY                                             │
│     onMounted() contains a promise but no catch() handler...  │
│                                                                │
│     ...                                                       │
│                                                                │
│  [< Prev Issue]  [Next Issue >]                                │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Component Structure

```
FileDetailView
├── Header
│   ├── Navigation (< back, current file breadcrumb, next >)
│   ├── File Path (monospace, secondary)
│   └── Menu (three-dot dropdown)
├── MetricsGrid (6 items, responsive 2-3 columns)
│   └── MetricItem (×6)
│       ├── Label
│       ├── Value (large number)
│       └── Context (optional unit or status)
├── TabBar (sticky)
│   ├── Tab (×4-5: AI Issues, ESLint, Accessibility, API Calls, +More)
│   ├── Active indicator (underline, color `#3B82F6`)
│   └── Disabled state (if no issues in category)
└── TabContent (dynamic, switches per tab)
    └── IssueList
        ├── Section Header (count + category title)
        ├── IssueCard (repeating, for each issue)
        │   ├── Issue Number (1, 2, 3...)
        │   ├── Issue Title (h3)
        │   ├── Severity Badge
        │   ├── Description (prose)
        │   ├── Metadata (file path, line number)
        │   ├── CodeSnippet
        │   │   ├── Line numbers (on left)
        │   │   ├── Code text (monospace)
        │   │   ├── Highlight line (darker background)
        │   │   └── Optional line annotation (column position)
        │   └── Actions (View in editor, Copy snippet)
        └── PaginationFooter
            ├── Issue navigation (< prev | next >)
            └── Counter (Issue X of Y)
```

### Visual Design Details

#### Header
- **Container:** Background `#1A1A1A`, border-bottom `1px solid #2D2D2D`, padding `space-4`, sticky top
- **Layout:** Flex row, align-center, space-between
- **Left Section:**
  - **Back Button:** Background `transparent`, border `1px solid #2D2D2D`, text `<` symbol, small icon, color `#A8A8A8`
  - **File Breadcrumb:** Flex row, gap `space-2`, align-center
    - **Current filename:** Font monospace, size `lg`, weight 600, color `#FFFFFF`
    - **Path hint (on hover/click):** Tooltip shows full path
- **Right Section:**
  - **Menu Button:** Three dots, background `transparent`, border `1px solid #2D2D2D`, color `#A8A8A8`
  - **Menu Options:** Export findings, Copy file path, Open in terminal, etc.
- **Secondary Row (below):**
  - **Full Path:** Font monospace, size `xs`, color `#707070`, weight 400

#### MetricsGrid
- **Container:** Display grid, grid-template-columns `repeat(auto-fit, minmax(160px, 1fr))`, gap `space-4`, margin `space-6`, background `#1A1A1A`, padding `space-6`, border `1px solid #2D2D2D`, border-radius `rounded-lg`
- **MetricItem:**
  - **Container:** Flex column, align-start, gap `space-1`
  - **Label:** Font-size `xs`, color `#A8A8A8`, weight 500, uppercase, letter-spacing `tracking-wide`
  - **Value:** Font-size `2xl`, weight 700, color `#FFFFFF`, font monospace
  - **Context (optional):** Font-size `xs`, color `#707070`, weight 400

#### TabBar (Sticky)
- **Container:** Position sticky, top (below header), background `#1A1A1A`, border-bottom `1px solid #2D2D2D`, padding `space-4`, z-index 5
- **Tabs Container:** Flex row, gap `space-0` (tabs butt against each other)
- **Tab (each):**
  - **Container:** Padding `space-3` vertical, `space-4` horizontal, cursor pointer, position relative, transition 200ms
  - **Text:** Font-size `sm`, weight 600, color `#A8A8A8` (inactive), color `#FFFFFF` (active)
  - **Underline (active):** Position absolute, bottom 0, left 0, right 0, height 3px, background `#3B82F6`
  - **Disabled State:** Opacity 0.5, cursor `not-allowed`, color `#4B5563`
  - **Hover (enabled):** Background `rgba(255, 255, 255, 0.05)`, color `#FFFFFF`

#### TabContent Container
- **Padding:** `space-6`
- **Max-width:** Prose-friendly (e.g., 80ch for text)
- **Overflow:** Auto, height calculated to fit below header/tabs

#### IssueCard
- **Container:** Background `#1A1A1A`, border `1px solid #2D2D2D`, border-radius `rounded-lg`, padding `space-6`, margin-bottom `space-4`
- **Hover:** Border color → `#3B82F6`, box-shadow `0 0 0 3px rgba(59, 130, 246, 0.1)`, transition 200ms
- **Layout:** Flex column, gap `space-4`

**Issue Header Row:**
- Flex row, align-center, gap `space-3`
- **Issue Number:** Font monospace, size `base`, weight 600, color `#3B82F6`
- **Severity Badge:** Pill-shaped (h-full, px-3), background matching severity color, text `#FFFFFF`, weight 600, size `xs`, min-width 70px

**Issue Title (h3):**
- Font-size `lg`, weight 600, color `#FFFFFF`, line-height `leading-tight`

**Description:**
- Font-size `base`, line-height `leading-relaxed`, color `#A8A8A8`, max-width `70ch`
- Preserve line breaks and formatting where applicable

**Metadata Row:**
- Flex row, gap `space-4`, font-size `sm`, color `#707070`, weight 400
- **File path:** Font monospace, preceded by "📄"
- **Line number:** Preceded by "📍" or "#", clickable (triggers "View in editor" if IDE extension)

**CodeSnippet Container:**
- **Background:** `#0F0F0F` (darker than card), border `1px solid #2D2D2D`, border-radius `rounded-base`, overflow-x auto, margin-top `space-3`
- **Inner layout:** Flex row (line numbers on left, code on right)
- **Line Numbers:**
  - **Container:** Background `#252525`, padding `space-3` horizontal, border-right `1px solid #2D2D2D`, user-select none, min-width 50px
  - **Text:** Font monospace, size `sm`, weight 400, color `#707070`, text-align right
- **Code:**
  - **Container:** Padding `space-3` horizontal and vertical, flex-grow 1, background `#0F0F0F`, overflow-x auto
  - **Text:** Font monospace, size `sm`, weight 400, color `#FFFFFF`, white-space pre
  - **Highlight Line:** Background `#1A4D2E` (dark green tint, subtle) or `rgba(16, 185, 129, 0.15)`, mark-style border-left `3px solid #10B981`
  - **Syntax Highlighting (optional):** Apply secondary syntax colors (keywords, strings, comments in muted tones)

**Actions Row (below snippet):**
- Flex row, gap `space-3`, justify-end, margin-top `space-3`
- **View in Editor Link (if IDE context):**
  - Text: "View in editor ↗", color `#3B82F6`, font-size `sm`, weight 500, cursor pointer
  - Hover: Text-decoration underline
- **Copy Snippet Button:**
  - Icon: Copy icon, background `transparent`, border `1px solid #2D2D2D`, color `#A8A8A8`
  - Hover: Border color → `#3B82F6`, color → `#3B82F6`
  - On click: Copy to clipboard, show toast: "Copied!", color `#10B981`, auto-dismiss 2s

#### PaginationFooter
- **Container:** Flex row, align-center, justify-between, border-top `1px solid #2D2D2D`, padding-top `space-4`, margin-top `space-6`
- **Navigation Buttons:**
  - **< Previous:** Disabled if on first issue, background `transparent`, border `1px solid #2D2D2D`, text `#A8A8A8`
  - **Next >:** Disabled if on last issue, background `transparent`, border `1px solid #2D2D2D`, text `#A8A8A8`
  - Hover (if enabled): Border color → `#3B82F6`, color → `#3B82F6`, cursor pointer
- **Counter:** Font-size `sm`, color `#A8A8A8`, text-align center, e.g., "Issue 1 of 7"

### Tab-Specific Considerations

#### AI Issues Tab
- **Section Header:** Font-size `lg`, weight 600, color `#FFFFFF`, margin-bottom `space-4`
  - Subtitle: "High-level insights from LLM analysis", font-size `sm`, color `#A8A8A8`, weight 400
- **IssueCards:** Full rich descriptions, often multi-paragraph
- **Code snippets:** Contextual, may reference multiple sections

#### ESLint Flags Tab
- **Section Header:** "Code Quality & Best Practice Violations"
- **IssueCards:** Typically shorter descriptions, rule reference included
- **Optional ESLint Rule Link:** "Learn more: [rule name]", links to ESLint documentation

#### Accessibility Defects Tab
- **Section Header:** "WCAG Compliance & A11y Issues"
- **IssueCards:** Reference WCAG level (A, AA, AAA), suggest remediation
- **Relevant Code:** Often highlights missing attributes (alt, aria-label, role, etc.)

#### API Calls Tab
- **Section Header:** "External API & Network Calls"
- **IssueCards:** May not be "issues" per se, but observations
  - List of APIs called, endpoints, HTTP methods
  - Calls inside loops flagged as warnings
  - Missing error handling flagged as issues
- **IssueItem Layout (alternative):**
  - API method, endpoint, line number
  - Status: ✓ (safe), ⚠ (inside loop), ✗ (no error handler)

### Data Loading & Async States

**Loading State (when file selected):**
- Show skeleton/placeholder in right pane while fetching details
- Skeleton includes: header, metrics grid (gray bars), tab bar, empty content area
- Duration: ~300ms (or actual fetch time, whichever is longer)

**Error State (if file fetch fails):**
- Show error message: "Failed to load file details. Retry?", color `#FF5E5E`
- Retry button below message
- Keep file selected in left pane for context

**Empty State (if file has no issues):**
- Per tab: "No [category] issues found. Great work!", color `#10B981`
- Disable that tab or show a muted, clickable state

---

## View 6: Global Utilities (Search & Filtering)

### Purpose
Global command palette (Cmd+K / Ctrl+K) and persistent search bars enable quick navigation across the codebase. Users can filter by severity, category, or file across all files without entering the split-pane explorer.

### Mental Model
"I can search anything instantly. High-severity issues across the entire codebase, specific files, specific problems. Fast and always accessible."

### Command Palette (Modal)

#### Trigger
- Keyboard shortcut: `Cmd+K` (Mac) or `Ctrl+K` (Windows/Linux)
- Persistent shortcut hint in header or footer: "(Cmd+K)"

#### Layout

```
┌──────────────────────────────────────┐
│  Search Across Codebase              │
│  ──────────────────────────────────  │
│  [🔍 Type to search... ]              │
│                                      │
│  Recent:                             │
│  • UserModal.vue                     │
│  • DataTable.vue                     │
│                                      │
│  Or filter by:                       │
│  [🔴 High Issues] [🟡 Medium]        │
│  [⚙️ ESLint] [♿ A11y] [🔗 API]       │
│                                      │
│  Help: Type '/' for commands         │
│  Press Esc to close                  │
└──────────────────────────────────────┘
```

#### Component Structure

```
CommandPalette (Modal)
├── Backdrop (dark, semi-transparent, click to close)
├── Container
│   ├── SearchInput (auto-focused)
│   ├── ResultsList
│   │   ├── ResultCategory (Files, Issues, Commands)
│   │   └── ResultItem (repeating)
│   │       ├── Icon
│   │       ├── Title (with search term highlighted)
│   │       ├── Subtitle (metadata)
│   │       ├── Keyboard shortcut (if applicable)
│   │       └── Click handler
│   └── Footer
│       ├── Help text
│       └── Keyboard hints (↑↓ to navigate, Enter to select, Esc to close)
```

#### Visual Design Details

**Modal Container:**
- **Position:** Fixed, centered, overlay
- **Width:** 90% max-width 600px
- **Background:** `#1A1A1A`, border `1px solid #2D2D2D`, border-radius `rounded-lg`, shadow `--shadow-xl`
- **Animation:** Fade in + scale up (200ms ease-out)

**SearchInput:**
- **Padding:** `space-4` vertical and horizontal
- **Font:** Size `base`, weight 400, color `#FFFFFF`
- **Placeholder:** "Search files, issues, commands...", color `#707070`
- **Background:** Transparent (inherit from modal)
- **Border:** Bottom only, `1px solid #2D2D2D`
- **Focus:** No outline (already in focus), optional subtle glow
- **Icon (left):** 🔍 emoji or icon, size `lg`, color `#3B82F6`, margin-right `space-2`

**ResultsList:**
- **Padding:** `space-4`
- **Max-height:** 400px, overflow-y auto
- **Font-size:** `sm`

**ResultCategory (e.g., "Files", "Issues"):**
- **Header:** Font-size `xs`, weight 600, color `#A8A8A8`, uppercase, letter-spacing `tracking-wide`, margin-top `space-3`, margin-bottom `space-2`

**ResultItem:**
- **Padding:** `space-3`, border-radius `rounded-base`, cursor pointer, transition 150ms
- **Hover:** Background `#252525`, border `1px solid #3B82F6`
- **Active (keyboard selected):** Same as hover
- **Layout:** Flex row, align-center, gap `space-3`
- **Icon:** Width 20px, color category-dependent
- **Content (flex-grow):**
  - **Title:** Font-size `sm`, weight 500, color `#FFFFFF`
    - Search term highlighted: `background: #3B82F6`, `color: #FFFFFF`, `padding: 2px 4px`, `border-radius: rounded-sm`
  - **Subtitle:** Font-size `xs`, color `#707070`, weight 400, margin-top `space-1`
    - For files: file path
    - For issues: severity + category, line number
    - For commands: description
- **Shortcut (optional, right-aligned):** Font-size `xs`, color `#4B5563`, weight 500, e.g., "⏎ Enter"

**Footer:**
- **Padding:** `space-3` vertical and horizontal
- **Border-top:** `1px solid #2D2D2D`
- **Text:** Font-size `xs`, color `#707070`, weight 400
- **Help:** "↑↓ Navigate  ⏎ Select  Esc Close"

### Persistent Global Filter Bar (Optional, in Dashboard Header)

#### Purpose
Quick filter across all data without opening command palette.

#### Layout
```
┌────────────────────────────────────────────────────────┐
│ Filter by:  [🔴 High] [🟡 Medium] [🟢 Low] [ℹ️ Info]   │
│             [⚙️ ESLint] [♿ A11y] [🔗 API] [🧠 AI]      │
│             [Clear All Filters]                        │
└────────────────────────────────────────────────────────┘
```

#### Component
- **Layout:** Flex row, wrap, gap `space-2`, padding `space-4`, background `#1A1A1A`, border-bottom `1px solid #2D2D2D`
- **Filter Chip (each):**
  - Background: `transparent` (inactive) or `#3B82F6` (active)
  - Border: `1px solid #2D2D2D` (inactive) or `1px solid #3B82F6` (active)
  - Text: `#A8A8A8` (inactive) or `#FFFFFF` (active)
  - Weight: 500, size: `sm`
  - Padding: `space-1` vertical, `space-3` horizontal
  - Border-radius: `rounded-full` (pill-shaped)
  - Cursor: pointer
  - Transition: All 200ms ease-out
  - **On click:** Toggle active state, filter all visible sections

---

## Component Hierarchy

A complete tree of Vue components and their relationships:

```
App (root)
├── Navigation (header with logo, breadcrumb, Cmd+K hint)
│
├── Router Views (page-level components)
│   ├── HomePage
│   │   ├── RecentAuditsPanel
│   │   │   └── AuditCard (×N)
│   │   └── QuickStartSection
│   │       ├── ProjectPathInput
│   │       ├── BrowseButton
│   │       └── AnalyzeButton
│   │
│   ├── AnalyzingState
│   │   ├── PipelineProgressVisual
│   │   │   ├── PhaseCard (×4)
│   │   │   └── ConnectorLine (SVG)
│   │   ├── ProgressDetailsPanel
│   │   │   ├── ProgressBar
│   │   │   └── RecentFindingsList
│   │   │       └── FindingItem (×5)
│   │   └── ActionButtons
│   │
│   ├── Dashboard
│   │   ├── DashboardHeader
│   │   ├── ExecutiveSynthesisPanel
│   │   ├── MetricsGrid
│   │   │   └── MetricCard (×3)
│   │   ├── ChartsSection
│   │   │   ├── SeverityChart (Recharts Pie)
│   │   │   └── CategoryChart (Recharts Bar)
│   │   ├── WorstOffendersPanel
│   │   │   └── OffenderRow (×5)
│   │   └── DashboardFooter
│   │
│   ├── SplitPaneExplorer
│   │   ├── FileExplorer (Left Pane)
│   │   │   ├── ControlsBar
│   │   │   │   ├── SearchInput
│   │   │   │   ├── SortDropdown
│   │   │   │   └── FilterButton
│   │   │   ├── FilterPanel (conditional)
│   │   │   └── FileTreeView
│   │   │       └── FileNode (×N, virtualized)
│   │   │           ├── IssueCategory (×M, nested)
│   │   │           └── IssueItem (×K, nested, conditional)
│   │   ├── PaneDivider (draggable)
│   │   └── FileDetailView (Right Pane)
│   │       ├── FileDetailHeader
│   │       ├── MetricsGrid
│   │       │   └── MetricItem (×6)
│   │       ├── TabBar
│   │       │   └── Tab (×5)
│   │       └── TabContent
│   │           └── IssueList
│   │               ├── IssueCard (×N)
│   │               │   ├── IssueHeader
│   │               │   ├── IssueTitle
│   │               │   ├── IssueDescription
│   │               │   ├── CodeSnippet
│   │               │   └── ActionButtons
│   │               └── PaginationFooter
│   │
│   └── NotFound (404 fallback)
│
├── CommandPalette (global modal)
│   ├── SearchInput
│   ├── ResultsList
│   │   ├── ResultCategory
│   │   └── ResultItem (×N)
│   └── Footer
│
├── GlobalFilterBar (persistent, in Dashboard/SplitPane header)
│   └── FilterChip (×N, toggleable)
│
└── GlobalProviders
    ├── ThemeProvider (dark theme context)
    ├── ToastProvider (notifications)
    └── AuditDataProvider (global audit state)
```

---

## State Management & Data Flow

### Composition API Structure (Vue 3)

Each major view uses Composition API with composables for logic reusability:

```
Composables (shared logic):
├── useAuditData.js
│   ├── Fetch audit run metadata
│   ├── Store in reactive ref
│   └── Expose updateAuditData()
│
├── useFileExplorer.js
│   ├── Manage selected file, sort, filters
│   ├── Compute filtered file list
│   └── Expose selectFile(), applyFilter(), etc.
│
├── useCodeSnippet.js
│   ├── Fetch code for line range from backend
│   ├── Highlight target line
│   ├── Expose copySnippet(), etc.
│   └── Memoize snippets to avoid refetch
│
├── usePagination.js
│   ├── Track current page / current issue
│   ├── Expose nextPage(), prevPage()
│   └── Expose getItemIndex(), etc.
│
├── useSearch.js
│   ├── Debounced search input
│   ├── Filter files & issues
│   └── Expose searchQuery, results
│
└── useWebSocket.js
    ├── Connect to backend SSE/WebSocket
    ├── Listen for pipeline progress updates
    ├── Emit events on completion
    └── Expose connection status
```

### Global State (Pinia Store or Context API)

```
AuditStore (Pinia or Context):
├── State
│   ├── currentRunId
│   ├── projectName
│   ├── analysisStatus (idle, analyzing, complete, failed)
│   ├── auditData (metrics, issues, synthesis)
│   ├── selectedFileId
│   ├── theme (dark / light, default dark)
│   └── preferences (sidebar width, sort order, etc.)
│
├── Getters
│   ├── isAnalyzing()
│   ├── totalIssues()
│   ├── filesWithIssues()
│   └── worstOffenders()
│
└── Actions
    ├── startAnalysis(projectPath)
    ├── fetchAuditData(runId)
    ├── selectFile(fileId)
    ├── applyFilters(filters)
    └── setTheme(theme)
```

### API Endpoints (Backend Contract)

The Vue frontend communicates with Flask backend via these endpoints:

```
GET /api/audit_runs
  → List all audit runs (with project name, timestamp, status)

GET /api/audit_runs/{run_id}
  → Fetch full audit metadata (project, status, start/end time, file count)

GET /api/audit_runs/{run_id}/synthesis
  → Executive summary (AI-generated text)

GET /api/audit_runs/{run_id}/metrics
  → Aggregate metrics (total issues, critical count, etc.)

GET /api/audit_runs/{run_id}/severity_distribution
  → Count of issues by severity (high, medium, low, info)

GET /api/audit_runs/{run_id}/category_distribution
  → Count of issues by category (AI, ESLint, A11y, API)

GET /api/audit_runs/{run_id}/worst_offenders?limit=5
  → Top 5 files by issue count with breakdown

GET /api/audit_runs/{run_id}/files
  → List all files in the codebase (with metadata: path, issue count, severity)

GET /api/audit_runs/{run_id}/files/{file_id}
  → Fetch all issues for a specific file (all categories)

GET /api/audit_runs/{run_id}/files/{file_id}/code_snippet?start_line=X&end_line=Y
  → Fetch raw code snippet (used for rendering in detail view)

GET /api/audit_runs/{run_id}/search?q=query
  → Global search across files and issues (used by command palette)

POST /api/audit_runs/{run_id}/start_analysis
  → Trigger new analysis on a directory

GET /api/audit_runs/{run_id}/status
  → Poll for real-time progress (returns current phase, file, percentage)
```

### Data Flow Example: User Selects a File

1. **User clicks file in FileTreeView**
   - `selectFile(fileId)` is called in `useFileExplorer`
   - `selectedFileId` ref updates
   - Right pane switches to loading skeleton

2. **FileDetailView component mounted**
   - Watches `selectedFileId`
   - Calls `fetchFileDetails(selectedFileId)`
   - Sends `GET /api/audit_runs/{run_id}/files/{file_id}`

3. **Backend responds with file data**
   - File metadata (path, complexity, etc.)
   - All issues grouped by category

4. **Frontend renders tabs**
   - Tab bar populates with available categories
   - First tab (AI Issues) shown by default
   - Each tab renders IssueCard components

5. **User clicks on code snippet**
   - `useCodeSnippet` composable fetches raw code (if not cached)
   - Sends `GET /api/audit_runs/{run_id}/files/{file_id}/code_snippet?start_line=X&end_line=Y`
   - Code rendered with line numbers and highlight

---

## Interaction Patterns & Animations

### Micro-Interactions

**Hover States:**
- Cards lift slightly: `transform: translateY(-2px)`, transition 200ms
- Border color shifts to accent: `#2D2D2D` → `#3B82F6`
- Opacity change on secondary elements (reveal on hover)

**Loading States:**
- Skeleton placeholder: Gray bars with pulse animation (infinite, 1.5s ease-in-out)
- Spinner: Rotating animation, 1s per rotation, infinite

**Focus States:**
- Keyboard-navigated elements (inputs, buttons) show a subtle glow box-shadow
- No default outline; use custom box-shadow for accessibility

**Success States:**
- Checkmark icon with pulse animation (3 pulses, 300ms each)
- Toast notification fades in from bottom-right, auto-dismisses after 4s

**Error States:**
- Red highlight on affected element (border, background tint)
- Error message slides in below with shake animation (200ms)

### Page Transitions

**Route transitions (between views):**
- Fade out current view: opacity 0 → 1, 200ms
- Fade in new view: opacity 0 → 1, 200ms (overlapping)
- Preserve scroll position per route (restore on back)

**Tab switching (within FileDetailView):**
- Fade content out: opacity 1 → 0, 100ms
- Fade content in: opacity 0 → 1, 100ms (immediate after fade-out)
- No layout shift (content height pre-allocated)

### Animations for Complex Elements

**Pipeline Visualization (Analyzing state):**
- Phase cards: Enter with scale animation (0 → 1) staggered (150ms between each)
- Connector line: Draw animation (stroke-dasharray animation, 1s ease-out)
- Progress bar: Width changes smoothly (500ms ease-out)
- Status icons: Spin (for in-progress), pulse (for completed)

**Chart Animations (Dashboard):**
- Pie chart segments: Rotate in from center, staggered (100ms between)
- Bar chart bars: Scale up from baseline (600ms ease-out)
- Legend items: Fade in with text-align shift (300ms)

**File Tree (Split Pane):**
- Expand/collapse: Height animation (smooth unfold/fold, 200ms ease-out)
- Nested items: Stagger animation on expand (50ms between items)

**Code Snippet:**
- Highlight line: Fade in subtle glow (200ms), persist for 3s, then fade out
- Line numbers: Fade in on hover (100ms)

---

## Accessibility & Performance Considerations

### Accessibility (WCAG 2.1 Level AA)

**Keyboard Navigation:**
- Tab through all interactive elements in logical order
- Cmd+K triggers command palette from anywhere
- Esc closes modals, dropdowns, overlays
- Arrow keys navigate lists (FileTreeView, ResultsList in command palette)
- Enter selects, Space toggles checkboxes
- Escape dismisses any open menu/modal

**Screen Reader Support:**
- All icons paired with aria-label or within button elements with descriptive text
- Headings use proper hierarchy (h1, h2, h3)
- Form inputs have associated labels or aria-labels
- Color not sole indicator of state (always pair with icon or text)
- Live regions announce pipeline progress (aria-live="polite")

**Color Contrast:**
- All text meets WCAG AA minimum (4.5:1 on small text, 3:1 on large)
- Severity colors tested for color-blindness (avoid red/green-only distinction)

**Focus Management:**
- Visible focus indicator on all interactive elements (custom 3px box-shadow)
- Auto-focus on modal/dialog open (SearchInput in command palette)
- Return focus to trigger element on close

**Semantic HTML:**
- Use `<button>` for clickable actions, `<a>` for navigation
- Use `<nav>`, `<main>`, `<section>`, `<article>` for landmark regions
- Use `<table>` or semantic list structures for tabular data (not CSS grid for semantics)

### Performance Optimizations

**Code Splitting:**
- Each major view (HomePage, Dashboard, SplitPaneExplorer, etc.) lazy-loaded via router
- Command palette code loaded on demand

**Virtualization:**
- FileTreeView uses vue-virtual-scroller for large file lists (100+ files)
- RecentAuditsPanel on HomePage uses pagination or intersection observer for incremental loading

**Caching & Memoization:**
- `useCodeSnippet` caches fetched snippets by file_id + line range
- `useAuditData` caches API responses with stale-while-revalidate strategy
- Local storage persists sidebar width, sort preference, recent selections

**Debouncing & Throttling:**
- Search input debounced 300ms before fetching results
- Resize handler (pane divider) throttled 100ms
- Scroll handlers throttled 200ms

**Image & Asset Optimization:**
- Charts rendered as SVG (scalable, no image files needed)
- Icons as inline SVG or font icons (no HTTP requests)
- No large hero images; typography and color carry the design

**Bundle Size:**
- Vue 3 + Vite enables tree-shaking and code splitting
- Recharts included for charts (consider alternative if size-conscious)
- TailwindCSS (utility-first, minimal CSS footprint)

**Lazy Loading:**
- Right pane (FileDetailView) doesn't render until file selected
- FilterPanel rendered conditionally (hidden by default)
- Charts in Dashboard load data only when tab active

---

## Design System Summary

### Color Palette Quick Reference

| Element | Light | Dark | Notes |
|---------|-------|------|-------|
| Background Primary | #F5F5F5 | #0F0F0F | Base surface |
| Background Secondary | #EFEFEF | #1A1A1A | Cards, panels |
| Background Tertiary | #E5E5E5 | #252525 | Hover, subtle |
| Text Primary | #000000 | #FFFFFF | Body text |
| Text Secondary | #4A4A4A | #A8A8A8 | Metadata |
| Border | #D0D0D0 | #2D2D2D | Dividers |
| Severity High | #FF5E5E | #FF5E5E | Critical issues |
| Severity Medium | #FFB800 | #FFB800 | Warnings |
| Severity Low | #4ADE80 | #4ADE80 | Info, low priority |
| Accent Primary | #3B82F6 | #3B82F6 | CTAs, highlights |
| Status Success | #10B981 | #10B981 | Completed, passed |
| Status Error | #EF4444 | #EF4444 | Failed, error |

### Typography Quick Reference

| Element | Size | Weight | Color | Line Height |
|---------|------|--------|-------|-------------|
| h1 Page Title | 40px | 700 | Primary | 1.2 |
| h2 Section | 28px | 600 | Primary | 1.2 |
| h3 Subsection | 20px | 600 | Primary | 1.2 |
| Body | 16px | 400 | Secondary | 1.5 |
| Small | 14px | 400 | Tertiary | 1.5 |
| Tiny | 12px | 500 | Tertiary | 1.2 |
| Monospace (code) | 14px | 400 | Primary | 1.5 |

### Responsive Breakpoints

- **Mobile (xs):** 320px – 480px (stacked layout)
- **Tablet (sm):** 481px – 768px (stacked or single column)
- **Desktop (md):** 769px – 1024px (two-column split)
- **Widescreen (lg):** 1025px – 1440px (full two-column, generous padding)
- **Ultra-wide (xl):** 1441px+ (max-width containers for readability)

---

## Implementation Roadmap

**Phase 1: Foundation**
1. Set up Vite + Vue 3 + Tailwind CSS project structure
2. Define global CSS variables (colors, typography, spacing)
3. Create reusable atomic components (Button, Card, Input, Badge, etc.)

**Phase 2: Core Views**
1. HomePage (with RecentAudits and QuickStart)
2. AnalyzingState (with pipeline visualization)
3. Dashboard (with metrics, charts, worst offenders)

**Phase 3: Interaction & Details**
1. SplitPaneExplorer (file list + pane divider)
2. FileDetailView (tabs, code snippets, pagination)
3. Command Palette (global search)

**Phase 4: Polish & Performance**
1. Animations and micro-interactions
2. Accessibility audit and fixes
3. Performance profiling and optimization
4. Dark mode refinement (already planned)

**Phase 5: Integration**
1. Connect all views to Flask API endpoints
2. WebSocket/SSE for real-time pipeline updates
3. Error handling and retry logic
4. State management setup (Pinia)

---

## Conclusion

This blueprint provides a complete, world-class design specification for the Code Audit Librarian frontend. It draws inspiration from Linear, Vercel, and Supabase while being purpose-built for Vue.js code analysis.

**Key Design Principles:**
- Minimalist clarity without sacrificing functionality
- Dark theme optimized for developer comfort during long sessions
- Progressive information disclosure (summary → detail)
- Smooth, purposeful animations (not gratuitous)
- Accessibility from the ground up
- Performance-conscious (virtualization, lazy loading, caching)

**Ready for Implementation:** Hand this document to your AI coding agent with confidence. Every component, layout, color, and interaction is specified. No design ambiguity remains.

---

**Version:** 1.0  
**Date:** January 2025  
**Prepared for:** Code Audit Librarian Development Team
