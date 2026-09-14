(() => {
  const factsRoot = document.getElementById('deviceFacts');
  if (!factsRoot) return;

  const serial = factsRoot.dataset.serial;
  const render = (facts, available) => {
    factsRoot.replaceChildren();
    const title = document.createElement('h2');
    title.textContent = 'Thông tin thiết bị';
    factsRoot.append(title);
    const grid = document.createElement('dl');
    const entries = [
      ['Model', facts.model],
      ['Android', facts.android_version],
      ['Pin', facts.battery_percent == null ? null : `${facts.battery_percent}%`],
      ['Trạng thái pin', facts.battery_status],
    ];
    entries.forEach(([label, value]) => {
      const term = document.createElement('dt');
      term.textContent = label;
      const description = document.createElement('dd');
      description.textContent = value || 'Không có dữ liệu';
      grid.append(term, description);
    });
    factsRoot.append(grid);
    if (!available) {
      const note = document.createElement('p');
      note.className = 'muted';
      note.textContent = 'Thiết bị chưa trả về dữ liệu. Hãy kiểm tra kết nối ADB rồi tải lại trang.';
      factsRoot.append(note);
    }
  };

  fetch(`/api/devices/${encodeURIComponent(serial)}/facts`, { credentials: 'same-origin' })
    .then((response) => response.json())
    .then((payload) => render(payload.facts || {}, Boolean(payload.available)))
    .catch(() => render({}, false));
})();
