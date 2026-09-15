# Accessible White–Blue Control Console Redesign

**Date:** 2026-09-15
**Status:** Proposed — approved visual direction; awaiting spec review
**Scope:** Browser UI only; no changes to ADB, WebSocket, authentication, device data contracts, or stream protocol.

## 1. Problem statement

The current UI combines two incompatible theme systems:

1. `static/css/glass.css` defines a dark glass interface with light foreground tokens and translucent dark surfaces.
2. `static/css/app-shell.css` applies a light white–blue interface.
3. Multiple templates, especially `templates/devices.html` and `templates/index.html`, apply dark-mode colors inline.

When a light surface inherits dark-mode text, placeholders, translucent backgrounds, or muted colors, foreground and background values become visually similar. This causes unreadable labels, console output, checkboxes, and device status text.

The redesign replaces this mixed styling model with one accessible, white–blue semantic token system.

## 2. Goals and acceptance criteria

| Goal | Acceptance criteria |
|---|---|
| Make every text surface readable | Normal text foreground/background combinations meet WCAG AA 4.5:1 or higher. |
| Remove theme collisions | `glass.css` is no longer loaded by any production page after the migration; no template has a hard-coded dark text/background color. |
| Make Wi‑Fi device connection easier | Pair and Connect are visually separate numbered cards with visible labels, 44px minimum inputs/buttons, helpers, submit feedback, and retryable errors. |
| Maintain familiar operations | Existing routes, IDs, forms, WebSocket handlers, ADB operations, keyboard mappings, and API contracts remain intact. |
| Present a coherent console | Desktop uses a navy sidebar + bright work surface; mobile uses a compact top app bar and bottom action navigation. |
| Handle empty/error states clearly | Each state has an icon, plain-language status, details where useful, and an actionable recovery path. |
| Be responsive and accessible | Verified at 375px, 768px, 1024px, and 1440px; keyboard focus is visible and logical; icon-only controls have labels. |

## 3. Chosen visual direction

### 3.1 Design personality

A calm, professional control console: bright work area, disciplined blue hierarchy, minimal motion, and technical data rendered clearly. It is neither glassmorphism nor a generic dark terminal.

### 3.2 Semantic token system

Only CSS custom properties may represent UI colors in application styles. Components reference semantic roles, never raw hex values.

```css
:root {
  /* Canvas and elevation */
  --color-canvas: #F6F9FC;
  --color-surface: #FFFFFF;
  --color-surface-subtle: #EEF5FC;
  --color-surface-raised: #FFFFFF;
  --color-border: #D7E2EE;
  --color-border-strong: #AFC3D8;

  /* Text */
  --color-text: #102A43;
  --color-text-secondary: #243B53;
  --color-text-muted: #486581;
  --color-text-inverse: #FFFFFF;
  --color-text-placeholder: #627D98;

  /* Brand and interaction */
  --color-primary: #0B74DE;
  --color-primary-hover: #075DB4;
  --color-primary-pressed: #054A8F;
  --color-primary-subtle: #E7F1FD;
  --color-focus: #0B74DE;

  /* Semantic states */
  --color-success: #0F7B46;
  --color-success-subtle: #E7F7EF;
  --color-warning: #9A5B00;
  --color-warning-subtle: #FFF4DB;
  --color-danger: #A61B3C;
  --color-danger-subtle: #FFF1F3;
  --color-info: #075DB4;
  --color-info-subtle: #E7F1FD;

  /* Navigation */
  --color-sidebar: #163A5F;
  --color-sidebar-hover: #1E4A75;
  --color-sidebar-active: #DCEEFF;
  --color-sidebar-text: #F7FBFF;
  --color-sidebar-muted: #C5D9EC;

  /* Shape, spacing and motion */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --shadow-card: 0 8px 20px rgba(16, 42, 67, 0.08);
  --transition-fast: 160ms ease-out;
}
```

The smallest body text must use `--color-text-muted`, not a lighter value. Placeholder text is supporting content only; it does not replace a visible label.

### 3.3 Typography and rhythm

- System font stack: `Inter, "Segoe UI", Arial, sans-serif`; it is fast, legible in Vietnamese, and requires no external font dependency.
- Type scale: 12 / 14 / 16 / 20 / 24 / 30px.
- Body text: minimum 16px on mobile, 1.5 line-height.
- Labels: 14px, 600 weight, `--color-text-secondary`.
- Page title: 24px, 700 weight, `--color-text`.
- Spacing system: 4 / 8 / 12 / 16 / 24 / 32 / 48px only.

## 4. Information architecture and page designs

### 4.1 Shared shell

| Viewport | Navigation | Content behavior |
|---|---|---|
| ≥1024px | Fixed 264px navy sidebar with icon + label items | Main canvas has 32px padding and maximum content width of 1440px. |
| 768–1023px | Collapsible sidebar | Main canvas has 24px padding. |
| <768px | Top app bar plus bottom nav for key routes; secondary actions in an overflow sheet | Main canvas has 16px gutters and no horizontal overflow. |

The active route uses a pale-blue filled item with navy text, plus a left accent strip. Sidebar icons and labels always appear together on desktop.

### 4.2 Login and password pages

- Centered 420px card on the pale-blue canvas.
- Clear product identifier, one sentence of purpose, and a single primary submit action.
- All fields have persistent labels, helper/error text, 44px height, and visible focus state.
- Password visibility control has an accessible name.

