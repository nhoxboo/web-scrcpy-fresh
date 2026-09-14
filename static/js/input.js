// ---- HID report descriptors -------------------------------------------------
// Boot-protocol keyboard: 8-byte report (1 modifier byte + 1 reserved +
// up to 6 simultaneously pressed key usage codes). Compatible with every
// Android version that supports UHID (Android 11+).
const UHID_KEYBOARD_DESCRIPTOR = new Uint8Array([
    0x05, 0x01,             // Usage Page (Generic Desktop)
    0x09, 0x06,             // Usage (Keyboard)
    0xA1, 0x01,             // Collection (Application)
    0x05, 0x07,             //   Usage Page (Keyboard)
    0x19, 0xE0,             //   Usage Min (224 — LCtrl)
    0x29, 0xE7,             //   Usage Max (231 — RGui)
    0x15, 0x00, 0x25, 0x01, //   Logical 0..1
    0x75, 0x01, 0x95, 0x08, //   8 bits of modifiers
    0x81, 0x02,             //   Input (Data,Var,Abs)
    0x95, 0x01, 0x75, 0x08, //   1 reserved byte
    0x81, 0x03,             //   Input (Const,Var,Abs)
    0x95, 0x06, 0x75, 0x08, //   6 keys, 8 bits each
    0x15, 0x00, 0x25, 0x65, //   Logical 0..101
    0x05, 0x07,             //   Usage Page (Keyboard)
    0x19, 0x00, 0x29, 0x65, //   Usage 0..101
    0x81, 0x00,             //   Input (Data,Array)
    0xC0,                   // End Collection
]);

// Mouse with relative X/Y as i16 + V wheel + H wheel (AC Pan).
// Report = 7 bytes:
//   [0]      buttons mask (5 bits)
//   [1..2]   dx (i16, little-endian)
//   [3..4]   dy (i16, little-endian)
//   [5]      vertical wheel (i8)
//   [6]      horizontal wheel (i8)
const UHID_MOUSE_DESCRIPTOR = new Uint8Array([
    0x05, 0x01,             // Usage Page (Generic Desktop)
    0x09, 0x02,             // Usage (Mouse)
    0xA1, 0x01,             // Collection (Application)
    0x09, 0x01,             //   Usage (Pointer)
    0xA1, 0x00,             //   Collection (Physical)
    0x05, 0x09,             //     Usage Page (Buttons)
    0x19, 0x01, 0x29, 0x05, //     Buttons 1..5
    0x15, 0x00, 0x25, 0x01,
    0x95, 0x05, 0x75, 0x01,
    0x81, 0x02,             //     Input (Data,Var,Abs)
    0x95, 0x01, 0x75, 0x03,
    0x81, 0x03,             //     3-bit padding
    0x05, 0x01,             //     Generic Desktop
    0x09, 0x30, 0x09, 0x31, //     X, Y
    0x16, 0x01, 0x80,       //     Logical Min -32767
    0x26, 0xFF, 0x7F,       //     Logical Max 32767
    0x75, 0x10, 0x95, 0x02,
    0x81, 0x06,             //     Input (Data,Var,Rel)
    0x09, 0x38,             //     Usage (Wheel)
    0x15, 0x81, 0x25, 0x7F, //     -127..127
    0x75, 0x08, 0x95, 0x01,
    0x81, 0x06,             //     Input (Data,Var,Rel)
    0x05, 0x0C,             //     Usage Page (Consumer)
    0x0A, 0x38, 0x02,       //     Usage (AC Pan)
    0x95, 0x01, 0x75, 0x08,
    0x81, 0x06,             //     Input (Data,Var,Rel)
    0xC0,                   //   End Collection
    0xC0,                   // End Collection
]);

// KeyboardEvent.code -> HID Usage ID for Keyboard/Keypad page (0x07).
// Spec: USB HID Usage Tables 1.12, section 10 (Keyboard/Keypad Page).
// Modifier keys live in HID_MODIFIER_BITS instead and toggle the byte 0
// of the boot keyboard report.
const HID_KEYBOARD_USAGE = {
    'KeyA': 0x04, 'KeyB': 0x05, 'KeyC': 0x06, 'KeyD': 0x07, 'KeyE': 0x08,
    'KeyF': 0x09, 'KeyG': 0x0a, 'KeyH': 0x0b, 'KeyI': 0x0c, 'KeyJ': 0x0d,
    'KeyK': 0x0e, 'KeyL': 0x0f, 'KeyM': 0x10, 'KeyN': 0x11, 'KeyO': 0x12,
    'KeyP': 0x13, 'KeyQ': 0x14, 'KeyR': 0x15, 'KeyS': 0x16, 'KeyT': 0x17,
    'KeyU': 0x18, 'KeyV': 0x19, 'KeyW': 0x1a, 'KeyX': 0x1b, 'KeyY': 0x1c,
    'KeyZ': 0x1d,
    'Digit1': 0x1e, 'Digit2': 0x1f, 'Digit3': 0x20, 'Digit4': 0x21,
    'Digit5': 0x22, 'Digit6': 0x23, 'Digit7': 0x24, 'Digit8': 0x25,
    'Digit9': 0x26, 'Digit0': 0x27,
    'Enter': 0x28, 'Escape': 0x29, 'Backspace': 0x2a, 'Tab': 0x2b,
    'Space': 0x2c, 'Minus': 0x2d, 'Equal': 0x2e, 'BracketLeft': 0x2f,
    'BracketRight': 0x30, 'Backslash': 0x31, 'Semicolon': 0x33,
    'Quote': 0x34, 'Backquote': 0x35, 'Comma': 0x36, 'Period': 0x37,
    'Slash': 0x38, 'CapsLock': 0x39,
    'F1': 0x3a, 'F2': 0x3b, 'F3': 0x3c, 'F4': 0x3d, 'F5': 0x3e,
    'F6': 0x3f, 'F7': 0x40, 'F8': 0x41, 'F9': 0x42, 'F10': 0x43,
    'F11': 0x44, 'F12': 0x45,
    'PrintScreen': 0x46, 'ScrollLock': 0x47, 'Pause': 0x48,
    'Insert': 0x49, 'Home': 0x4a, 'PageUp': 0x4b, 'Delete': 0x4c,
    'End': 0x4d, 'PageDown': 0x4e,
    'ArrowRight': 0x4f, 'ArrowLeft': 0x50, 'ArrowDown': 0x51, 'ArrowUp': 0x52,
    'NumLock': 0x53, 'NumpadDivide': 0x54, 'NumpadMultiply': 0x55,
    'NumpadSubtract': 0x56, 'NumpadAdd': 0x57, 'NumpadEnter': 0x58,
    'Numpad1': 0x59, 'Numpad2': 0x5a, 'Numpad3': 0x5b, 'Numpad4': 0x5c,
    'Numpad5': 0x5d, 'Numpad6': 0x5e, 'Numpad7': 0x5f, 'Numpad8': 0x60,
    'Numpad9': 0x61, 'Numpad0': 0x62, 'NumpadDecimal': 0x63,
    'IntlBackslash': 0x64, 'ContextMenu': 0x65,
};

