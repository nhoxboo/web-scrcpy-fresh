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
        // + real keyboard on Samsung DeX (and any Android virtual display),
        // and is what makes desktop-style UI usable.
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
        this._pointerLockOwner = null; // element that holds pointer lock

        let mouseX = null;
        let mouseY = null;
        let leftButtonIsPressed = false;
        let rightButtonIsPressed = false;

        const isUhid = () => this.useUhid && this._uhidReady;

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
        // emulated USB HID mouse — move freely on the DeX desktop.
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
            const dx = uhidPendingDx, dy = uhidPendingDy;
            uhidPendingDx = 0; uhidPendingDy = 0;
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

    /** Tear down the HID devices (called when DeX session ends or socket dies). */
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
        // browser deltaY positive = scroll down. Invert so DeX scrolls in
        // the natural direction.
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