### 4.3 Device management page

The page follows a clear sequence:

1. **Connection guide** — collapsible info card with concise four-step Android Wireless Debugging instructions.
2. **Saved devices** — one row per unique endpoint; device name, endpoint, status badge, primary Connect button, and separate danger delete action with confirmation.
3. **Connect a new device** — two independent step cards:
   - **Step 1: Pair lần đầu:** Pair host, port, code, optional name, Save device checkbox, Pair button.
   - **Step 2: Kết nối thiết bị đã pair:** Host, port, optional name, Save device checkbox, Connect button.
4. **Connection feedback** — `role="status"` for progress/success and `role="alert"` for errors. Technical ADB detail appears in a readable monospace disclosure below a plain Vietnamese explanation and Retry action.
5. **Device facts** — four cards: Model, Android, Battery, Battery status. Empty state says what is missing and links the user to the connection action.

Rows must not duplicate an endpoint. The UI deduplicates saved endpoint rendering defensively even if a legacy runtime JSON file contains duplicates.

### 4.4 Android control console

- The content starts with an explicit selected-device status bar and reconnect state.
- Video/canvas stays dark by design (`#0B1220`) because it is media content, but all control UI around it remains light.
- A grouped command dock uses icon + visible label or `aria-label` with tooltip; all buttons are 44×44px minimum.
- Advanced controls are in labeled tabs/sheets, not visually mixed with primary navigation.
- Error/status banner uses semantic state colors and textual state, never color alone.

### 4.5 iOS page

- Same shared shell and surfaces.
- A truthful availability card: state, requirements, next action; no simulated connected state.
- iOS-specific implementation is not part of this UI migration.

## 5. Component contracts

| Component | Required behavior |
|---|---|
| `.ui-card` | White surface, visible border, consistent radius/elevation; no transparency. |
| `.ui-label` | Persistent visible label; text meets AA contrast. |
| `.ui-input` | 44px minimum height, white background, dark text, clear placeholder and blue 3px focus outline. |
| `.button-primary` | Blue surface with white text; hover/pressed/disabled variants use token values. |
| `.button-secondary` | White surface, border, navy text; no low-contrast ghost style. |
| `.button-danger` | Red subtle or solid variant; destructive action visually isolated. |
| `.status-banner` | Contains icon, state label, summary, and optional action. State remains understandable without color. |
| `.empty-state` | Icon, title, explanation, and relevant primary action. |
| `.data-fact` | Label in secondary text, value in primary text, stable fixed layout. |

## 6. Migration strategy

### Slice 1 — tokens and shared primitives

- Replace `app-shell.css` with the semantic theme foundation and primitives.
- Add a dedicated `control-console.css` for shared layout and component contracts.
- Stop loading `glass.css` from all migrated templates.
- Add CSS regression tests asserting that production templates do not load `glass.css` and that token/property invariants exist.

### Slice 2 — device management vertical path

- Convert `devices.html` to semantic classes; remove inline dark styles.
- Add readable feedback/empty states and defensive de-duplication display.
- Preserve form names, IDs, fetch endpoints, and submitted payloads.

### Slice 3 — Android control console

- Convert console shell, toolbar, dialogs, panels, and status states to semantic classes.
- Preserve element IDs and JavaScript event bindings.
- Keep only the media stage dark.

### Slice 4 — login, password, iOS and responsive refinement

- Convert remaining templates to the shared component contracts.
- Apply shared responsive navigation and focus treatment.

### Slice 5 — visual/accessibility QA and controlled rollout

- Run full tests, Ruff, static contrast token assertions, Browser console checks, screenshot QA at four viewport sizes, and keyboard/tab smoke tests.
- Use a QA listener with ADB keep-alive disabled.
- Restart production task only after QA passes; re-check health endpoint and visual route availability.

## 7. Error handling and non-goals

### Error handling

- API/ADB timeouts show: human explanation, endpoint involved, retry button, and expandable technical detail.
- An unreachable device never changes current selected device silently.
- Disabled buttons use `disabled`, reduced opacity, and an explanatory reason where applicable.

### Non-goals

- No change to pair/connect backend behavior.
- No persistent database migration.
- No synthetic iOS connection implementation.
- No third-party UI framework or external font payload.
- No public HTTPS topology change.

## 8. Test plan

| Layer | Verification |
|---|---|
| Unit/static | Tests confirm no legacy `glass.css` reference in production templates; check semantic tokens, no dark inline colors in migrated templates, and form labels/roles. |
| Existing suite | `pytest -q`. |
| Code quality | `ruff check .`, `ruff format --check .`, `git diff --check`. |
| Browser runtime | Login, device management, Android console, iOS page: no console errors; expected API status; live DOM uses new stylesheet. |
| Visual | Screenshots at 375, 768, 1024, 1440px; no clipped text, invisible labels, or horizontal overflow. |
| Keyboard/a11y | Tab order, visible focus, Escape behavior in dialogs, icon control names, and state announcements. |
| Production | Scheduled task restart only after QA; `GET /healthz` returns 200, then check `/login` and `/devices`. |

## 9. Rollback

Each vertical slice is a separate commit. Reverting the latest slice restores the prior verified state without altering ADB data or `saved_wifi_devices.json`. Production deployment remains a scheduled-task restart, so rollback is a task restart after a targeted Git revert.