// Generic Xbox-style HID gamepad descriptor. Recognised by Android's
// generic HID input service as InputDevice.SOURCE_GAMEPAD, so any cloud
// game / emulator that reads KeyEvent.KEYCODE_BUTTON_* + MotionEvent
// SOURCE_GAMEPAD will pick it up. Report layout (13 bytes per report):
//
//   bytes 0..2  : 17 buttons (1 bit each) + 7 bits padding
//                 bit  0: A (HID button 1) — W3C Standard Gamepad buttons[0]
//                 bit  1: B (button 2)        — buttons[1]
//                 bit  2: X (button 3)        — buttons[2]
//                 bit  3: Y (button 4)        — buttons[3]
//                 bit  4: L1 (button 5)       — buttons[4]
//                 bit  5: R1 (button 6)       — buttons[5]
//                 bit  6: L2 (button 7)       — buttons[6] (digital, also analog below)
//                 bit  7: R2 (button 8)       — buttons[7]
//                 bit  8: Select (button 9)   — buttons[8]
//                 bit  9: Start (button 10)   — buttons[9]
//                 bit 10: L3 (button 11)      — buttons[10]
//                 bit 11: R3 (button 12)      — buttons[11]
//                 bit 12: D-Pad Up (button 13)  — buttons[12]
//                 bit 13: D-Pad Down (button 14)— buttons[13]
//                 bit 14: D-Pad Left (button 15)— buttons[14]
//                 bit 15: D-Pad Right (button 16)— buttons[15]
//                 bit 16: Home (button 17)    — buttons[16]
//                 bits 17..23: padding
//   bytes 3..10 : 4 axes i16 LE (LX, LY, RX, RY), -32768..32767, +Y = down
//                 (W3C Standard Gamepad: axes[0]=LX, axes[1]=LY,
//                  axes[2]=RX, axes[3]=RY)
//   bytes 11..12: 2 triggers u8 (L2, R2), 0..255. Many Android games look
//                 at the digital button bits; some emulators want the
//                 analog value, so we send both.
const UHID_GAMEPAD_DESCRIPTOR = new Uint8Array([
    0x05, 0x01,                     // Usage Page (Generic Desktop)
    0x09, 0x05,                     // Usage (Game Pad)
    0xA1, 0x01,                     // Collection (Application)
    // 17 buttons
    0x05, 0x09,                     //   Usage Page (Button)
    0x19, 0x01,                     //   Usage Minimum (Button 1)
    0x29, 0x11,                     //   Usage Maximum (Button 17)
    0x15, 0x00, 0x25, 0x01,         //   Logical 0..1
    0x75, 0x01, 0x95, 0x11,         //   1 bit × 17
    0x81, 0x02,                     //   Input (Data,Var,Abs)
    // 7 bits padding
    0x75, 0x01, 0x95, 0x07,
    0x81, 0x03,                     //   Input (Const,Var,Abs)
    // 4 axes (i16)
    0x05, 0x01,                     //   Usage Page (Generic Desktop)
    0x09, 0x30, 0x09, 0x31,         //   Usage X, Usage Y
    0x09, 0x33, 0x09, 0x34,         //   Usage Rx, Usage Ry
    0x16, 0x00, 0x80,               //   Logical Min -32768
    0x26, 0xFF, 0x7F,               //   Logical Max 32767
    0x75, 0x10, 0x95, 0x04,         //   16 bits × 4
    0x81, 0x02,                     //   Input (Data,Var,Abs)
    // 2 triggers (u8, 0..255)
    0x05, 0x01,
    0x09, 0x32, 0x09, 0x35,         //   Usage Z, Usage Rz
    0x15, 0x00, 0x26, 0xFF, 0x00,   //   Logical 0..255
    0x75, 0x08, 0x95, 0x02,         //   8 bits × 2
    0x81, 0x02,
    0xC0,                           // End Collection
]);

// Cheap byte-array equality for the gamepad diff loop. Bigger than
// `Array.prototype.every` would inline, but this is hot path (called every
// animation frame, per gamepad) — staying allocation-free matters.
function _byteArraysEqual(a, b) {
    if (a === b) return true;
    if (!a || !b || a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) {
        if (a[i] !== b[i]) return false;
    }
    return true;
}

// Modifier keys map to bits in byte 0 of the boot keyboard report.
const HID_MODIFIER_BITS = {
    'ControlLeft': 0x01, 'ShiftLeft': 0x02, 'AltLeft': 0x04, 'MetaLeft': 0x08,
    'ControlRight': 0x10, 'ShiftRight': 0x20, 'AltRight': 0x40, 'MetaRight': 0x80,
};

