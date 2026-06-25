import { useCallback } from 'react';

export function useDeviceInput(inputRef: any, socketRef: any) {

  const sendControl = useCallback((data: any) => {
    if (socketRef.current) {
      socketRef.current.emit('control_data', data);
    }
  }, [socketRef]);

  const keyTap = useCallback((code: number) => {
    if (!inputRef.current) return;
    const ev = { shiftKey: false, ctrlKey: false, altKey: false, metaKey: false, getModifierState: () => false, repeat: 0 };
    inputRef.current.sendKeyCode(ev, 0, code);
    inputRef.current.sendKeyCode(ev, 1, code);
  }, [inputRef]);

  const doPower = useCallback(() => {
    if (!inputRef.current) return;
    inputRef.current.screen_on_off(0);
    setTimeout(() => inputRef.current.screen_on_off(1), 80);
  }, [inputRef]);

  const doVolDown = useCallback(() => keyTap(25), [keyTap]);
  const doVolUp = useCallback(() => keyTap(24), [keyTap]);
  const doBack = useCallback(() => keyTap(4), [keyTap]);
  const doHome = useCallback(() => keyTap(3), [keyTap]);
  const doRecent = useCallback(() => keyTap(187), [keyTap]);

  return {
    doPower,
    doVolDown,
    doVolUp,
    doBack,
    doHome,
    doRecent,
    sendControl,
  };
}
