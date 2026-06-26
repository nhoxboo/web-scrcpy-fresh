import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { useScrcpy } from '../hooks/useScrcpy';
import { useDeviceInput } from '../hooks/useDeviceInput';

export default function Panel() {
  const [sessionInfo, setSessionInfo] = useState({ username: '', device_label: '', device_serial: '' });
  const navigate = useNavigate();

  const { status, deviceSize, socketRef, inputRef } = useScrcpy();
  const { doPower, doVolDown, doVolUp, doBack, doHome, doRecent } = useDeviceInput(inputRef, socketRef);

  useEffect(() => {
    fetch('/api/session')
      .then(r => {
        if (r.status === 401) {
          navigate('/login');
          throw new Error('Unauthorized');
        }
        return r.json();
      })
      .then(d => {
        if (d.authenticated) {
          setSessionInfo(d);
        } else {
          navigate('/login');
        }
      })
      .catch(console.error);
  }, [navigate]);

  const handleLogout = async () => {
    try {
      const res = await fetch('/api/csrf');
      const data = await res.json();
      const formData = new FormData();
      formData.append('csrf_token', data.csrf_token);
      await fetch('/api/logout', { method: 'POST', body: formData });
      navigate('/login');
    } catch (e) {
      console.error(e);
    }
  };

  const isWebCodecs = localStorage.getItem('decoderMode') === 'webcodecs' && typeof window.VideoDecoder !== 'undefined';

  return (
    <div style={{ height: '100dvh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div className="glass" style={{ padding: "20px 22px", zIndex: 30, display: "flex", alignItems: "center", gap: "12px", borderRadius: "14px" }}>
        <div style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <i className="fa-solid fa-mobile-screen-button" style={{ color: '#6aa6ff' }}></i>
          <span className="brand-grad" style={{ fontSize: '1rem' }}>Remote Android nhoxboo</span>
        </div>
        <span className="chip"><i className="fa-solid fa-user"></i> {sessionInfo.username}</span>
        <span className="chip" title="Thiết bị đang điều khiển">
          <i className="fa-solid fa-mobile-screen"></i> {sessionInfo.device_label || 'auto'}
        </span>
        <button className="glass-btn" onClick={() => navigate('/devices')} style={{ padding: '6px 10px', fontSize: '.8rem' }}><i className="fa-solid fa-shuffle"></i> Đổi máy</button>
        <div style={{ flex: 1 }}></div>
        <button className="glass-btn" onClick={() => navigate('/change-password')} style={{ padding: '6px 10px', fontSize: '.8rem' }}><i className="fa-solid fa-key"></i> Đổi mật khẩu</button>
        <button className="glass-btn" onClick={handleLogout} style={{ padding: '6px 10px', fontSize: '.8rem' }}><i className="fa-solid fa-right-from-bracket"></i> Đăng xuất</button>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div className="glass" style={{ padding: "16px", zIndex: 30, display: "flex", flexDirection: "column", alignItems: "center", gap: "8px", width: "70px", justifyContent: "center", borderRadius: "14px" }}>
          <button className="tool" title="Power" onClick={doPower}><i className="fa-solid fa-power-off"></i></button>
          <button className="tool" title="Volume +" onClick={doVolUp}><i className="fa-solid fa-volume-high"></i></button>
          <button className="tool" title="Volume -" onClick={doVolDown}><i className="fa-solid fa-volume-low"></i></button>
          <div style={{ width: '30px', height: '1px', background: 'rgba(255,255,255,0.1)', margin: '4px 0' }}></div>
          <button className="tool" title="Back" onClick={doBack}><i className="fa-solid fa-arrow-left"></i></button>
          <button className="tool" title="Home" onClick={doHome}><i className="fa-solid fa-house"></i></button>
          <button className="tool" title="Recent" onClick={doRecent}><i className="fa-solid fa-layer-group"></i></button>
          <div style={{ width: '30px', height: '1px', background: 'rgba(255,255,255,0.1)', margin: '4px 0' }}></div>
          <button className="tool" title="Rotate" onClick={() => inputRef.current?.rotateDevice()}><i className="fa-solid fa-rotate"></i></button>
        </div>

        <div style={{ flex: 1, position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px', background: 'var(--bg-0)' }} id="videoWrap">
          <div className={`phone-shell ${deviceSize.width > deviceSize.height ? 'landscape' : ''}`} id="phoneShell" style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(180deg,rgba(40,45,66,.7),rgba(20,24,40,.7))', border: '1px solid rgba(255,255,255,.12)', borderRadius: '38px', boxShadow: '0 30px 70px rgba(0,0,0,.55),inset 0 1px 0 rgba(255,255,255,.12),inset 0 -1px 0 rgba(0,0,0,.3)', padding: deviceSize.width > deviceSize.height ? '8px' : '18px 10px 14px 10px', maxWidth: '100%', maxHeight: '100%' }}>
            <video id="player" autoPlay muted playsInline style={{ display: isWebCodecs ? 'none' : 'block', maxWidth: 'none', maxHeight: 'none', objectFit: 'contain', borderRadius: '20px', background: '#000', border: '1px solid #1f2937', width: '100%', height: '100%' }}></video>
            <canvas id="playerCanvas" style={{ display: isWebCodecs ? 'block' : 'none', maxWidth: 'none', maxHeight: 'none', objectFit: 'contain', borderRadius: '20px', background: '#000', border: '1px solid #1f2937', width: '100%', height: '100%' }}></canvas>
          </div>
        </div>
      </div>

      <div className="glass" style={{ padding: "10px 20px", display: "flex", alignItems: "center", fontSize: ".8rem", color: "#a8b3cf", zIndex: 30, borderRadius: "14px" }}>
        <span className="dot" style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#4ade80', marginRight: '6px', boxShadow: '0 0 12px #4ade80', animation: 'pulse 1.4s ease-in-out infinite' }}></span>
        <span>{status}</span>
      </div>
    </div>
  );
}