class ScrcpyInput {
    constructor(callback, videoElement, width, height, debug = false, options = {}) {
        this.callback = callback
        this.width = width
        this.height = height
        this.debug = debug
        // useUhid: when true, mouse and keyboard are routed through UHID
        // (HID-over-AOA via scrcpy UHID_CREATE / UHID_INPUT control messages)
        // instead of inject_keycode + touch events. This gives a real cursor
        // + real keyboard on the device (works on the main display and on
        // Virtual Desktop / external displays alike), which is what makes
        // desktop-style UI usable.
        this.useUhid = !!options.useUhid;
        this.videoElement = videoElement;
        // Will be initialized after the video metadata arrives (we need a
        // valid socket/control connection too, since UHID_CREATE only makes
        // sense after the server is ready). See enableUhid().
        this._uhidReady = false;
        this._uhidKeyboardId = 1;
        this._uhidMouseId = 2;
        this._uhidMods = 0;            // current modifier byte
        this._uhidKeysPressed = [];    // up to 6 HID usage codes
        this._uhidButtons = 0;         // current mouse button mask
        // Gamepad UHID state. We reserve IDs 3..6 for up to 4 controllers so
        // the keyboard (1) and mouse (2) IDs stay stable. The actual UHID
        // device is only created when the corresponding browser-side Gamepad
        // first reports input, and destroyed on `gamepaddisconnected`.
        this._uhidGamepadBaseId = 3;
        this._uhidGamepadIds = [3, 4, 5, 6];
        this._uhidGamepadCreated = [false, false, false, false];
        this._uhidGamepadLastReport = [null, null, null, null];
        this._gamepadEnabled = false;
        this._gamepadPollHandle = null;
        this._gamepadConnHandler = null;
        this._gamepadDiscHandler = null;
        // Status callback (optional) — `(index, name, action)` where action
        // is 'connected' | 'disconnected' | 'ignored'. The UI uses this to
        // surface a toast / status-bar update.
        this._gamepadStatusCallback = options.gamepadStatusCallback || null;
        this._pointerLockOwner = null; // element that holds pointer lock
        // Mouse sensitivity (multiplier on browser movementX/Y deltas before
        // they are sent as UHID mouse reports). 1.0 = passthrough; <1 slows
        // the device cursor relative to the host mouse, >1 speeds it up.
        // The device's own pointer-speed setting in Android stacks on top
        // of this — adjust here first since it doesn't require touching the
        // device settings.
        this._uhidMouseSpeed = Number(options.uhidMouseSpeed);
        if (!Number.isFinite(this._uhidMouseSpeed) || this._uhidMouseSpeed <= 0) {
            this._uhidMouseSpeed = 1.0;
        }
        // Optional pointer ballistics: when on, movement is scaled
        // non-linearly so small motions stay slow (precision) while fast
        // motions get amplified (long throws), similar to Windows pointer
        // acceleration. Off by default — a flat multiplier is more
        // predictable for most users.
        this._uhidMouseAccel = !!options.uhidMouseAccel;
        // Carry sub-pixel residual across frames so a 0.5x slowdown on a
        // 1px move doesn't quietly truncate to 0.
        this._uhidScaleResidualX = 0;
        this._uhidScaleResidualY = 0;

        let mouseX = null;
        let mouseY = null;
        let leftButtonIsPressed = false;
        let rightButtonIsPressed = false;

        const isUhid = () => this.useUhid && this._uhidReady;

        // Kill the browser's native HTML5 drag-and-drop on the video. When
        // the user holds left-button and drags inside the <video> element,
        // Chromium/WebKit otherwise initiates an image-drag operation,
        // which (a) shows the "forbidden" 🚫 cursor since there's no drop
        // target, and (b) hijacks mousemove events from us so the touch
        // gesture sent to scrcpy stops mid-flight. Setting draggable=false
        // doesn't fully cover Safari, so we also preventDefault() on
        // dragstart and selectstart.
        try { videoElement.draggable = false; } catch (e) { /* ignore */ }
        const blockDrag = (ev) => { ev.preventDefault(); ev.stopPropagation(); };
        videoElement.addEventListener('dragstart', blockDrag);
        videoElement.addEventListener('selectstart', blockDrag);

        document.addEventListener('mousedown', (event) => {
            if (isUhid()) return; // UHID path handles its own mousedown
            const rect = videoElement.getBoundingClientRect();
            const local_x = event.clientX - rect.left;
            const local_y = event.clientY - rect.top;

            if (videoElement.contains(event.target)) {
                if (event.button === 0) {
                    leftButtonIsPressed = true;

                    mouseX = (local_x / (rect.right - rect.left)) * this.width;
                    mouseY = (local_y / (rect.bottom - rect.top)) * this.height;

                    let data = this.createTouchProtocolData(0, mouseX, mouseY, this.width, this.height, 0, 0, 65535);
                    this.callback(data);
                    // Suppress the native drag/select that the browser
                    // would otherwise trigger when the cursor moves while
                    // the button is held — same reason as the dragstart
                    // listener above. Must be in mousedown because that's
                    // the gesture's entry point.
                    event.preventDefault();
                } else if (event.button === 2) {
                    rightButtonIsPressed = true;

                    this.sendKeyCode(event, 0, 4);
                    event.preventDefault();
                }
            }
        });

        document.addEventListener('mouseup', (event) => {
            if (isUhid()) return;
            if (!leftButtonIsPressed) return;

            const rect = videoElement.getBoundingClientRect();
            const local_x = event.clientX - rect.left;
            const local_y = event.clientY - rect.top;

            if (event.button === 0) {
                leftButtonIsPressed = false;

                if (videoElement.contains(event.target)) {
                    mouseX = (local_x / (rect.right - rect.left)) * this.width;
                    mouseY = (local_y / (rect.bottom - rect.top)) * this.height;
                }

                let data = this.createTouchProtocolData(1, mouseX, mouseY, this.width, this.height, 0, 0, 0);
                this.callback(data);

            } else if (event.button === 2 && rightButtonIsPressed) {
                rightButtonIsPressed = false;

                this.sendKeyCode(event, 1, 4);
                event.preventDefault();
            }
        });

        // RAF-coalesced mousemove (same rationale as pointermove below).
        let pendingMouseEvent = null;
        let mouseRafScheduled = false;
        const flushMouse = () => {
            mouseRafScheduled = false;
            const event = pendingMouseEvent;
            pendingMouseEvent = null;
            if (!event || !leftButtonIsPressed) return;
            const rect = videoElement.getBoundingClientRect();
            const local_x = event.clientX - rect.left;
            const local_y = event.clientY - rect.top;
            mouseX = (local_x / (rect.right - rect.left)) * this.width;
            mouseY = (local_y / (rect.bottom - rect.top)) * this.height;
            const data = this.createTouchProtocolData(2, mouseX, mouseY, this.width, this.height, 0, 0, 65535);
            this.callback(data);
        };
        document.addEventListener('mousemove', (event) => {
            if (isUhid()) return;
            if (!leftButtonIsPressed) return;
            if (!videoElement.contains(event.target)) return;
            pendingMouseEvent = event;
            if (!mouseRafScheduled) {
                mouseRafScheduled = true;
                requestAnimationFrame(flushMouse);
            }
        });

        // Multi-touch support via Pointer Events (touch/pen only; mouse handled
        // by the mousedown/mouseup/mousemove listeners above). Each finger gets
        // a unique small integer pointer id that scrcpy maps to a separate
        // MotionEvent pointer, enabling pinch-zoom and multi-finger gestures.
        const toDevicePoint = (ev) => {
            const rect = videoElement.getBoundingClientRect();
            const localX = Math.max(0, Math.min(rect.width, ev.clientX - rect.left));
            const localY = Math.max(0, Math.min(rect.height, ev.clientY - rect.top));
            const x = (localX / Math.max(1, rect.width)) * this.width;
            const y = (localY / Math.max(1, rect.height)) * this.height;
            return { x, y, rect };
        };

        const touchPointers = new Map();   // browser pointerId -> scrcpy finger id (BigInt)
        const usedFingerIds = new Set();
        const MAX_FINGERS = 10;
        const allocFingerId = () => {
            for (let i = 0; i < MAX_FINGERS; i++) {
                if (!usedFingerIds.has(i)) {
                    usedFingerIds.add(i);
                    return BigInt(i);
                }
            }
            return 0n;
        };
        const releaseFingerId = (scrcpyId) => {
            usedFingerIds.delete(Number(scrcpyId));
        };
        const pointerPressure = (ev) => {
            // scrcpy expects pressure as int16 (0..65535). PointerEvent.pressure
            // is 0..1; 0.5 is the "no-force-info" neutral value.
            const p = typeof ev.pressure === 'number' && ev.pressure > 0 ? ev.pressure : 0.5;
            return Math.max(0, Math.min(65535, Math.round(p * 65535)));
        };

        videoElement.addEventListener('pointerdown', (ev) => {
            if (ev.pointerType !== 'touch' && ev.pointerType !== 'pen') return;
            try { videoElement.setPointerCapture(ev.pointerId); } catch (e) { /* ignore */ }
            const p = toDevicePoint(ev);
            const fid = allocFingerId();
            touchPointers.set(ev.pointerId, fid);
            const data = this.createTouchProtocolData(
                0, p.x, p.y, this.width, this.height, 0, 1, pointerPressure(ev), fid,
            );
            this.callback(data);
            ev.preventDefault();
        }, { passive: false });

        // Coalesce pointermove to one emit per animation frame (~60-120 Hz)
        // per pointer. Browsers fire pointermove at the input device's native
        // rate (often 200-1000 Hz on styluses / high-poll-rate mice), which
        // floods the WebSocket and adds end-to-end lag without making touch
        // tracking visibly smoother on the device.
        const pendingMoves = new Map();
        let rafScheduled = false;
        const flushMoves = () => {
            rafScheduled = false;
            for (const [pointerId, ev] of pendingMoves) {
                pendingMoves.delete(pointerId);
                const fid = touchPointers.get(pointerId);
                if (fid === undefined) continue;
                const p = toDevicePoint(ev);
                const data = this.createTouchProtocolData(
                    2, p.x, p.y, this.width, this.height, 0, 1, pointerPressure(ev), fid,
                );
                this.callback(data);
            }
        };
        videoElement.addEventListener('pointermove', (ev) => {
            if (ev.pointerType !== 'touch' && ev.pointerType !== 'pen') return;
            const fid = touchPointers.get(ev.pointerId);
            if (fid === undefined) return;
            // getCoalescedEvents() merges any sub-frame events the UA buffered;
            // we keep only the freshest one per pointer.
            pendingMoves.set(ev.pointerId, ev);
            if (!rafScheduled) {
                rafScheduled = true;
                requestAnimationFrame(flushMoves);
            }
            ev.preventDefault();
        }, { passive: false });

        const endPointer = (ev) => {
            if (ev.pointerType !== 'touch' && ev.pointerType !== 'pen') return;
            const fid = touchPointers.get(ev.pointerId);
            if (fid === undefined) return;
            touchPointers.delete(ev.pointerId);
            releaseFingerId(fid);
            const p = toDevicePoint(ev);
            const data = this.createTouchProtocolData(
                1, p.x, p.y, this.width, this.height, 0, 0, 0, fid,
            );
            this.callback(data);
            ev.preventDefault();
        };
        videoElement.addEventListener('pointerup', endPointer, { passive: false });
        videoElement.addEventListener('pointercancel', endPointer, { passive: false });

        videoElement.addEventListener('contextmenu', (event) => {
            event.preventDefault();
        });

        videoElement.addEventListener('wheel', (event) => {
            if (isUhid()) {
                // In UHID mode, wheel is delivered as a HID mouse report
                // with vertical/horizontal wheel bytes. See _uhidSendMouse.
                this._uhidSendWheel(event.deltaX, event.deltaY);
                event.preventDefault();
                return;
            }
            const hScroll = event.deltaX;
            const vScroll = event.deltaY;
            const deltaMode = event.deltaMode;
            const deltaZ = event.deltaZ;
            const clientX = event.clientX;
            const clientY = event.clientY;
            const button = event.button;

            const rect = videoElement.getBoundingClientRect();
            const relativeX = clientX - rect.left;
            const relativeY = clientY - rect.top;
            const width = rect.right - rect.left;
            const height = rect.bottom - rect.top;

            // switch (deltaMode) {
            //     case WheelEvent.DOM_DELTA_PIXEL:
            //         deltaModeValue.textContent = 'pixel';
            //         break;
            //     case WheelEvent.DOM_DELTA_LINE:
            //         deltaModeValue.textContent = 'row';
            //         break;
            //     case WheelEvent.DOM_DELTA_PAGE:
            //         deltaModeValue.textContent = 'page';
            //         break;
            //     default:
            //         deltaModeValue.textContent = 'unknown';
            // }
            let data = this.createScrollProtocolData(relativeX, relativeY, width, height, hScroll, vScroll, button);
            this.callback(data);
        });

        videoElement.addEventListener('keydown', async (event) => {
            if (isUhid()) {
                if (this._uhidKeyDown(event)) {
                    event.preventDefault();
                }
                return;
            }
            const androidKeyCode = this.mapToAndroidKeyCode(event);
            if (androidKeyCode !== null) {
                this.sendKeyCode(event, 0, androidKeyCode)
            } else {
                console.log(`key: ${event.code}, not mapped to android key code`);
            }

            if (event.ctrlKey && event.key === 'v') {
                try {
                    const clipboardData = await navigator.clipboard.readText();
                } catch (err) {
                    console.error('Failed to read clipboard contents: ', err);
                }
            }
        });

        videoElement.addEventListener('keyup', async (event) => {
            if (isUhid()) {
                if (this._uhidKeyUp(event)) {
                    event.preventDefault();
                }
                return;
            }
            const androidKeyCode = this.mapToAndroidKeyCode(event);
            if (androidKeyCode !== null) {
                this.sendKeyCode(event, 1, androidKeyCode)
            } else {
                console.log(`key: ${event.code}, not mapped to android key code`);
            }
        });

        // ---- UHID mouse handling --------------------------------------------
        // We use Pointer Lock so movementX/Y are real relative deltas (the
        // browser cursor disappears, mouse motion is captured). This matches
        // how every remote-desktop client (Parsec, Moonlight, NoMachine) does
        // mouse capture, and it lets the device-side cursor — driven by the
        // emulated USB HID mouse — move freely on the desktop UI.
        const uhidMouseDown = (event) => {
            if (!isUhid()) return;
            if (!videoElement.contains(event.target)) return;
            // First click: request pointer lock so subsequent mouse motion
            // is delivered as relative deltas. The button event itself is
            // also sent so the user can drag from outside-locked into a
            // click without losing the press.
            if (document.pointerLockElement !== videoElement) {
                try { videoElement.requestPointerLock(); } catch (e) { /* ignore */ }
            }
            const bit = this._uhidButtonBit(event.button);
            if (bit !== null) {
                this._uhidButtons |= bit;
                this._uhidSendMouse(0, 0, 0, 0);
            }
            event.preventDefault();
        };
        const uhidMouseUp = (event) => {
            if (!isUhid()) return;
            const bit = this._uhidButtonBit(event.button);
            if (bit !== null) {
                this._uhidButtons &= ~bit;
                this._uhidSendMouse(0, 0, 0, 0);
            }
            event.preventDefault();
        };
        // RAF-coalesce relative mouse deltas so we don't flood the WebSocket
        // on high-poll-rate mice. Accumulated dx/dy is sent as a single HID
        // report per frame.
        let uhidPendingDx = 0, uhidPendingDy = 0, uhidMoveScheduled = false;
        const flushUhidMove = () => {
            uhidMoveScheduled = false;
            if (uhidPendingDx === 0 && uhidPendingDy === 0) return;
            const rawDx = uhidPendingDx, rawDy = uhidPendingDy;
            uhidPendingDx = 0; uhidPendingDy = 0;
            // Apply user sensitivity. With acceleration on, also scale by a
            // mild non-linear curve based on the move speed within this RAF
            // tick (~16ms): big sweeps amplify, fine adjustments stay 1:1.
            const speed = this._uhidMouseSpeed;
            let sx = rawDx * speed, sy = rawDy * speed;
            if (this._uhidMouseAccel) {
                const mag = Math.hypot(rawDx, rawDy);
                // Curve: 1.0 at mag<=4 (precision zone), grows up to ~2.0 at
                // mag>=40. Tunable; keeps low-speed feel intact.
                const accel = 1 + Math.min(1, Math.max(0, (mag - 4) / 36));
                sx *= accel;
                sy *= accel;
            }
            // Preserve sub-pixel residue so slow drags stay smooth.
            sx += this._uhidScaleResidualX;
            sy += this._uhidScaleResidualY;
            const dx = Math.trunc(sx);
            const dy = Math.trunc(sy);
            this._uhidScaleResidualX = sx - dx;
            this._uhidScaleResidualY = sy - dy;
            if (dx === 0 && dy === 0) return;
            this._uhidSendMouse(dx, dy, 0, 0);
        };
        const uhidMouseMove = (event) => {
            if (!isUhid()) return;
            if (document.pointerLockElement !== videoElement) return;
            uhidPendingDx += event.movementX || 0;
            uhidPendingDy += event.movementY || 0;
            if (!uhidMoveScheduled) {
                uhidMoveScheduled = true;
                requestAnimationFrame(flushUhidMove);
            }
        };
        videoElement.addEventListener('mousedown', uhidMouseDown);
        document.addEventListener('mouseup', uhidMouseUp);
        document.addEventListener('mousemove', uhidMouseMove);
    }

