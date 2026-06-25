import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import LiquidGlass from 'liquid-glass-react';

export default function Devices() {
  const [devices, setDevices] = useState<{active: any[], saved: any[], current_selected: string}>({ active: [], saved: [], current_selected: '' });
  const [error, setError] = useState('');
  const [csrfToken, setCsrfToken] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetch('/api/csrf')
      .then(r => r.json())
      .then(d => { if (d.ok) setCsrfToken(d.csrf_token); })
      .catch(console.error);

    fetch('/api/devices')
      .then(r => {
        if (r.status === 401) {
          navigate('/login');
          throw new Error('Unauthorized');
        }
        return r.json();
      })
      .then(d => setDevices(d))
      .catch(e => setError(e.message));
  }, [navigate]);

  const selectDevice = async (serial: string | null) => {
    setError('');
    const formData = new FormData();
    formData.append('csrf_token', csrfToken);

    if (serial === null) {
      formData.append('action', 'clear');
    } else {
      formData.append('serial', serial);
    }

    try {
      const res = await fetch('/api/devices/select', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();

      if (res.ok && data.ok) {
        navigate('/');
      } else {
        setError(data.error || 'Lỗi khi chọn thiết bị');
      }
    } catch (err: any) {
      setError('Lỗi kết nối: ' + err.message);
    }
  };

  return (
    <div style={{ minHeight: '100dvh', padding: '30px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>

      <div style={{ width: '100%', maxWidth: '800px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ margin: 0, fontSize: '1.4rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <i className="fa-solid fa-mobile-screen-button" style={{ color: '#6aa6ff' }}></i>
          <span className="brand-grad">Remote Android nhoxboo</span>
        </h2>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={() => navigate('/')} className="glass-btn">
            <i className="fa-solid fa-arrow-left"></i> Quay lại Panel
          </button>
          <button onClick={() => selectDevice(null)} className="glass-btn">
            <i className="fa-solid fa-eraser"></i> Auto (Mặc định)
          </button>
        </div>
      </div>

      {error && (
        <div className="flash" style={{ width: '100%', maxWidth: '800px', marginBottom: '20px', padding: '10px 12px', borderRadius: '12px', background: 'rgba(251,113,133,0.10)', border: '1px solid rgba(251,113,133,0.35)', color: '#fecaca', fontSize: '.9rem' }}>
          <i className="fa-solid fa-circle-exclamation"></i> {error}
        </div>
      )}

      <div style={{ width: '100%', maxWidth: '800px', display: 'grid', gap: '20px' }}>
        <LiquidGlass
          displacementScale={50}
          blurAmount={0.0625}
          saturation={120}
          elasticity={0.2}
          cornerRadius={18}
          padding="24px"
        >
          <h3 style={{ margin: '0 0 16px', fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px', color: '#e2e8f0' }}>
            <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#4ade80', boxShadow: '0 0 12px #4ade80', animation: 'pulse 1.4s ease-in-out infinite' }}></span>
            Thiết bị đang kết nối (ADB)
          </h3>

          {devices.active.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '.9rem', border: '1px dashed rgba(255,255,255,0.1)', borderRadius: '12px' }}>
              Không tìm thấy thiết bị nào qua USB hoặc Wi-Fi.
              <br />Hãy chạy <code>adb devices</code> để kiểm tra.
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '10px' }}>
              {devices.active.map((d: any) => {
                const isSelected = d.serial === devices.current_selected;
                return (
                  <div key={d.serial} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px', background: isSelected ? 'rgba(106,166,255,0.15)' : 'rgba(255,255,255,0.03)', border: `1px solid ${isSelected ? 'rgba(106,166,255,0.4)' : 'rgba(255,255,255,0.08)'}`, borderRadius: '12px', transition: 'all 0.2s ease' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <i className={d.serial.includes(':') ? 'fa-solid fa-wifi' : 'fa-brands fa-usb'} style={{ fontSize: '1.4rem', color: isSelected ? '#6aa6ff' : '#94a3b8' }}></i>
                      <div>
                        <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '1.05rem' }}>{d.model || 'Unknown Device'}</div>
                        <div style={{ fontSize: '.8rem', color: '#94a3b8', marginTop: '2px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <span style={{ fontFamily: 'monospace' }}>{d.serial}</span>
                          {d.state === 'unauthorized' && <span className="chip warn">Unauthorized</span>}
                        </div>
                      </div>
                    </div>

                    {d.state === 'device' ? (
                      <button
                        onClick={() => selectDevice(d.serial)}
                        className={`glass-btn ${isSelected ? 'primary' : ''}`}
                        style={{ minWidth: '120px' }}
                      >
                        {isSelected ? <><i className="fa-solid fa-check"></i> Đang điều khiển</> : 'Chọn thiết bị'}
                      </button>
                    ) : (
                      <button disabled className="glass-btn" title="Vui lòng bấm Allow USB Debugging trên điện thoại">
                        <i className="fa-solid fa-lock"></i> Chưa cấp quyền
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </LiquidGlass>

        {devices.saved.length > 0 && (
          <LiquidGlass
            displacementScale={40}
            blurAmount={0.0625}
            saturation={110}
            elasticity={0.2}
            cornerRadius={18}
            padding="24px"
          >
            <h3 style={{ margin: '0 0 16px', fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px', color: '#e2e8f0' }}>
              <i className="fa-solid fa-clock-rotate-left" style={{ color: '#94a3b8' }}></i> Thiết bị Wi-Fi đã lưu (đang offline)
            </h3>

            <div style={{ display: 'grid', gap: '10px' }}>
              {devices.saved.map((d: any) => {
                const target = d.target || `${d.host}:${d.port}`;
                return (
                  <div key={d.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px', opacity: 0.7 }}>
                      <i className="fa-solid fa-wifi" style={{ fontSize: '1.2rem', color: '#64748b' }}></i>
                      <div>
                        <div style={{ fontWeight: 500, color: '#e2e8f0', fontSize: '.95rem' }}>{d.name || target}</div>
                        <div style={{ fontSize: '.75rem', color: '#64748b', marginTop: '2px', fontFamily: 'monospace' }}>{target}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </LiquidGlass>
        )}
      </div>
    </div>
  );
}
