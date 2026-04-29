class ScrcpyInput {
    constructor(callback, videoElement, width, height, debug = false) {
        this.callback = callback
        this.width = width
        this.height = height
        this.debug = debug
        let mouseX = null;
        let mouseY = null;
        let leftButtonIsPressed = false;
        let rightButtonIsPressed = false;

        document.addEventListener('mousedown', (event) => {
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
            const androidKeyCode = this.mapToAndroidKeyCode(event);
            if (androidKeyCode !== null) {
                this.sendKeyCode(event, 1, androidKeyCode)
            } else {
                console.log(`key: ${event.code}, not mapped to android key code`);
            }
        });
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