    // ---- UHID public API -------------------------------------------------------

    /**
     * Register HID keyboard + mouse devices with the scrcpy server. Must be
     * called after the control socket is up. Idempotent: subsequent calls
     * with the same useUhid flag are no-ops.
     */
    enableUhid() {
        if (!this.useUhid || this._uhidReady) return;
        this.sendUhidCreate(
            this._uhidKeyboardId, 0x18d1, 0x4ee0, 'web-scrcpy keyboard',
            UHID_KEYBOARD_DESCRIPTOR,
        );
        this.sendUhidCreate(
            this._uhidMouseId, 0x18d1, 0x4ee1, 'web-scrcpy mouse',
            UHID_MOUSE_DESCRIPTOR,
        );
        this._uhidReady = true;
    }

    /**
     * Update the UHID mouse sensitivity at runtime. Called by the toolbar
     * slider so the user can A/B test speeds without reconnecting.
     * Clamped to a safe range; values outside (0.05, 8) are sketchy.
     */
    setUhidMouseSpeed(speed) {
        const v = Number(speed);
        if (!Number.isFinite(v) || v <= 0) return;
        this._uhidMouseSpeed = Math.max(0.05, Math.min(8, v));
    }

    /** Toggle Windows-style pointer ballistics for UHID mouse moves. */
    setUhidMouseAccel(on) {
        this._uhidMouseAccel = !!on;
    }

    /** Tear down the HID devices (called when socket dies). */
    disableUhid() {
        if (!this._uhidReady) return;
        try { this.sendUhidDestroy(this._uhidKeyboardId); } catch (e) { /* ignore */ }
        try { this.sendUhidDestroy(this._uhidMouseId); } catch (e) { /* ignore */ }
        this._uhidReady = false;
        this._uhidMods = 0;
        this._uhidKeysPressed = [];
        this._uhidButtons = 0;
        try {
            if (document.pointerLockElement === this.videoElement) {
                document.exitPointerLock();
            }
        } catch (e) { /* ignore */ }
    }

    // ---- UHID gamepad public API ----------------------------------------------

