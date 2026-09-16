# Connection-first Android Console

**Date:** 2026-09-16
**Status:** Approved by Anh Nam — implement on `fix/console-offline-composition`
**Scope:** Android main console only (`templates/index.html`, console CSS, static regression tests). ADB, Scrcpy, Socket.IO, authentication, CSRF and device API contracts remain unchanged.

## Problem

The current main console presents a remote-phone frame, side keys, nav keys and zoom controls before a Scrcpy video stream is available. When ADB is offline, this produces a large blank device frame surrounded by controls, plus a disconnected status/log region. The control dock is also mixed into the navigation sidebar, making the sidebar long and visually dense.

## Goal

Make the remote-control workflow state-led:

1. **Before stream availability:** show a single clear connection recovery surface.
2. **After `screen_size`:** show the device canvas and its direct manipulation controls.
3. **Keep navigation, session actions and device identity separate from remote commands.**

## Information architecture

### Desktop ≥1024px

- **Left sidebar:** product/device identity, route actions (`Đổi máy`, iOS, password, logout). It contains no remote command grid or transport configuration.
- **Main command dock:** the existing `quick-dock` is moved into the main work area. Its element IDs and handlers remain unchanged. It wraps or scrolls as needed, leaving the sidebar stable.
- **Connection state card:** displayed in the media area until the first valid `screen_size` event.
- **Stream stage:** after readiness, display the phone frame, side keys, Android nav bar, resize handle and zoom controls.
- **Compact status line:** remains available below the media stage; it never becomes a large empty panel.

### Tablet/mobile

- Existing responsive mobile sidebar drawer behavior remains intact.
- The command dock is horizontally scrollable, retains 44px targets and is directly below the page edge.
- Connection recovery card fits within canvas gutters; no horizontal overflow.

## Connection state contract

`#consoleMain` receives one of the following classes through the existing inline console script:

| Class | Meaning | Visible UI |
|---|---|---|
| `connection-pending` | Page boot / socket connection in progress | Connection card with neutral copy; Retry and Change device actions. |
| `connection-error` | Socket / Scrcpy / ADB failure | Connection card with danger styling, readable exact detail, Retry and Change device actions. |
| `connection-ready` | First valid `screen_size` received | Phone stream frame and its direct controls; connection card hidden. |

`#connectionStatus` stays a polite live region and provides the title/summary. `#status` continues to receive every status message through the existing `st(message)` helper, but text is inserted with `textContent` rather than HTML interpolation.

## Recovery card

The card includes:

- semantic state icon (`aria-hidden`), title and plain Vietnamese explanation;
- the exact last connection detail in a dedicated `#statusText` text node;
- **Kết nối lại** (`#connectionRetry`) forwarding to the existing `#reconnect` handler;
- **Đổi máy** link to `/devices`;
- no fake device-online/stream state.

## Behavioral invariants

- Preserve all existing IDs, `data-*` attributes, forms, routes, static scripts, inline Socket.IO/Scrcpy control semantics and ADB actions.
- Preserve `#reconnect` as the canonical reconnect control. The new recovery button only calls its existing click handler.
- Do not change server Python, socket transport settings, auth/session logic, ADB serial, or `saved_wifi_devices.json`.
- Do not touch port 8000 during implementation or isolated QA.
- Keep 44px minimum interactive targets and visible focus styling.
- Do not add raw colours to templates; styles use existing semantic tokens. The active media stage remains dark.

## Regression and QA contract

1. Static tests must verify the command dock is a direct child of `#consoleMain`, not sidebar content.
2. Static tests must verify all existing remote-control DOM IDs and inline script bindings remain present.
3. Static tests must verify state classes/card IDs, recovery button forwarding contract and a safe `st()` implementation using `textContent`.
4. CSS tests must verify pending/error hide the phone-frame controls and ready hides the connection card.
5. Browser QA on an isolated listener at desktop/tablet/mobile must verify: no horizontal overflow; pending/error card is readable; no blank phone frame on connection failure; retry control is present; and console errors are captured.

## Non-goals

- No visual redesign of Devices, Login, Change Password or iOS pages.
- No ADB device recovery automation or backend change.
- No physical-device action in QA.
