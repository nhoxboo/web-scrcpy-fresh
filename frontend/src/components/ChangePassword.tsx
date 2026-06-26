import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function ChangePassword() {
  const [oldPassword, setOldPassword] = useState('');
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [csrfToken, setCsrfToken] = useState('');
  const [username, setUsername] = useState('admin');
  const navigate = useNavigate();

  useEffect(() => {
    fetch('/api/csrf')
      .then(r => r.json())
      .then(d => { if (d.ok) setCsrfToken(d.csrf_token); })
      .catch(console.error);

    fetch('/api/session')
      .then(r => r.json())
      .then(d => {
        if (!d.authenticated) {
          navigate('/login');
        } else {
          setUsername(d.username);
          setNewUsername(d.username);
        }
      })
      .catch(console.error);
  }, [navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (newPassword !== confirmPassword) {
      setError('Xác nhận mật khẩu mới không khớp');
      return;
    }

    const formData = new FormData();
    formData.append('old_password', oldPassword);
    formData.append('new_username', newUsername);
    formData.append('new_password', newPassword);
    formData.append('confirm_password', confirmPassword);
    formData.append('csrf_token', csrfToken);

    try {
      const res = await fetch('/api/change-password', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();

      if (res.ok && data.ok) {
        setSuccess(data.message || 'Đổi mật khẩu thành công. Đang chuyển hướng...');
        setTimeout(() => navigate('/login'), 2000);
      } else {
        setError(data.error || 'Lỗi khi đổi mật khẩu');
      }
    } catch (err: any) {
      setError('Lỗi kết nối: ' + err.message);
    }
  };

  return (
    <div style={{ minHeight: '100dvh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '20px' }}>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '24px', fontWeight: 600 }}>
        <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#4ade80', boxShadow: '0 0 12px #4ade80' }}></span>
        <span className="brand-grad" style={{ fontSize: '1.2rem' }}>Remote Android nhoxboo</span>
      </div>

      <div className="glass"







        style={{ padding: "30px 28px", borderRadius: "18px", width: '100%', maxWidth: '420px' }}
      >
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h2 style={{ margin: '0 0 8px', fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
            <i className="fa-solid fa-key" style={{ color: '#c084fc' }}></i> Đổi thông tin đăng nhập
          </h2>

          <div style={{ display: 'grid', gap: '6px' }}>
            <label style={{ fontSize: '.78rem', color: '#a8b3cf', letterSpacing: '.04em', textTransform: 'uppercase' }}>Mật khẩu hiện tại *</label>
            <input
              type="password"
              className="glass-input"
              placeholder="Nhập mật khẩu đang dùng"
              required
              value={oldPassword}
              onChange={e => setOldPassword(e.target.value)}
            />
          </div>

          <hr style={{ border: 0, height: '1px', background: 'rgba(255,255,255,0.1)', margin: '4px 0' }} />

          <div style={{ display: 'grid', gap: '6px' }}>
            <label style={{ fontSize: '.78rem', color: '#a8b3cf', letterSpacing: '.04em', textTransform: 'uppercase' }}>Tên đăng nhập mới</label>
            <input
              type="text"
              className="glass-input"
              placeholder="Tên đăng nhập mới (tùy chọn)"
              value={newUsername}
              onChange={e => setNewUsername(e.target.value)}
            />
            <div style={{ fontSize: '.72rem', color: '#64748b' }}>Hiện tại là <code>{username}</code>. Bỏ qua nếu chỉ muốn đổi mật khẩu.</div>
          </div>

          <div style={{ display: 'grid', gap: '6px' }}>
            <label style={{ fontSize: '.78rem', color: '#a8b3cf', letterSpacing: '.04em', textTransform: 'uppercase' }}>Mật khẩu mới *</label>
            <input
              type="password"
              className="glass-input"
              placeholder="Tối thiểu 6 ký tự"
              required
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
            />
          </div>

          <div style={{ display: 'grid', gap: '6px' }}>
            <label style={{ fontSize: '.78rem', color: '#a8b3cf', letterSpacing: '.04em', textTransform: 'uppercase' }}>Xác nhận mật khẩu mới *</label>
            <input
              type="password"
              className="glass-input"
              placeholder="Nhập lại mật khẩu mới"
              required
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', gap: '10px', marginTop: '8px' }}>
            <button type="button" onClick={() => navigate('/')} className="glass-btn" style={{ flex: 1 }}>Hủy</button>
            <button type="submit" className="glass-btn primary" style={{ flex: 1 }}><i className="fa-solid fa-check"></i> Lưu thay đổi</button>
          </div>

          {error && (
            <div className="flash" style={{ padding: '10px 12px', borderRadius: '12px', background: 'rgba(251,113,133,0.10)', border: '1px solid rgba(251,113,133,0.35)', color: '#fecaca', fontSize: '.9rem' }}>
              <i className="fa-solid fa-circle-exclamation"></i> {error}
            </div>
          )}
          {success && (
            <div className="flash" style={{ padding: '10px 12px', borderRadius: '12px', background: 'rgba(74,222,128,0.10)', border: '1px solid rgba(74,222,128,0.35)', color: '#bbf7d0', fontSize: '.9rem' }}>
              <i className="fa-solid fa-circle-check"></i> {success}
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