    /**
     * Start listening for browser Gamepad events and poll their state every
     * animation frame. The poll loop diffs state vs. the last sent report
     * and only sends a UHID_INPUT when something changed (button toggled,
     * stick moved beyond deadzone, trigger moved). Per-frame poll is the
     * official way to read Gamepad state on the web — there is no event
     * for button/axis changes, just the connect/disconnect ones.
     *
     * Idempotent: calling twice in a row only attaches one set of listeners.
     */
    enableGamepadInput() {
        if (this._gamepadEnabled) return;
        if (typeof navigator === 'undefined' || typeof navigator.getGamepads !== 'function') {
            // Browser without Gamepad API (or HTTPS-restricted context that
            // disabled it). Surface to the caller so the UI can warn.
            if (this._gamepadStatusCallback) {
                try { this._gamepadStatusCallback(-1, '', 'unsupported'); } catch (e) { /* ignore */ }
            }
            return;
        }
        this._gamepadEnabled = true;
        const onConnect = (e) => {
            const gp = e.gamepad;
            if (!gp || gp.index < 0 || gp.index >= this._uhidGamepadIds.length) {
                if (this._gamepadStatusCallback) {
                    try { this._gamepadStatusCallback(gp ? gp.index : -1, gp ? gp.id : '', 'ignored'); } catch (err) { /* ignore */ }
                }
                return;
            }
            this._uhidEnsureGamepad(gp.index, gp.id || 'web-scrcpy gamepad');
            if (this._gamepadStatusCallback) {
                try { this._gamepadStatusCallback(gp.index, gp.id || '', 'connected'); } catch (err) { /* ignore */ }
            }
        };
        const onDisconnect = (e) => {
            const gp = e.gamepad;
            if (!gp || gp.index < 0 || gp.index >= this._uhidGamepadIds.length) return;
            this._uhidDestroyGamepad(gp.index);
            if (this._gamepadStatusCallback) {
                try { this._gamepadStatusCallback(gp.index, gp.id || '', 'disconnected'); } catch (err) { /* ignore */ }
            }
        };
        this._gamepadConnHandler = onConnect;
        this._gamepadDiscHandler = onDisconnect;
        window.addEventListener('gamepadconnected', onConnect);
        window.addEventListener('gamepaddisconnected', onDisconnect);
        // Some browsers (Chromium) only fire `gamepadconnected` after the
        // first input arrives, so we also do an immediate sweep — any
        // gamepad already plugged in is created now.
        try {
            const pads = navigator.getGamepads ? navigator.getGamepads() : [];
            for (let i = 0; i < pads.length && i < this._uhidGamepadIds.length; i++) {
                const gp = pads[i];
                if (gp && gp.connected) {
                    this._uhidEnsureGamepad(gp.index, gp.id || 'web-scrcpy gamepad');
                    if (this._gamepadStatusCallback) {
                        try { this._gamepadStatusCallback(gp.index, gp.id || '', 'connected'); } catch (err) { /* ignore */ }
                    }
                }
            }
        } catch (e) { /* ignore */ }
        const poll = () => {
            if (!this._gamepadEnabled) return;
            this._uhidPollGamepads();
            this._gamepadPollHandle = (typeof requestAnimationFrame === 'function')
                ? requestAnimationFrame(poll)
                : setTimeout(poll, 16);
        };
        poll();
    }

    /** Tear down the gamepad poll loop and any created UHID gamepad devices. */
    disableGamepadInput() {
        if (!this._gamepadEnabled) return;
        this._gamepadEnabled = false;
        if (this._gamepadPollHandle != null) {
            if (typeof cancelAnimationFrame === 'function') {
                try { cancelAnimationFrame(this._gamepadPollHandle); } catch (e) { /* ignore */ }
            }
            try { clearTimeout(this._gamepadPollHandle); } catch (e) { /* ignore */ }
            this._gamepadPollHandle = null;
        }
        if (this._gamepadConnHandler) {
            try { window.removeEventListener('gamepadconnected', this._gamepadConnHandler); } catch (e) { /* ignore */ }
            this._gamepadConnHandler = null;
        }
        if (this._gamepadDiscHandler) {
            try { window.removeEventListener('gamepaddisconnected', this._gamepadDiscHandler); } catch (e) { /* ignore */ }
            this._gamepadDiscHandler = null;
        }
        for (let i = 0; i < this._uhidGamepadIds.length; i++) {
            if (this._uhidGamepadCreated[i]) this._uhidDestroyGamepad(i);
        }
    }

    _uhidEnsureGamepad(index, displayName) {
        if (index < 0 || index >= this._uhidGamepadIds.length) return;
        if (this._uhidGamepadCreated[index]) return;
        const id = this._uhidGamepadIds[index];
        // VID 0x18d1 (Google) + PID 0x9400+index keeps each slot distinct so
        // the Android InputManager treats reconnects of a different physical
        // controller as a fresh device. The name is just for diagnostics.
        const safeName = String(displayName || 'web-scrcpy gamepad').slice(0, 64);
        this.sendUhidCreate(id, 0x18d1, 0x9400 + index, safeName, UHID_GAMEPAD_DESCRIPTOR);
        this._uhidGamepadCreated[index] = true;
        this._uhidGamepadLastReport[index] = null;
    }

    _uhidDestroyGamepad(index) {
        if (index < 0 || index >= this._uhidGamepadIds.length) return;
        if (!this._uhidGamepadCreated[index]) return;
        try { this.sendUhidDestroy(this._uhidGamepadIds[index]); } catch (e) { /* ignore */ }
        this._uhidGamepadCreated[index] = false;
        this._uhidGamepadLastReport[index] = null;
    }

    _uhidPollGamepads() {
        if (typeof navigator === 'undefined' || typeof navigator.getGamepads !== 'function') return;
        let pads;
        try {
            pads = navigator.getGamepads();
        } catch (e) {
            return;
        }
        if (!pads) return;
        for (let i = 0; i < pads.length && i < this._uhidGamepadIds.length; i++) {
            const gp = pads[i];
            if (!gp || !gp.connected) continue;
            if (!this._uhidGamepadCreated[i]) {
                this._uhidEnsureGamepad(i, gp.id || 'web-scrcpy gamepad');
            }
            const report = this._buildGamepadReport(gp);
            const prev = this._uhidGamepadLastReport[i];
            if (!prev || !_byteArraysEqual(prev, report)) {
                this.sendUhidInput(this._uhidGamepadIds[i], report);
                this._uhidGamepadLastReport[i] = report;
            }
        }
    }

    /**
     * Build a 13-byte HID gamepad report from a browser Gamepad. The W3C
     * Standard Gamepad button/axis layout is mapped one-to-one into the
     * report bits described above the descriptor. Non-standard mappings
     * fall back to the same indices, which is good enough for most pads.
     */
    _buildGamepadReport(gp) {
        const report = new Uint8Array(13);
        let buttons = 0;
        const btns = gp.buttons || [];
        for (let i = 0; i < 17 && i < btns.length; i++) {
            const b = btns[i];
            const pressed = (typeof b === 'object') ? !!b.pressed : !!b;
            if (pressed) buttons |= (1 << i);
        }
        report[0] = buttons & 0xff;
        report[1] = (buttons >>> 8) & 0xff;
        report[2] = (buttons >>> 16) & 0xff;
        const axes = gp.axes || [];
        const dv = new DataView(report.buffer);
        const axisToI16 = (v) => {
            const n = Number(v);
            if (!Number.isFinite(n)) return 0;
            const clamped = Math.max(-1, Math.min(1, n));
            const scaled = Math.round(clamped * 32767);
            return Math.max(-32768, Math.min(32767, scaled));
        };
        dv.setInt16(3, axisToI16(axes[0]), true);  // LX
        dv.setInt16(5, axisToI16(axes[1]), true);  // LY
        dv.setInt16(7, axisToI16(axes[2]), true);  // RX
        dv.setInt16(9, axisToI16(axes[3]), true);  // RY
        const triggerToU8 = (b) => {
            if (!b) return 0;
            const v = (typeof b === 'object') ? Number(b.value) : Number(b);
            if (!Number.isFinite(v)) return 0;
            return Math.max(0, Math.min(255, Math.round(v * 255)));
        };
        report[11] = triggerToU8(btns[6]); // L2 analog
        report[12] = triggerToU8(btns[7]); // R2 analog
        return report;
    }

    sendUhidCreate(id, vendorId, productId, name, descriptor) {
        // scrcpy UHID_CREATE control message (server v3.1+):
        //   u8 type=12 | u16 id | u16 vendor_id | u16 product_id |
        //   u8 name_len | name bytes (UTF-8) | u16 desc_len | desc bytes
        const nameBytes = new TextEncoder().encode(name);
        const buf = new ArrayBuffer(1 + 2 + 2 + 2 + 1 + nameBytes.length + 2 + descriptor.length);
        const view = new DataView(buf);
        let offset = 0;
        view.setUint8(offset, 12); offset += 1;
        view.setUint16(offset, id, false); offset += 2;
        view.setUint16(offset, vendorId, false); offset += 2;
        view.setUint16(offset, productId, false); offset += 2;
        view.setUint8(offset, nameBytes.length); offset += 1;
        new Uint8Array(buf, offset, nameBytes.length).set(nameBytes);
        offset += nameBytes.length;
        view.setUint16(offset, descriptor.length, false); offset += 2;
        new Uint8Array(buf, offset, descriptor.length).set(descriptor);
        this.callback(buf);
    }

