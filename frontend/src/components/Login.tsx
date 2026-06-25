import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import LiquidGlass from 'liquid-glass-react';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [csrfToken, setCsrfToken] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetch('/api/csrf')
      .then(r => r.json())
      .then(d => { if (d.ok) setCsrfToken(d.csrf_token); })
      .catch(console.error);

    fetch('/api/session')
      .then(r => r.json())
      .then(d => { if (d.authenticated) navigate('/'); })
      .catch(console.error);
  }, [navigate]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    formData.append('csrf_token', csrfToken);

    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();

      if (res.ok && data.ok) {
        navigate('/');
      } else {
        setError(data.error || 'Sai tài khoản hoặc mật khẩu');
      }
    } catch (err: any) {
      setError('Lỗi kết nối: ' + err.message);
    }
  };

  return (
    <div style={{ minHeight: '100dvh', display: 'grid', placeItems: 'center', padding: '24px' }}>
      <div style={{ width: 'min(94vw, 880px)', display: 'grid', gridTemplateColumns: '1.05fr 1fr', gap: '28px' }}>

        <LiquidGlass
          displacementScale={64}
          blurAmount={0.0625}
          saturation={130}
          aberrationIntensity={2}
          elasticity={0.35}
          cornerRadius={18}
          padding="38px 34px"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '6px 12px', borderRadius: '999px', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', fontSize: '.78rem', color: '#a8b3cf', width: 'fit-content' }}>
              <i className="fa-solid fa-bolt" style={{ color: '#5eead4' }}></i> Liquid Glass UI · v2
            </span>
            <h1 style={{ margin: 0, fontSize: 'clamp(2rem, 4.6vw, 2.8rem)', lineHeight: 1.05, letterSpacing: '-0.02em' }}>
              <small style={{ display: 'block', fontSize: '.42em', letterSpacing: '.35em', textTransform: 'uppercase', color: '#a8b3cf', marginBottom: '6px', fontWeight: 500 }}>Remote Android</small>
              <span className="brand-grad">nhoxboo</span>
            </h1>
            <p style={{ margin: 0, color: '#a8b3cf', fontSize: '.98rem', lineHeight: 1.55 }}>
              Điều khiển điện thoại từ trình duyệt: chuột thật, bàn phím thật, đồng bộ clipboard 2 chiều, chế độ DeX.
            </p>
            <ul style={{ margin: '4px 0 0', padding: 0, listStyle: 'none', display: 'grid', gap: '10px', fontSize: '.9rem' }}>
              <li style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#d2d8eb' }}><i className="fa-solid fa-mouse-pointer" style={{ width: '28px', height: '28px', display: 'grid', placeItems: 'center', borderRadius: '9px', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: '#6aa6ff' }}></i> UHID mouse / keyboard với cursor thật</li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#d2d8eb' }}><i className="fa-solid fa-display" style={{ width: '28px', height: '28px', display: 'grid', placeItems: 'center', borderRadius: '9px', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: '#6aa6ff' }}></i> Samsung DeX desktop mirroring</li>
            </ul>
          </div>
        </LiquidGlass>

        <LiquidGlass
          displacementScale={64}
          blurAmount={0.0625}
          saturation={130}
          aberrationIntensity={2}
          elasticity={0.35}
          cornerRadius={18}
          padding="30px 28px"
        >
          <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h2 style={{ margin: '0 0 6px', fontSize: '1.18rem', display: 'flex', alignItems: 'center', gap: '10px', fontWeight: 600 }}>
              <i className="fa-solid fa-right-to-bracket"></i> Đăng nhập
            </h2>

            <div style={{ display: 'grid', gap: '6px' }}>
              <label htmlFor="username" style={{ fontSize: '.78rem', color: '#a8b3cf', letterSpacing: '.04em', textTransform: 'uppercase' }}>Tên đăng nhập</label>
              <input
                id="username"
                className="glass-input"
                placeholder="username"
                autoComplete="username"
                required
                autoFocus
                value={username}
                onChange={e => setUsername(e.target.value)}
              />
            </div>

            <div style={{ display: 'grid', gap: '6px' }}>
              <label htmlFor="password" style={{ fontSize: '.78rem', color: '#a8b3cf', letterSpacing: '.04em', textTransform: 'uppercase' }}>Mật khẩu</label>
              <input
                id="password"
                className="glass-input"
                type="password"
                placeholder="••••••••"
                autoComplete="current-password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
            </div>

            <button className="glass-btn primary" type="submit" style={{ marginTop: '8px' }}>
              <i className="fa-solid fa-arrow-right"></i> Đăng nhập
            </button>

            {error && (
              <div className="flash" style={{ marginTop: '6px', padding: '10px 12px', borderRadius: '12px', background: 'rgba(251,113,133,0.10)', border: '1px solid rgba(251,113,133,0.35)', color: '#fecaca', fontSize: '.9rem' }}>
                <i className="fa-solid fa-circle-exclamation"></i> {error}
              </div>
            )}

            <div className="footer" style={{ marginTop: '8px', fontSize: '.76rem', color: '#a8b3cf', textAlign: 'center' }}>
              © Remote Android nhoxboo · scrcpy 3.3.4
            </div>
          </form>
        </LiquidGlass>
      </div>
    </div>
  );
}
