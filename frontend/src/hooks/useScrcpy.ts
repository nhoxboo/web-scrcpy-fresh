import { useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';

declare global {
  interface Window {
    JMuxer: any;
    VideoParser: any;
    AudioParser: any;
    ScrcpyInput: any;
    parser: any;
    VideoDecoder: any;
  }
}

export function useScrcpy() {
  const [status, setStatus] = useState('Đang kết nối...');
  const [deviceSize, setDeviceSize] = useState({ width: 0, height: 0 });
  const socketRef = useRef<Socket | null>(null);
  const jmuxerRef = useRef<any>(null);
  const videoDecoderRef = useRef<any>(null);
  const inputRef = useRef<any>(null);

  useEffect(() => {
    const useWebCodecs = localStorage.getItem('decoderMode') === 'webcodecs' && typeof window.VideoDecoder !== 'undefined';
    const useWebRtc = localStorage.getItem('transportMode') !== 'websocket';

    // Set socket query options
    const socketQuery: any = {};
    const displayIdSaved = localStorage.getItem('scrcpyDisplayId') || '0';
    if (displayIdSaved !== '0') socketQuery.display_id = displayIdSaved;

    const socket = io({ query: socketQuery });
    socketRef.current = socket;

    socket.on('connect', () => {
      setStatus('Đã kết nối Socket.IO.');
    });

    socket.on('disconnect', (reason) => {
      setStatus(`Mất kết nối: ${reason}`);
    });

    socket.on('connect_error', (err) => {
      setStatus(`Lỗi kết nối: ${err.message || 'unknown'}`);
    });

    // Handle incoming video data
    socket.on('video_data', (data) => {
      if (!useWebRtc && window.parser) {
        window.parser.appendData(new Uint8Array(data));
      }
    });

    // Initialize Parsers (These are globals loaded from vanilla JS for now)
    if (window.VideoParser) {
      window.parser = new window.VideoParser(({ type, data }: any) => {
        if (type === 'nalu') {
          if (useWebCodecs && videoDecoderRef.current?.state === 'configured') {
            try {
              // @ts-ignore
              const chunk = new EncodedVideoChunk({ type: 'delta', timestamp: (performance.now() * 1000) | 0, data });
              videoDecoderRef.current.decode(chunk);
            } catch (e) {}
          } else if (jmuxerRef.current) {
            jmuxerRef.current.feed({ video: data });
          }
        } else if (type === 'init') {
          if (useWebCodecs) {
            videoDecoderRef.current = new window.VideoDecoder({
              output: (frame: any) => {
                const canvas = document.getElementById('playerCanvas') as HTMLCanvasElement;
                if (canvas) {
                  if (canvas.width !== frame.displayWidth || canvas.height !== frame.displayHeight) {
                    canvas.width = frame.displayWidth;
                    canvas.height = frame.displayHeight;
                  }
                  const ctx = canvas.getContext('2d');
                  ctx?.drawImage(frame, 0, 0, canvas.width, canvas.height);
                }
                frame.close();
              },
              error: (err: any) => console.error('WebCodecs Error:', err)
            });
            videoDecoderRef.current.configure({ codec: 'avc1.64002a', avc: { format: 'annexb' }, optimizeForLatency: true });
          } else {
            if (!jmuxerRef.current) {
              jmuxerRef.current = new window.JMuxer({ node: 'player', mode: 'video', flushingTime: 50, fps: 60, clearBuffer: false, onError: (e: any) => console.error(e) });
            }
            jmuxerRef.current.feed({ video: data['sps'] });
            jmuxerRef.current.feed({ video: data['pps'] });
          }
        } else if (type === 'screen_size') {
          setDeviceSize({ width: data['width'], height: data['height'] });
          setStatus(`Kết nối OK | Screen ${data['width']}x${data['height']}`);

          if (window.ScrcpyInput) {
            inputRef.current = new window.ScrcpyInput((controlData: any) => {
              socket.emit('control_data', controlData);
            }, document.getElementById(useWebCodecs ? 'playerCanvas' : 'player'), data['width'], data['height'], false, {
              useUhid: localStorage.getItem('uhidInput') !== '0',
            });
            if (localStorage.getItem('uhidInput') !== '0') inputRef.current.enableUhid();
          }
        } else if (type === 'size_change') {
          setDeviceSize({ width: data['width'], height: data['height'] });
          if (inputRef.current) inputRef.current.resizeScreen(data['width'], data['height']);
        }
      });
    }

    return () => {
      socket.disconnect();
      if (jmuxerRef.current) jmuxerRef.current.destroy();
      if (videoDecoderRef.current) videoDecoderRef.current.close();
    };
  }, []);

  return { status, deviceSize, socketRef, inputRef };
}