    sendUhidInput(id, data) {
        // u8 type=13 | u16 id | u16 size | data bytes
        const buf = new ArrayBuffer(1 + 2 + 2 + data.length);
        const view = new DataView(buf);
        view.setUint8(0, 13);
        view.setUint16(1, id, false);
        view.setUint16(3, data.length, false);
        new Uint8Array(buf, 5, data.length).set(data);
        this.callback(buf);
    }

    sendUhidDestroy(id) {
        // u8 type=14 | u16 id
        const buf = new ArrayBuffer(3);
        const view = new DataView(buf);
        view.setUint8(0, 14);
        view.setUint16(1, id, false);
        this.callback(buf);
    }

    // ---- UHID keyboard internals ---------------------------------------------

    _uhidKeyDown(event) {
        const modBit = HID_MODIFIER_BITS[event.code];
        if (modBit !== undefined) {
            this._uhidMods |= modBit;
            this._uhidSendKeyboardReport();
            return true;
        }
        const usage = HID_KEYBOARD_USAGE[event.code];
        if (usage === undefined) return false;
        if (!this._uhidKeysPressed.includes(usage)) {
            if (this._uhidKeysPressed.length < 6) {
                this._uhidKeysPressed.push(usage);
            }
        }
        this._uhidSendKeyboardReport();
        return true;
    }

    _uhidKeyUp(event) {
        const modBit = HID_MODIFIER_BITS[event.code];
        if (modBit !== undefined) {
            this._uhidMods &= ~modBit;
            this._uhidSendKeyboardReport();
            return true;
        }
        const usage = HID_KEYBOARD_USAGE[event.code];
        if (usage === undefined) return false;
        const i = this._uhidKeysPressed.indexOf(usage);
        if (i >= 0) this._uhidKeysPressed.splice(i, 1);
        this._uhidSendKeyboardReport();
        return true;
    }

    _uhidSendKeyboardReport() {
        // Boot keyboard report: 8 bytes
        //   [0] modifiers, [1] reserved, [2..7] up to 6 key usage codes
        const r = new Uint8Array(8);
        r[0] = this._uhidMods & 0xff;
        for (let i = 0; i < 6; i++) {
            r[2 + i] = this._uhidKeysPressed[i] || 0;
        }
        this.sendUhidInput(this._uhidKeyboardId, r);
    }

    // ---- UHID mouse internals -------------------------------------------------

    _uhidButtonBit(button) {
        // Web button → HID button bit. Buttons are 1..5.
        switch (button) {
            case 0: return 0x01; // left
            case 1: return 0x04; // middle
            case 2: return 0x02; // right
            case 3: return 0x08; // back / X1
            case 4: return 0x10; // forward / X2
            default: return null;
        }
    }

    _uhidSendMouse(dx, dy, wheelV, wheelH) {
        // 7-byte mouse report:
        //   [0] buttons, [1..2] dx (i16 LE), [3..4] dy (i16 LE),
        //   [5] vertical wheel (i8), [6] horizontal wheel (i8)
        const clamp16 = (v) => Math.max(-32767, Math.min(32767, v | 0));
        const clamp8 = (v) => Math.max(-127, Math.min(127, v | 0));
        const r = new Uint8Array(7);
        const dv = new DataView(r.buffer);
        r[0] = this._uhidButtons & 0xff;
        dv.setInt16(1, clamp16(dx), true);
        dv.setInt16(3, clamp16(dy), true);
        dv.setInt8(5, clamp8(wheelV));
        dv.setInt8(6, clamp8(wheelH));
        this.sendUhidInput(this._uhidMouseId, r);
    }

    _uhidSendWheel(deltaX, deltaY) {
        // Browser wheel deltas are pixel-based and can be large (~100 per
        // notch). Compress to HID's ±127 range with sign preserved.
        const sign = (v) => (v > 0 ? 1 : v < 0 ? -1 : 0);
        // HID wheel "vertical" is positive = up (away from user), but
        // browser deltaY positive = scroll down. Invert so the device
        // scrolls in the natural direction.
        const wv = -sign(deltaY) * Math.min(127, Math.ceil(Math.abs(deltaY) / 40) || 1);
        const wh = sign(deltaX) * Math.min(127, Math.ceil(Math.abs(deltaX) / 40) || 1);
        this._uhidSendMouse(0, 0, wv, wh);
    }

    resizeScreen(width, height) {
        this.width = width;
        this.height = height;
    }

    mapToAndroidKeyCode(event) {
        const codeToAndroidKeyCode = {
            'KeyA': 29,  // KEYCODE_A
            'KeyB': 30,  // KEYCODE_B
            'KeyC': 31,  // KEYCODE_C
            'KeyD': 32,  // KEYCODE_D
            'KeyE': 33,  // KEYCODE_E
            'KeyF': 34,  // KEYCODE_F
            'KeyG': 35,  // KEYCODE_G
            'KeyH': 36,  // KEYCODE_H
            'KeyI': 37,  // KEYCODE_I
            'KeyJ': 38,  // KEYCODE_J
            'KeyK': 39,  // KEYCODE_K
            'KeyL': 40,  // KEYCODE_L
            'KeyM': 41,  // KEYCODE_M
            'KeyN': 42,  // KEYCODE_N
            'KeyO': 43,  // KEYCODE_O
            'KeyP': 44,  // KEYCODE_P
            'KeyQ': 45,  // KEYCODE_Q
            'KeyR': 46,  // KEYCODE_R
            'KeyS': 47,  // KEYCODE_S
            'KeyT': 48,  // KEYCODE_T
            'KeyU': 49,  // KEYCODE_U
            'KeyV': 50,  // KEYCODE_V
            'KeyW': 51,  // KEYCODE_W
            'KeyX': 52,  // KEYCODE_X
            'KeyY': 53,  // KEYCODE_Y
            'KeyZ': 54,  // KEYCODE_Z

            'Digit0': 7,   // KEYCODE_0
            'Digit1': 8,   // KEYCODE_1
            'Digit2': 9,   // KEYCODE_2
            'Digit3': 10,  // KEYCODE_3
            'Digit4': 11,  // KEYCODE_4
            'Digit5': 12,  // KEYCODE_5
            'Digit6': 13,  // KEYCODE_6
            'Digit7': 14,  // KEYCODE_7
            'Digit8': 15,  // KEYCODE_8
            'Digit9': 16,  // KEYCODE_9

            'Enter': 66,       // KEYCODE_ENTER
            'Backspace': 67,   // KEYCODE_DEL
            'Tab': 61,         // KEYCODE_TAB
            'Space': 62,       // KEYCODE_SPACE
            'Escape': 111,     // KEYCODE_ESCAPE
            'CapsLock': 115,   // KEYCODE_CAPS_LOCK
            'NumLock': 143,    // KEYCODE_NUM_LOCK
            'ScrollLock': 116, // KEYCODE_SCROLL_LOCK

            'ArrowUp': 19,     // KEYCODE_DPAD_UP
            'ArrowDown': 20,   // KEYCODE_DPAD_DOWN
            'ArrowLeft': 21,   // KEYCODE_DPAD_LEFT
            'ArrowRight': 22,  // KEYCODE_DPAD_RIGHT

            'ShiftLeft': 59,   // KEYCODE_SHIFT_LEFT
            'ShiftRight': 60,  // KEYCODE_SHIFT_RIGHT
            'ControlLeft': 113,// KEYCODE_CTRL_LEFT
            'ControlRight': 114,// KEYCODE_CTRL_RIGHT
            'AltLeft': 57,     // KEYCODE_ALT_LEFT
            'AltRight': 58,    // KEYCODE_ALT_RIGHT
            'MetaLeft': 117,   // KEYCODE_META_LEFT
            'MetaRight': 118,  // KEYCODE_META_RIGHT

            'Numpad0': 144,    // KEYCODE_NUMPAD_0
            'Numpad1': 145,    // KEYCODE_NUMPAD_1
            'Numpad2': 146,    // KEYCODE_NUMPAD_2
            'Numpad3': 147,    // KEYCODE_NUMPAD_3
            'Numpad4': 148,    // KEYCODE_NUMPAD_4
            'Numpad5': 149,    // KEYCODE_NUMPAD_5
            'Numpad6': 150,    // KEYCODE_NUMPAD_6
            'Numpad7': 151,    // KEYCODE_NUMPAD_7
            'Numpad8': 152,    // KEYCODE_NUMPAD_8
            'Numpad9': 153,    // KEYCODE_NUMPAD_9
            'NumpadEnter': 160,// KEYCODE_NUMPAD_ENTER
            'NumpadAdd': 157,  // KEYCODE_NUMPAD_ADD
            'NumpadSubtract': 156, // KEYCODE_NUMPAD_SUBTRACT
            'NumpadMultiply': 155, // KEYCODE_NUMPAD_MULTIPLY
            'NumpadDivide': 154,   // KEYCODE_NUMPAD_DIVIDE

            'F1': 131,  // KEYCODE_F1
            'F2': 132,  // KEYCODE_F2
            'F3': 133,  // KEYCODE_F3
            'F4': 134,  // KEYCODE_F4
            'F5': 135,  // KEYCODE_F5
            'F6': 136,  // KEYCODE_F6
            'F7': 137,  // KEYCODE_F7
            'F8': 138,  // KEYCODE_F8
            'F9': 139,  // KEYCODE_F9
            'F10': 140, // KEYCODE_F10
            'F11': 141, // KEYCODE_F11
            'F12': 142, // KEYCODE_F12

            'Back': 4,    // KEYCODE_BACK
            'Home': 3,    // KEYCODE_HOME
            'Menu': 82,   // KEYCODE_MENU
        };

        const androidKeyCode = codeToAndroidKeyCode[event.code];
        return androidKeyCode !== undefined ? androidKeyCode : null;
    }

    sendKeyCode(keyevent, action, keycode) {
        const capsLockState = keyevent.getModifierState('CapsLock');
        const numLockState = keyevent.getModifierState('NumLock');
        const scrollLockState = keyevent.getModifierState('ScrollLock');

        let metakey = 0;
        if (keyevent.shiftKey) {
            metakey |= 0x40;
        }
        if (keyevent.ctrlKey) {
            metakey |= 0x2000;
        }
        if (keyevent.altKey) {
            metakey |= 0x10;
        }
        if (keyevent.metaKey) {
            metakey |= 0x20000;
        }
        if (capsLockState) {
            metakey |= 0x100000;
        }
        if (numLockState) {
            metakey |= 0x200000;
        }
        // if(scrollLockState)
        // {
        //     metakey |= 0x400000;
        // }
        let data = this.createKeyProtocolData(action, keycode, keyevent.repeat, metakey);
        this.callback(data);
    }

    // Deprecated typo alias kept for backward compatibility with older callers.
    snedKeyCode(keyevent, action, keycode) {
        return this.sendKeyCode(keyevent, action, keycode);
    }

    rotateDevice() {
        // scrcpy ROTATE_DEVICE control message: single type byte (=11).
        // Tells the device to cycle its orientation lock (portrait <-> landscape).
        const buffer = new ArrayBuffer(1);
        new DataView(buffer).setUint8(0, 11);
        this.callback(buffer);
    }

    sendSetClipboard(text, paste = false) {
        // scrcpy SET_CLIPBOARD control message:
        //   [u8 type=9][i64 sequence][u8 paste][u32 length][bytes...]
        // sequence is for ACK_CLIPBOARD round-tripping; we don't track acks
        // so 0 is fine. paste=true asks the device to paste the text into
        // the focused field after copying.
        if (text == null) return;
        const enc = new TextEncoder();
        const bytes = enc.encode(text);
        // Server caps clipboard text at ~256k - 5; truncate defensively.
        const MAX = (1 << 18) - 5;
        const slice = bytes.length > MAX ? bytes.subarray(0, MAX) : bytes;
        const buf = new ArrayBuffer(1 + 8 + 1 + 4 + slice.length);
        const view = new DataView(buf);
        view.setUint8(0, 9);                 // TYPE_SET_CLIPBOARD
        // Sequence (i64 BE) — set to 0; we don't use ACK_CLIPBOARD.
        view.setBigInt64(1, 0n, false);
        view.setUint8(9, paste ? 1 : 0);
        view.setUint32(10, slice.length, false);
        new Uint8Array(buf, 14, slice.length).set(slice);
        this.callback(buf);
    }

    sendInjectText(text) {
        // scrcpy INJECT_TEXT control message:
        //   [u8 type=1][u32be byte_length][N utf8 bytes]
        // Used for general text input — Vietnamese diacritics, emoji,
        // anything an Android IME would normally produce. Special keys
        // (Enter, Backspace, arrow keys) still go through inject_keycode.
        // We chunk to 256 bytes to stay safely under scrcpy's per-message
        // text limit (server caps at 300 in scrcpy 3.x).
        if (!text) return;
        const enc = new TextEncoder();
        const bytes = enc.encode(text);
        const CHUNK = 256;
        for (let off = 0; off < bytes.length; off += CHUNK) {
            const slice = bytes.subarray(off, Math.min(off + CHUNK, bytes.length));
            const buf = new ArrayBuffer(1 + 4 + slice.length);
            const view = new DataView(buf);
            view.setUint8(0, 1);
            view.setUint32(1, slice.length, false);
            new Uint8Array(buf, 5).set(slice);
            this.callback(buf);
        }
    }

    createTouchProtocolData(action, x, y, width, height, actionButton, buttons, pressure,
                             pointerId = 0xfffffffffffffffdn) {
        // scrcpy touch control message (big-endian):
        //   u8 type (2) | u8 action | u64 pointer_id | i32 x | i32 y
        //   u16 w | u16 h | i16 pressure | i32 action_button | i32 buttons
        // pointer_id == -3 (0xffff..fd) is scrcpy's "virtual finger" id used for
        // single-touch / mouse-emulated input. For real multi-finger input we
        // pass small positive ids (0..9) so each finger is tracked separately.
        const type = 2;
        const buffer = new ArrayBuffer(1 + 1 + 8 + 4 + 4 + 2 + 2 + 2 + 4 + 4);
        const view = new DataView(buffer);
        let offset = 0;

        view.setUint8(offset, type); offset += 1;
        view.setUint8(offset, action); offset += 1;

        const pid = typeof pointerId === 'bigint' ? pointerId : BigInt(pointerId);
        view.setBigUint64(offset, pid, false); offset += 8;

        view.setInt32(offset, x, false); offset += 4;
        view.setInt32(offset, y, false); offset += 4;
        view.setUint16(offset, width, false); offset += 2;
        view.setUint16(offset, height, false); offset += 2;
        view.setInt16(offset, pressure, false); offset += 2;
        view.setInt32(offset, actionButton, false); offset += 4;
        view.setInt32(offset, buttons, false);

        return buffer;
    }

    createKeyProtocolData(action, keycode, repeat, metaState) {
        const type = 0; // key event

        const buffer = new ArrayBuffer(1 + 1 + 4 + 4 + 4);
        const view = new DataView(buffer);

        let offset = 0;

        view.setUint8(offset, type);
        offset += 1;

        view.setUint8(offset, action);
        offset += 1;

        view.setInt32(offset, keycode, false);
        offset += 4;
        view.setInt32(offset, repeat, false);
        offset += 4;
        view.setInt32(offset, metaState, false);

        return buffer;
    }

    createScrollProtocolData(x, y, width, height, hScroll, vScroll, button) {
        const type = 3; // scroll event

        const buffer = new ArrayBuffer(1 + 4 + 4 + 2 + 2 + 2 + 2 + 4);
        const view = new DataView(buffer);

        let offset = 0;
        view.setUint8(offset, type);
        offset += 1;

        view.setInt32(offset, x, false);
        offset += 4;
        view.setInt32(offset, y, false);
        offset += 4;
        view.setUint16(offset, width, false);
        offset += 2;
        view.setUint16(offset, height, false);
        offset += 2;

        view.setInt16(offset, hScroll, false);
        offset += 2;
        view.setInt16(offset, vScroll, false);
        offset += 2;

        view.setInt32(offset, button, false);

        return buffer;
    }

    createScreenProtocolData(action) {
        const type = 4; // Screen off/on event

        const buffer = new ArrayBuffer(1 + 1);
        const view = new DataView(buffer);

        let offset = 0;
        view.setUint8(offset, type);
        offset += 1;

        view.setUint8(offset, action);

        return buffer;
    }

    createPowerProtocolData(action) {
        const type = 7; // Screen Power off/on event

        const buffer = new ArrayBuffer(1 + 1);
        const view = new DataView(buffer);

        let offset = 0;
        view.setUint8(offset, type);
        offset += 1;

        view.setUint8(offset, action);

        return buffer;
    }

    add_debug_item(text) {
        const p = document.createElement('p');
        p.textContent = text;
        const span = document.createElement('span');
        span.textContent = '0';
        p.appendChild(span);
        document.body.appendChild(p);
        return span;
    }

    screen_on_off(action) {
        let data = null;
        data = this.createScreenProtocolData(action);
        this.callback(data)
    }
}


// --- Drag & Drop ---
const dropZone = document.getElementById('dropZone');
const mainContent = document.querySelector('.main-content');

if (mainContent && dropZone) {
    mainContent.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.display = 'flex';
    });
    mainContent.addEventListener('dragleave', (e) => {
        // Only hide if we actually leave the container (not its children)
        if (!mainContent.contains(e.relatedTarget)) {
            dropZone.style.display = 'none';
        }
    });
    mainContent.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.display = 'none';
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            const formData = new FormData();
            formData.append('file', file);
            
            const isApk = file.name.toLowerCase().endsWith('.apk');
            const url = isApk ? '/api/install' : '/api/push';
            
            if(window.showStatus) window.showStatus(isApk ? 'Đang cài đặt APK...' : 'Đang tải file lên...');
            fetch(url, { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    if(window.showStatus) window.showStatus(data.message || (isApk ? 'Cài đặt thành công' : 'Upload thành công'));
                })
                .catch(err => {
                    if(window.showStatus) window.showStatus('Lỗi: ' + err);
                });
        }
    });
}

// --- Keymapping ---
// NOTE: every top-level `const`/`let` here shares the SAME global lexical scope
// as the inline <script> in templates/index.html. A name declared in both files
// is a hard SyntaxError ("Identifier 'x' has already been declared") that kills
// the ENTIRE inline script block — no socket, no video, no controls. Keep every
// binding in this file prefixed `km*` so it can never collide with the panel's
// own variables. See the `hotkeyBtn` incident (fixed 2026-08-27).
let keymapMode = false;
let keymapNodes = JSON.parse(localStorage.getItem('scrcpy_keymaps') || '[]');
const keymapOverlay = document.getElementById('keymapOverlay');
const kmHotkeyBtn = document.getElementById('hotkeyConfig');


function renderKeymaps() {
    if (!keymapOverlay) return;
    keymapOverlay.innerHTML = `
       <div style="position:absolute; top: 10px; left: 50%; transform: translateX(-50%); background:rgba(0,0,0,0.8); color:#fbbf24; padding:8px 16px; border-radius:20px; font-family:sans-serif; font-size:0.85rem; font-weight:bold; border:1px solid #fbbf24; box-shadow:0 4px 12px rgba(0,0,0,0.5);">
         <i class="fa-solid fa-pen-ruler"></i> CHẾ ĐỘ GÁN PHÍM: Click vào màn hình để thêm phím. Bấm "Gán phím" lần nữa để lưu.
       </div>
    `;
    keymapNodes.forEach((node, i) => {
        const el = document.createElement('div');
        el.style.position = 'absolute';
        el.style.left = node.x * 100 + '%';
        el.style.top = node.y * 100 + '%';
        el.style.transform = 'translate(-50%, -50%)';
        el.style.width = '30px';
        el.style.height = '30px';
        el.style.borderRadius = '50%';
        el.style.background = 'rgba(236, 72, 153, 0.8)';
        el.style.border = '2px solid #fff';
        el.style.color = '#fff';
        el.style.display = 'flex';
        el.style.alignItems = 'center';
        el.style.justifyContent = 'center';
        el.style.fontWeight = 'bold';
        el.style.fontSize = '12px';
        el.style.zIndex = '95';
        el.innerText = node.key.toUpperCase();
        
        if (keymapMode) {
            el.style.cursor = 'pointer';
            el.onclick = (e) => {
                e.stopPropagation();
                keymapNodes.splice(i, 1);
                renderKeymaps();
            };
        }
        keymapOverlay.appendChild(el);
    });
}

if (kmHotkeyBtn && keymapOverlay) {
    kmHotkeyBtn.addEventListener('click', () => {
        keymapMode = !keymapMode;
        if (keymapMode) {
            keymapOverlay.style.display = 'block';
            kmHotkeyBtn.classList.add('active');
            renderKeymaps();
        } else {
            keymapOverlay.style.display = 'none';
            kmHotkeyBtn.classList.remove('active');
            localStorage.setItem('scrcpy_keymaps', JSON.stringify(keymapNodes));
        }
    });

    keymapOverlay.addEventListener('click', (e) => {
        if (!keymapMode) return;
        const rect = keymapOverlay.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;
        const y = (e.clientY - rect.top) / rect.height;
        
        const key = prompt("Nhập phím (ví dụ: W, A, S, D, Space):");
        if (key && key.trim()) {
            keymapNodes.push({ key: key.trim().toLowerCase(), x, y });
            renderKeymaps();
        }
    });
}

// Keymap playback bridge.
//
// The panel (templates/index.html) owns the live socket and the ScrcpyInput
// instance; it publishes them as `window.scrcpyBridge` once the stream is up.
// Earlier revisions of this block emitted a `touch_event` socket.io event with
// a JSON payload — but the server has NO 'touch_event' handler (only
// 'control_data', app.py:1982) and `window.socket` / `window.playerCanvas`
// were never assigned anywhere, so every mapped key was silently dropped.
// We now build a real scrcpy touch message and push it through the same
// sendControl path the mouse uses.
const KM_ACTION_DOWN = 0;
const KM_ACTION_UP = 1;

function kmSendTouch(node, action) {
    const bridge = window.scrcpyBridge;
    if (!bridge || !bridge.input || typeof bridge.send !== 'function') return false;
    const w = bridge.deviceWidth, h = bridge.deviceHeight;
    if (!w || !h) return false;
    // node.x / node.y are normalised 0..1 positions captured over the video.
    const x = Math.round(node.x * w);
    const y = Math.round(node.y * h);
    // pointerId: use a small positive id derived from the key so several mapped
    // keys held at once are tracked as separate fingers (scrcpy allows 0..9).
    const pid = (node.key.charCodeAt(0) % 8) + 1;
    const pressure = action === KM_ACTION_DOWN ? 65535 : 0;
    const buttons = action === KM_ACTION_DOWN ? 1 : 0;
    const data = bridge.input.createTouchProtocolData(
        action, x, y, w, h, /*actionButton*/ 1, buttons, pressure, pid);
    bridge.send(data);
    return true;
}

const kmHeld = new Set();

document.addEventListener('keydown', (e) => {
    if (keymapMode) return;
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    const node = keymapNodes.find(n => n.key === e.key.toLowerCase());
    if (!node) return;
    // Ignore auto-repeat: holding a key must be ONE touch-down, not a stream of
    // them, otherwise the device sees hundreds of taps per second.
    if (kmHeld.has(node.key)) { e.preventDefault(); return; }
    if (kmSendTouch(node, KM_ACTION_DOWN)) {
        kmHeld.add(node.key);
        e.preventDefault();
    }
});

document.addEventListener('keyup', (e) => {
    if (keymapMode) return;
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    const node = keymapNodes.find(n => n.key === e.key.toLowerCase());
    if (!node) return;
    if (!kmHeld.has(node.key)) return;
    kmHeld.delete(node.key);
    kmSendTouch(node, KM_ACTION_UP);
    e.preventDefault();
});

// Releasing everything when the tab loses focus prevents a key from being
// stuck "down" on the device after alt-tab.
window.addEventListener('blur', () => {
    for (const key of Array.from(kmHeld)) {
        const node = keymapNodes.find(n => n.key === key);
        kmHeld.delete(key);
        if (node) kmSendTouch(node, KM_ACTION_UP);
    }
});

